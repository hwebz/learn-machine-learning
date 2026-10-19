from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from app.adapters.base import HealthStatus, ProviderResult, Source, StepCallback
from app.adapters.selectors_loader import load_selectors, provider_selectors
from app.browser.artifacts import save_artifacts
from app.browser.extraction import clean_markdown_text, html_to_markdown, normalize_sources
from app.browser.locators import resolve_locator
from app.browser.session import BrowserSession
from app.browser.waits import wait_for_completion, wait_for_input
from app.core.config import settings

logger = structlog.get_logger(__name__)


class ProviderNeedsUserAction(RuntimeError):
    """Raised when the adapter cannot proceed without human help (login, CAPTCHA, rate limit)."""


class AnswerExtractionError(RuntimeError):
    """An extraction failure that may retain usable partial text."""

    def __init__(self, message: str, answer: str = "") -> None:
        super().__init__(message)
        self.answer = answer


class TokenBucket:
    """Simple in-process token bucket for per-provider hourly caps."""

    def __init__(self, capacity: int, refill_per_second: float) -> None:
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_per_second = refill_per_second
        self._updated = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated
        self._updated = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)

    def try_acquire(self) -> bool:
        self._refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


_buckets: dict[str, TokenBucket] = {}


def _bucket_for(provider: str) -> TokenBucket:
    bucket = _buckets.get(provider)
    if bucket is None:
        capacity = max(1, settings.max_questions_per_hour)
        bucket = TokenBucket(capacity=capacity, refill_per_second=capacity / 3600.0)
        _buckets[provider] = bucket
    return bucket


def reset_buckets() -> None:
    """Clear rate-limit state (tests / smoke scripts)."""
    _buckets.clear()


class BrowserProviderAdapter(ABC):
    """Shared Playwright ask() flow for signed-in chatbot web UIs.

    Subclasses only declare ``name`` and site-specific hooks; all selector
    resolution, completion detection, artifacts, and blocking handling live
    here. Every provider must return the same ``ProviderResult`` contract as
    the official-API adapters so the orchestrator is unchanged.
    """

    name: str = ""

    def __init__(
        self,
        *,
        session: BrowserSession | None = None,
        selectors: dict[str, Any] | None = None,
        artifact_dir: Path | None = None,
    ) -> None:
        from app.browser.session import BrowserSessionManager
        self._session = session or BrowserSessionManager.get_session(self.name)
        self._selectors = selectors if selectors is not None else load_selectors()
        self._artifact_dir = artifact_dir or settings.artifact_dir
        self._cfg = provider_selectors(self._selectors, self.name)

    # ------------------------------------------------------------- health

    async def health(self) -> HealthStatus:
        """Static health: selectors present + profile dir exists. Never launches a browser."""
        from app.core.config import get_provider_profile_dir

        try:
            provider_selectors(self._selectors, self.name)
            selectors_ok = True
            detail = "Selectors configured"
        except Exception as exc:  # noqa: BLE001
            selectors_ok = False
            detail = f"Selector config error: {exc}"
        profile_dir = get_provider_profile_dir(self.name)
        logged_in = profile_dir.is_dir() and any(profile_dir.iterdir())
        if not logged_in:
            detail = f"{detail}; profile dir empty or missing — run scripts/login_profile.py"
        return HealthStatus(logged_in=logged_in, selectors_ok=selectors_ok, detail=detail)

    # ------------------------------------------------------------- hooks

    @abstractmethod
    async def _select_mode(self, page: Any, mode: str) -> None:
        """Optionally switch the site's research/pro mode. Must be best-effort."""

    async def _enter_prompt(self, page: Any, input_locator: Any, prompt: str) -> None:
        """Enter prompt into the chat input. Subclasses can override for custom autocomplete/skills."""
        try:
            await input_locator.click(timeout=5000)
        except Exception:  # noqa: BLE001 — fall back to fill on real <textarea>/<input>
            pass
        try:
            await input_locator.fill(prompt, timeout=10000)
        except Exception:  # noqa: BLE001 — contenteditable: use type() instead
            await input_locator.click(timeout=5000)
            await input_locator.type(prompt, delay=15)

    async def _prepare_response(self, page: Any) -> None:
        """Record provider-specific response state before submitting."""

    async def _response_ready(self, page: Any) -> bool | None:
        """Return None for normal completion, or readiness for a rich response."""
        return None

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        # 1. Attempt to use the site's Copy button if available (cleanest Markdown)
        # In async mode, bypass the OS clipboard entirely to prevent concurrent answer collisions
        allow_clipboard = (settings.work_mode == "sync")
        done_chain = self._cfg.get("done_indicator", [])
        if allow_clipboard and done_chain:
            copy_locator, _ = await resolve_locator(page, done_chain)
            if copy_locator is not None:
                try:
                    count = await copy_locator.count()
                    if count > 0:
                        # Clear clipboard first to prevent stale text leakage from prior providers
                        try:
                            await page.evaluate("navigator.clipboard.writeText('')")
                        except Exception:  # noqa: BLE001
                            pass
                        target_btn = copy_locator.last if count > 1 else copy_locator.first
                        await target_btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        clipboard_text = await page.evaluate("navigator.clipboard.readText()")
                        if (
                            clipboard_text
                            and len(clipboard_text.strip()) > 10
                            and clipboard_text.strip().lower() != prompt.strip().lower()
                        ):
                            logger.info("answer_copied_from_clipboard", provider=self.name, length=len(clipboard_text))
                            return clean_markdown_text(clipboard_text)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("clipboard_copy_fallback", provider=self.name, error=str(exc))

        # 2. Fall back to DOM answer container extraction
        locator, _ = await resolve_locator(page, self._cfg.get("answer_container", []))
        if locator is None:
            return ""
        try:
            count = await locator.count()
            if count == 0:
                return ""
            target = locator.last if count > 1 else locator
            html = await target.inner_html(timeout=5000)
            markdown = html_to_markdown(html, provider=self.name)
            if markdown.strip():
                return clean_markdown_text(markdown)
            raw_text = await target.inner_text(timeout=5000)
            return clean_markdown_text(raw_text)
        except Exception:  # noqa: BLE001
            return ""

    async def _extract_sources(self, page: Any) -> list[Source]:
        locator, _ = await resolve_locator(page, self._cfg.get("source_links", []))
        if locator is None:
            return []
        pairs: list[tuple[str, str | None]] = []
        try:
            count = await locator.count()
            for index in range(count):
                item = locator.nth(index)
                href = await item.get_attribute("href", timeout=2000)
                text = ""
                try:
                    text = (await item.inner_text(timeout=2000)).strip()
                except Exception:  # noqa: BLE001
                    pass
                if not href:
                    raw_grouped = await item.get_attribute("data-grouped-citations", timeout=1000)
                    if raw_grouped:
                        try:
                            import json
                            parsed = json.loads(raw_grouped)
                            if isinstance(parsed, list) and len(parsed) > 0:
                                aria = await item.get_attribute("aria-label", timeout=1000) or ""
                                aria_title = ""
                                if aria:
                                    lbl = aria.strip()
                                    if lbl.lower().startswith("citation:"):
                                        lbl = lbl[9:].strip()
                                    if " — " in lbl:
                                        aria_title = lbl.split(" — ", 1)[1].strip()
                                    elif " - " in lbl:
                                        aria_title = lbl.split(" - ", 1)[1].strip()
                                    elif lbl:
                                        aria_title = lbl
                                is_multi = len(parsed) > 1
                                for p_item in parsed:
                                    if isinstance(p_item, dict) and p_item.get("url"):
                                        p_url = p_item["url"]
                                        p_name = (p_item.get("name") or "").strip() or None
                                        p_title = p_name if is_multi else (aria_title or p_name)
                                        pairs.append((p_url, p_title))
                                continue
                        except Exception:  # noqa: BLE001
                            pass
                if not href and text.startswith(("http://", "https://")):
                    href = text
                    text = ""
                if href:
                    pairs.append((href, text or None))
        except Exception:  # noqa: BLE001
            return []
        return normalize_sources(pairs)

    async def attempt_login_recovery(self, page: Any) -> bool:
        """Best-effort recovery when the site shows a login screen. Returns True
        once the page is past the login wall (e.g., a remembered-account tile was
        clicked and navigation completed). Base implementation never recovers;
        sites that remember the account (Copilot) override this."""
        return False

    async def _retry_button_visible(self, page: Any) -> bool:
        """Return True if a site-specific retry button is visible and click it.
        Used when the model returns a transient error (e.g., Kimi busy).
        Subclasses declare 'retry_indicator' in selectors.yaml; base does nothing."""
        chain = self._cfg.get("retry_indicator")
        if not chain:
            return False
        locator, _ = await resolve_locator(page, chain)
        if locator is None:
            return False
        try:
            count = await locator.count()
            if count == 0:
                return False
            btn = locator.first
            if await btn.is_visible(timeout=2000):
                await btn.click(timeout=5000)
                return True
        except Exception:  # noqa: BLE001
            return False
        return False

    # ------------------------------------------------------------- ask flow

    async def ask(
        self,
        prompt: str,
        *,
        timeout_s: int,
        mode: str = "default",
        on_step: StepCallback | None = None,
    ) -> ProviderResult:
        started_at = datetime.now(timezone.utc)
        bucket = _bucket_for(self.name)
        if not bucket.try_acquire():
            raise ProviderNeedsUserAction(
                f"Rate limit reached for {self.name} ({settings.max_questions_per_hour}/hour)."
            )

        async def _notify(step: str, message: str, data: dict[str, Any] | None = None) -> None:
            if on_step is not None:
                try:
                    await on_step(step, message, data)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("on_step_notify_failed", provider=self.name, step=step, error=str(exc))

        # Defensive jitter between questions (dispatcher also delays).
        await _notify("waiting_turn", f"Chuẩn bị tài nguyên trình duyệt cho {self.name}...")
        await asyncio.sleep(random.uniform(settings.min_delay_between_questions_s, settings.max_delay_between_questions_s))

        job_tag = f"ui-{self.name}-{int(time.time())}"
        artifact_paths: list[str] = []
        status: str = "ok"
        error: str | None = None
        answer = ""
        completion_text = ""
        sources: list[Source] = []
        live_polled_citations: list[dict[str, Any]] = []
        conversation_url: str | None = None

        try:
            async with self._session.exclusive():
                target_url = self._cfg.get("new_chat_url", "")
                await _notify("navigating", f"Đang mở trang web {self.name} ({target_url})...", {"url": target_url})
                page = await self._session.new_page(target_url)
                try:
                    from app.browser.waits import detect_blocking_state

                    await _notify("checking_auth", f"Đang kiểm tra đăng nhập/CAPTCHA trên {self.name}...")
                    blocking = await detect_blocking_state(page, self._selectors.get("blocking", {}))
                    if blocking is not None and blocking.kind == "login":
                        await _notify("recovering_auth", f"Phát hiện màn hình đăng nhập, đang thử tự động khôi phục phiên cho {self.name}...")
                        recovered = await self.attempt_login_recovery(page)
                        if recovered:
                            blocking = await detect_blocking_state(page, self._selectors.get("blocking", {}))

                    if blocking is not None:
                        status = "needs_user_action"
                        error = f"Blocked ({blocking.kind}): {blocking.detail}. Complete login/CAPTCHA in the browser, then retry."
                        await _notify(
                            "blocked",
                            f"{self.name} yêu cầu xác thực người dùng ({blocking.kind}): {blocking.detail}",
                            {"blocking_kind": blocking.kind, "blocking_detail": blocking.detail, "needs_user_action": True, "provider": self.name, "status": "needs_user_action", "error": error},
                        )
                    else:
                        # SPA editors (e.g., Mistral, Gemini) can take several seconds to hydrate
                        # depending on network conditions — poll until the input appears
                        # instead of sleeping a fixed amount.
                        await _notify("locating_input", f"Đang định vị ô nhập prompt trên {self.name}...")
                        input_locator = await wait_for_input(page, self._cfg.get("question_input", []))
                        if input_locator is None:
                            status = "error"
                            error = "Question input locator not found — selectors may be stale. See selectors.yaml and data/artifacts."
                            await _notify("error", f"Không tìm thấy ô nhập câu hỏi trên {self.name}.", {"error": error})
                        else:
                            if mode and mode != "default":
                                await _notify("selecting_mode", f"Đang cấu hình chế độ nghiên cứu ({mode}) cho {self.name}...")
                            await self._select_mode(page, mode)

                            await _notify("entering_prompt", f"Đang nhập câu hỏi vào ô chat của {self.name}...")
                            try:
                                await self._enter_prompt(page, input_locator, prompt)
                            except Exception as exc2:  # noqa: BLE001
                                status = "error"
                                error = f"Could not enter prompt: {type(exc2).__name__}: {exc2}"
                            if status != "error":
                                await asyncio.sleep(0.75)  # let the submit button render
                                await self._prepare_response(page)
                                submit_locator, _ = await resolve_locator(page, self._cfg.get("submit", []))
                                if submit_locator is None:
                                    # Fall back to submitting via Enter key (common in SPAs).
                                    try:
                                        await input_locator.press("Enter")
                                    except Exception:  # noqa: BLE001
                                        status = "error"
                                        error = "Submit locator not found and Enter key failed — selectors may be stale."
                                else:
                                    await submit_locator.click()
                                if status != "error":
                                    await _notify("submitting", f"Đã gửi câu hỏi đến {self.name}, đang chờ xử lý...")
                            if status not in {"error", "needs_user_action"}:
                                await _notify("generating", f"Đang đợi {self.name} sinh câu trả lời (thời gian tối đa {timeout_s}s)...")
                                # Per-provider completion overrides (e.g., Mistral's
                                # done_marker_delay_s) take precedence over global defaults.
                                completion_cfg = {**self._selectors.get("completion", {}),
                                                  **(self._cfg.get("completion") or {})}

                                last_thinking_snapshot: dict[str, Any] | None = None

                                async def _on_thinking_poll(
                                    state: str,
                                    generating: bool,
                                    is_thinking: bool,
                                    thinking_text: str,
                                    citations: list[dict[str, Any]],
                                    last_text: str,
                                    poll_count: int,
                                    elapsed_s: float,
                                    thinking_steps: list[dict[str, Any]] | None = None,
                                    **kwargs: Any,
                                ) -> None:
                                    nonlocal last_thinking_snapshot, conversation_url

                                    try:
                                        cur_page_url = page.url
                                        if cur_page_url and cur_page_url.startswith(("http://", "https://")) and cur_page_url != target_url:
                                            conversation_url = cur_page_url
                                    except Exception:
                                        pass

                                    steps_list = thinking_steps or []
                                    cits_list = citations or []

                                    # Accumulate live citations
                                    if cits_list:
                                        for c in cits_list:
                                            c_url = c.get("url")
                                            if c_url and not any(existing.get("url") == c_url for existing in live_polled_citations):
                                                live_polled_citations.append(c)

                                    # Build normalized snapshot to compare against previous status
                                    norm_steps = [
                                        (
                                            s.get("title", "").strip(),
                                            s.get("description", "").strip(),
                                            s.get("status", "").strip(),
                                        )
                                        for s in steps_list
                                        if isinstance(s, dict)
                                    ]
                                    norm_citations = sorted([
                                        str(c.get("url", "")).strip()
                                        for c in cits_list
                                        if isinstance(c, dict) and c.get("url")
                                    ])
                                    current_snapshot = {
                                        "is_thinking": bool(is_thinking),
                                        "steps": norm_steps,
                                        "thinking_text": (thinking_text or "").strip(),
                                        "citations": norm_citations,
                                        "last_text": (last_text or "").strip(),
                                    }

                                    # Deduplication: If thinking steps, citations, and response text have not changed, do NOT push new event to SSE
                                    if last_thinking_snapshot is not None and current_snapshot == last_thinking_snapshot:
                                        return

                                    last_thinking_snapshot = current_snapshot

                                    # Compose descriptive message without time counter so message is stable
                                    if is_thinking and steps_list:
                                        active_step = steps_list[-1]
                                        step_title = (active_step.get("title") or "").strip() or "Thinking..."
                                        step_desc = (active_step.get("description") or "").strip()
                                        if step_desc:
                                            desc_preview = step_desc[:120] + "..." if len(step_desc) > 120 else step_desc
                                            msg = f"{self.name} đang suy luận: {step_title} — {desc_preview}"
                                        else:
                                            msg = f"{self.name} đang suy luận: {step_title}"
                                    elif generating or last_text:
                                        msg = f"{self.name} đang sinh câu trả lời: Đang lấy câu trả lời trực tiếp..."
                                        if not steps_list:
                                            steps_list = [{
                                                "title": f"{self.name} đang sinh câu trả lời: Đang lấy câu trả lời trực tiếp...",
                                                "description": "Đang lấy câu trả lời trực tiếp...",
                                                "status": "running" if generating else "completed",
                                            }]
                                    elif is_thinking and thinking_text:
                                        msg = f"{self.name} đang sinh câu trả lời: Đang lấy câu trả lời trực tiếp..."
                                        if not steps_list:
                                            steps_list = [{
                                                "title": f"{self.name} đang sinh câu trả lời: Đang lấy câu trả lời trực tiếp...",
                                                "description": "Đang lấy câu trả lời trực tiếp...",
                                                "status": "running" if generating else "completed",
                                            }]
                                    elif steps_list:
                                        active_step = steps_list[-1]
                                        step_title = (active_step.get("title") or "").strip() or "Thinking..."
                                        step_desc = (active_step.get("description") or "").strip()
                                        if step_desc:
                                            desc_preview = step_desc[:120] + "..." if len(step_desc) > 120 else step_desc
                                            msg = f"{self.name}: {step_title} — {desc_preview}"
                                        else:
                                            msg = f"{self.name}: {step_title}"
                                    elif cits_list:
                                        msg = f"{self.name} đang đối chiếu {len(cits_list)} nguồn tài liệu ({state})..."
                                    elif generating:
                                        msg = f"{self.name} đang sinh câu trả lời: Đang lấy câu trả lời trực tiếp..."
                                    else:
                                        msg = f"{self.name}: {state}"

                                    await _notify(
                                        "thinking_progress",
                                        msg,
                                        {
                                            "provider": self.name,
                                            "state": state,
                                            "generating": generating,
                                            "is_thinking": is_thinking,
                                            "thinking_text": thinking_text,
                                            "thinking_steps": steps_list,
                                            "citations": cits_list,
                                            "citations_count": len(cits_list),
                                            "text_preview": last_text[-250:] if last_text else "",
                                            "streaming_text": last_text,
                                            "elapsed_s": elapsed_s,
                                            "poll_count": poll_count,
                                            "conversation_url": conversation_url,
                                        },
                                    )

                                completion = await wait_for_completion(
                                    page,
                                    provider=self.name,
                                    provider_cfg=self._cfg,
                                    blocking=self._selectors.get("blocking", {}),
                                    completion_cfg=completion_cfg,
                                    timeout_s=timeout_s,
                                    on_poll=_on_thinking_poll,
                                    response_ready=self._response_ready,
                                    thinking_interval_s=settings.thinking_interval_check,
                                    response_interval_s=settings.response_interval_check,
                                )
                                # Some sites (e.g., Kimi) finish with "System is
                                # currently busy..." and a Retry button — retry a
                                # couple of times before giving up.
                                retries = 0
                                max_retries = int(self._cfg.get("max_retries", 2))
                                while (
                                    completion.reason in {"timeout", "stable", "done_marker"}
                                    and retries < max_retries
                                    and await self._retry_button_visible(page)
                                ):
                                    retries += 1
                                    logger.info("answer_retry", provider=self.name, attempt=retries)
                                    await _notify("retrying", f"{self.name} thông báo bận, đang thử lại (lần {retries}/{max_retries})...")
                                    last_thinking_snapshot = None
                                    completion = await wait_for_completion(
                                        page,
                                        provider=self.name,
                                        provider_cfg=self._cfg,
                                        blocking=self._selectors.get("blocking", {}),
                                        completion_cfg=completion_cfg,
                                        timeout_s=timeout_s,
                                        on_poll=_on_thinking_poll,
                                        thinking_interval_s=settings.thinking_interval_check,
                                        response_interval_s=settings.response_interval_check,
                                    )
                                completion_text = completion.text
                                if completion.reason == "blocked":
                                    status = "needs_user_action"
                                    error = f"Blocked during generation: {completion.blocking_detail}"
                                    await _notify(
                                        "blocked",
                                        f"{self.name} bị gián đoạn do yêu cầu xác thực: {completion.blocking_detail}",
                                        {"blocking_kind": "verification", "blocking_detail": completion.blocking_detail, "needs_user_action": True, "provider": self.name, "status": "needs_user_action", "error": error},
                                    )
                                elif completion.reason == "timeout":
                                    status = "partial" if completion.text.strip() else "timeout"
                                    if status == "timeout":
                                        error = f"No answer within {timeout_s}s"
                                    else:
                                        error = "Answer may be incomplete (timeout while generating)"
                                elif completion.reason == "page_closed":
                                    status = "error"
                                    error = f"Browser tab closed before answer was extracted"
                                else:
                                    status = "ok"

                    if status in {"ok", "partial"}:
                        try:
                            await _notify("extracting", f"Đang trích xuất nội dung câu trả lời và nguồn trích dẫn từ {self.name}...")

                            # Provider-specific: Ensure the sources / thinking drawer is open before extracting
                            if self.name == "qwen":
                                try:
                                    drawer_present = await page.locator(".qwen-chat-thinking-and-sources-content").count() > 0
                                    if not drawer_present:
                                        drawer_btn = page.locator(
                                            "button.qwen-chat-package-comp-source-list, "
                                            ".anticon.qwen-chat-status-card-after, "
                                            ".qwen-chat-tool-status-card"
                                        ).first
                                        if await drawer_btn.is_visible(timeout=1000):
                                            await drawer_btn.click(timeout=2000)
                                            await page.wait_for_timeout(600)
                                except Exception:  # noqa: BLE001
                                    pass
                            elif self.name == "copilot":
                                try:
                                    cot_btn = page.locator(
                                        "button.scc-ChainOfThought__expandButton[aria-expanded='false'], "
                                        "button[class*='scc-ChainOfThought__expandButton'][aria-expanded='false'], "
                                        "button[id*='expand-button'][aria-expanded='false']"
                                    ).first
                                    if await cot_btn.count() > 0 and await cot_btn.is_visible(timeout=1000):
                                        await cot_btn.click(timeout=1500)
                                        await page.wait_for_timeout(400)
                                except Exception:  # noqa: BLE001
                                    pass
                                try:
                                    sources_btn = page.locator(
                                        "button[data-testid='sources-button-testid'], "
                                        "button[aria-label='Sources'], "
                                        "[data-testid='sources-button-testid']"
                                    ).first
                                    if await sources_btn.count() > 0 and await sources_btn.is_visible(timeout=1000):
                                        await sources_btn.click(timeout=1500)
                                        await page.wait_for_timeout(500)
                                except Exception:  # noqa: BLE001
                                    pass
                            elif self.name == "gemini":
                                try:
                                    thought_toggles = page.locator(
                                        ".thoughts-container button[aria-expanded='false'], "
                                        ".thoughts-wrapper button[aria-expanded='false'], "
                                        "button.thoughts-header[aria-expanded='false'], "
                                        "button.thoughts-toggle[aria-expanded='false'], "
                                        "button[aria-label*='suy nghĩ' i][aria-expanded='false'], "
                                        "button[aria-label*='thought' i][aria-expanded='false']"
                                    )
                                    count = await thought_toggles.count()
                                    for idx in range(count):
                                        toggle = thought_toggles.nth(idx)
                                        if await toggle.is_visible(timeout=500):
                                            await toggle.click(timeout=1000)
                                            await page.wait_for_timeout(300)
                                except Exception:  # noqa: BLE001
                                    pass

                            answer = await self._extract_answer(page, prompt=prompt) or completion_text

                            # Perform a final DOM scan to catch any citations loaded when drawer opened
                            try:
                                final_scan = await page.evaluate(DOM_SCAN_THINKING_AND_CITATIONS, self.name)
                                if isinstance(final_scan, dict) and final_scan.get("citations"):
                                    for c in final_scan["citations"]:
                                        c_url = c.get("url")
                                        if c_url and not any(existing.get("url") == c_url for existing in live_polled_citations):
                                            live_polled_citations.append(c)
                            except Exception:  # noqa: BLE001
                                pass

                            sources = await self._extract_sources(page)
                            if live_polled_citations:
                                known_urls = {str(s.url) for s in sources}
                                # Backfill titles for existing sources if extracted without title
                                for s in sources:
                                    if not s.title:
                                        matching = next((c for c in live_polled_citations if c.get("url") == str(s.url)), None)
                                        if matching and matching.get("title"):
                                            s.title = matching["title"]
                                pairs_to_add = [
                                    (str(c["url"]), c.get("title"))
                                    for c in live_polled_citations
                                    if c.get("url") and str(c["url"]) not in known_urls
                                ]
                                if pairs_to_add:
                                    sources.extend(normalize_sources(pairs_to_add))
                            if not answer.strip():
                                status = "partial" if status == "partial" else "error"
                                error = error or "Extracted answer was empty"
                        except AnswerExtractionError as exc:
                            answer = exc.answer
                            status = "partial" if answer.strip() else "error"
                            error = str(exc)
                        except RuntimeError as exc:
                            if "closed" in str(exc).lower():
                                status = "error"
                                error = error or "Browser tab closed while extracting answer"
                            else:
                                raise

                    try:
                        raw_url = page.url
                        if raw_url and raw_url.startswith(("http://", "https://")):
                            conversation_url = raw_url
                    except Exception:  # noqa: BLE001
                        pass
                finally:
                    try:
                        raw_url = page.url
                        if raw_url and raw_url.startswith(("http://", "https://")):
                            conversation_url = raw_url
                    except Exception:  # noqa: BLE001
                        pass
                    artifact_paths = await save_artifacts(
                        page,
                        job_tag=job_tag,
                        provider=self.name,
                        artifact_dir=self._artifact_dir,
                    )
                    try:
                        # Keep at least one tab alive (navigate to about:blank)
                        # so Chromium doesn't exit when the last tab is closed.
                        if self._session._ctx is not None and len(self._session._ctx.pages) <= 1:
                            await page.goto("about:blank")
                        else:
                            await page.close()
                    except Exception:  # noqa: BLE001
                        pass
        except ProviderNeedsUserAction:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("ui_ask_failed", provider=self.name)
            status = "error"
            error = f"{type(exc).__name__}: {exc}"

        finished_at = datetime.now(timezone.utc)
        logger.info(
            "ui_ask_finished",
            provider=self.name,
            status=status,
            sources=len(sources),
            answer_len=len(answer),
        )
        return ProviderResult(
            provider=self.name,
            prompt=prompt,
            answer_markdown=answer,
            sources=sources,
            conversation_url=conversation_url,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            started_at=started_at,
            finished_at=finished_at,
            artifact_paths=artifact_paths,
            error=error,
        )

    async def delete_conversation(self, conversation_url: str) -> bool:
        """Best-effort automated deletion of a chat conversation on the provider platform."""
        if not conversation_url or not conversation_url.startswith(("http://", "https://")):
            return False

        logger.info("provider_delete_conversation_start", provider=self.name, url=conversation_url)
        try:
            async with self._session.exclusive():
                page = await self._session.new_page(conversation_url)
                try:
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=7000)
                    except Exception:
                        pass
                    await asyncio.sleep(2.0)

                    # 1. ChatGPT API-level deletion check
                    if self.name == "chatgpt":
                        match = re.search(r"/c/([a-f0-9\-]+)", conversation_url)
                        if match:
                            conv_id = match.group(1)
                            api_ok = await page.evaluate(
                                """async (id) => {
                                    try {
                                        const res = await fetch(`/backend-api/conversation/${id}`, {
                                            method: 'PATCH',
                                            headers: {'Content-Type': 'application/json'},
                                            body: JSON.stringify({is_visible: false})
                                        });
                                        return res.ok;
                                    } catch (e) {
                                        return false;
                                    }
                                }""",
                                conv_id,
                            )
                            if api_ok:
                                logger.info("chatgpt_conversation_deleted_via_api", conv_id=conv_id)
                                return True

                    # 2. Universal & configured selector chains
                    delete_cfg = self._cfg.get("delete_chat") or {}
                    menu_chain = delete_cfg.get("menu_button") or [
                        {"css": "button[data-testid*='options' i]"},
                        {"css": "button[data-testid*='menu' i]"},
                        {"css": "button[aria-haspopup='menu']"},
                        {"css": "button[aria-label*='Options' i]"},
                        {"css": "button[aria-label*='More' i]"},
                        {"css": "button[aria-label*='Tùy chọn' i]"},
                        {"css": "button[aria-label*='Thao tác' i]"},
                        {"css": "button[aria-label*='Chat actions' i]"},
                    ]
                    del_chain = delete_cfg.get("delete_button") or [
                        {"css": "[role='menuitem']:has-text('Delete')"},
                        {"css": "[role='menuitem']:has-text('Xóa')"},
                        {"css": "button:has-text('Delete')"},
                        {"css": "button:has-text('Xóa')"},
                        {"css": "div[role='menuitem']:has-text('Delete')"},
                    ]
                    confirm_chain = delete_cfg.get("confirm_button") or [
                        {"css": "[role='dialog'] button:has-text('Delete')"},
                        {"css": "[role='dialog'] button:has-text('Xóa')"},
                        {"css": "button[data-testid*='confirm' i]"},
                        {"css": "button.btn-danger"},
                        {"css": "button:has-text('Confirm')"},
                        {"css": "button:has-text('Xác nhận')"},
                    ]

                    # Step A: Click options/overflow menu if present
                    menu_btn, _ = await resolve_locator(page, menu_chain)
                    if menu_btn is not None:
                        try:
                            if await menu_btn.is_visible(timeout=2000):
                                await menu_btn.click(timeout=2000)
                                await asyncio.sleep(0.5)
                        except Exception:
                            pass

                    # Step B: Click Delete item
                    del_btn, _ = await resolve_locator(page, del_chain)
                    if del_btn is not None:
                        try:
                            if await del_btn.is_visible(timeout=2000):
                                await del_btn.click(timeout=2000)
                                await asyncio.sleep(0.5)
                        except Exception:
                            pass

                    # Step C: Click Confirm Delete button
                    confirm_btn, _ = await resolve_locator(page, confirm_chain)
                    if confirm_btn is not None:
                        try:
                            if await confirm_btn.is_visible(timeout=2000):
                                await confirm_btn.click(timeout=3000)
                                await asyncio.sleep(1.0)
                                logger.info("provider_conversation_deleted_via_ui", provider=self.name, url=conversation_url)
                                return True
                        except Exception:
                            pass

                    logger.warning("provider_delete_selectors_not_matched", provider=self.name, url=conversation_url)
                    return False
                finally:
                    try:
                        if self._session._ctx is not None and len(self._session._ctx.pages) <= 1:
                            await page.goto("about:blank")
                        else:
                            await page.close()
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("provider_delete_conversation_error", provider=self.name, url=conversation_url, error=str(exc))
            return False
