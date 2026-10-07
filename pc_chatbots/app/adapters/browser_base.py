from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from app.adapters.base import HealthStatus, ProviderResult, Source
from app.adapters.selectors_loader import load_selectors, provider_selectors
from app.browser.artifacts import save_artifacts
from app.browser.extraction import html_to_markdown, normalize_sources
from app.browser.locators import resolve_locator
from app.browser.session import BrowserSession
from app.browser.waits import wait_for_completion
from app.core.config import settings

logger = structlog.get_logger(__name__)


class ProviderNeedsUserAction(RuntimeError):
    """Raised when the adapter cannot proceed without human help (login, CAPTCHA, rate limit)."""


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
        self._session = session or BrowserSession.instance()
        self._selectors = selectors if selectors is not None else load_selectors()
        self._artifact_dir = artifact_dir or settings.artifact_dir
        self._cfg = provider_selectors(self._selectors, self.name)

    # ------------------------------------------------------------- health

    async def health(self) -> HealthStatus:
        """Static health: selectors present + profile dir exists. Never launches a browser."""
        try:
            provider_selectors(self._selectors, self.name)
            selectors_ok = True
            detail = "Selectors configured"
        except Exception as exc:  # noqa: BLE001
            selectors_ok = False
            detail = f"Selector config error: {exc}"
        profile_dir = settings.browser_profile_dir
        logged_in = profile_dir.is_dir() and any(profile_dir.iterdir())
        if not logged_in:
            detail = f"{detail}; profile dir empty or missing — run scripts/login_profile.py"
        return HealthStatus(logged_in=logged_in, selectors_ok=selectors_ok, detail=detail)

    # ------------------------------------------------------------- hooks

    @abstractmethod
    async def _select_mode(self, page: Any, mode: str) -> None:
        """Optionally switch the site's research/pro mode. Must be best-effort."""

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        # 1. Attempt to use the site's Copy button if available (cleanest Markdown)
        done_chain = self._cfg.get("done_indicator", [])
        if done_chain:
            copy_locator, _ = await resolve_locator(page, done_chain)
            if copy_locator is not None:
                try:
                    count = await copy_locator.count()
                    if count > 0:
                        target_btn = copy_locator.last if count > 1 else copy_locator.first
                        await target_btn.click(timeout=2000)
                        await asyncio.sleep(0.3)
                        clipboard_text = await page.evaluate("navigator.clipboard.readText()")
                        if (
                            clipboard_text
                            and len(clipboard_text.strip()) > 10
                            and clipboard_text.strip().lower() != prompt.strip().lower()
                        ):
                            logger.info("answer_copied_from_clipboard", provider=self.name, length=len(clipboard_text))
                            return clipboard_text.strip()
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
            markdown = html_to_markdown(html)
            if markdown.strip():
                return markdown.strip()
            return (await target.inner_text(timeout=5000)).strip()
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
                if href:
                    pairs.append((href, text or None))
        except Exception:  # noqa: BLE001
            return []
        return normalize_sources(pairs)

    # ------------------------------------------------------------- ask flow

    async def ask(self, prompt: str, *, timeout_s: int, mode: str = "default") -> ProviderResult:
        started_at = datetime.now(timezone.utc)
        bucket = _bucket_for(self.name)
        if not bucket.try_acquire():
            raise ProviderNeedsUserAction(
                f"Rate limit reached for {self.name} ({settings.max_questions_per_hour}/hour)."
            )

        # Defensive jitter between questions (dispatcher also delays).
        await asyncio.sleep(random.uniform(settings.min_delay_between_questions_s, settings.max_delay_between_questions_s))

        job_tag = f"ui-{self.name}-{int(time.time())}"
        artifact_paths: list[str] = []
        status: str = "ok"
        error: str | None = None
        answer = ""
        completion_text = ""
        sources: list[Source] = []
        conversation_url: str | None = None

        try:
            async with self._session.exclusive():
                page = await self._session.new_page(self._cfg["new_chat_url"])
                try:
                    from app.browser.waits import detect_blocking_state

                    blocking = await detect_blocking_state(page, self._selectors.get("blocking", {}))
                    if blocking is not None:
                        status = "needs_user_action"
                        error = f"Blocked ({blocking.kind}): {blocking.detail}. Complete login/CAPTCHA in the browser, then retry."
                    else:
                        await self._select_mode(page, mode)

                        input_locator, _ = await resolve_locator(page, self._cfg.get("question_input", []))
                        if input_locator is None:
                            status = "error"
                            error = "Question input locator not found — selectors may be stale. See selectors.yaml and data/artifacts."
                        else:
                            # Click to focus, then type. fill() does not work reliably on
                            # contenteditable rich-text editors (Perplexity/Gemini), and the
                            # submit button often only appears after text is entered.
                            try:
                                await input_locator.click(timeout=5000)
                            except Exception:  # noqa: BLE001 — fall back to fill on real <textarea>/<input>
                                pass
                            try:
                                await input_locator.fill(prompt, timeout=10000)
                            except Exception:  # noqa: BLE001 — contenteditable: use type() instead
                                try:
                                    await input_locator.click(timeout=5000)
                                    await input_locator.type(prompt, delay=15)
                                except Exception as exc2:  # noqa: BLE001
                                    status = "error"
                                    error = f"Could not enter prompt: {type(exc2).__name__}: {exc2}"
                            if status != "error":
                                await asyncio.sleep(0.75)  # let the submit button render
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
                            if status not in {"error", "needs_user_action"}:
                                completion = await wait_for_completion(
                                    page,
                                    provider_cfg=self._cfg,
                                    blocking=self._selectors.get("blocking", {}),
                                    completion_cfg=self._selectors.get("completion", {}),
                                    timeout_s=timeout_s,
                                )
                                completion_text = completion.text
                                if completion.reason == "blocked":
                                    status = "needs_user_action"
                                    error = f"Blocked during generation: {completion.blocking_detail}"
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
                            answer = await self._extract_answer(page, prompt=prompt) or completion_text
                            sources = await self._extract_sources(page)
                            if not answer.strip():
                                status = "partial" if status == "partial" else "error"
                                error = error or "Extracted answer was empty"
                        except RuntimeError as exc:
                            if "closed" in str(exc).lower():
                                status = "error"
                                error = error or "Browser tab closed while extracting answer"
                            else:
                                raise

                    try:
                        raw_url = page.url
                        conversation_url = raw_url if raw_url.startswith(("http://", "https://")) else None
                    except Exception:  # noqa: BLE001
                        conversation_url = None
                finally:
                    artifact_paths = await save_artifacts(
                        page,
                        job_tag=job_tag,
                        provider=self.name,
                        artifact_dir=self._artifact_dir,
                    )
                    try:
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
