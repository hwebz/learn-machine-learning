from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any

import structlog

from app.browser.locators import SelectorChain, resolve_locator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CompletionResult:
    done: bool
    reason: str  # stable | done_marker | blocked | timeout | error
    text: str
    blocking_detail: str | None = None


@dataclass(frozen=True, slots=True)
class BlockingState:
    kind: str  # login | captcha | verification | rate_limit
    detail: str


_TARGET_CLOSED_MARKERS = (
    "Target page, context or browser has been closed",
    "Target closed",
    "Browser has been closed",
)


def is_target_closed_error(exc: BaseException) -> bool:
    """True when a Playwright error means the tab/browser is gone (not just slow)."""
    text = str(exc)
    return any(marker in text for marker in _TARGET_CLOSED_MARKERS)


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without a browser)
# ---------------------------------------------------------------------------


def match_blocking_url(url: str, patterns: list[str]) -> str | None:
    lowered = url.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return pattern
    return None


def match_blocking_text(text: str, patterns: list[str]) -> str | None:
    if not isinstance(text, str):
        return None
    lowered = text.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return pattern
    return None


def classify_blocking(pattern: str) -> str:
    p = pattern.lower()
    if "captcha" in p or "verify" in p or "unusual traffic" in p:
        return "captcha"
    if "rate" in p or "limit" in p:
        return "rate_limit"
    if "login" in p or "signin" in p or "sign in" in p or "accounts.google" in p:
        return "login"
    return "verification"


def evaluate_completion(
    *,
    input_editable: bool,
    text_stable: bool,
    done_marker_visible: bool,
    generating: bool = False,
) -> tuple[bool, str]:
    """Complete when a done marker (e.g. Copy button) is visible AND generation
    has finished, or when the model is not generating, the answer text is stable,
    and input is editable.
    """
    if generating:
        return False, "in_progress"
    if done_marker_visible:
        return True, "done_marker"
    if input_editable and text_stable:
        return True, "stable"
    return False, "in_progress"


class StabilityTracker:
    """Tracks answer text stability over time (pure, clock injectable)."""

    def __init__(self, stable_seconds: float, clock: Any = time.monotonic) -> None:
        self.stable_seconds = stable_seconds
        self._clock = clock
        self._prev_text: str | None = None
        self._stable_since: float | None = None

    def update(self, text: str) -> bool:
        """Feed the latest answer text; return True once text has been unchanged
        for at least stable_seconds (non-empty text required)."""
        now = self._clock()
        if not text.strip():
            self._prev_text = text
            self._stable_since = None
            return False
        if text != self._prev_text:
            self._prev_text = text
            self._stable_since = now
            return False
        if self._stable_since is None:
            self._stable_since = now
            return False
        return (now - self._stable_since) >= self.stable_seconds


# ---------------------------------------------------------------------------
# Page-dependent detection
# ---------------------------------------------------------------------------


async def wait_for_input(
    page: Any,
    question_input: SelectorChain,
    *,
    timeout_s: float = 30,
    poll_s: float = 1.0,
) -> Any | None:
    """Poll until any rung of the input chain matches, network conditions permitting.

    SPAs (e.g., Mistral) hydrate their editors several seconds after page load,
    and the delay varies with the network — so poll instead of sleeping a fixed
    amount. Returns the first matching locator, or None on timeout.
    """
    import time as _time

    deadline = _time.monotonic() + timeout_s
    while True:
        locator, rung = await resolve_locator(page, question_input)
        if locator is not None:
            return locator
        if _time.monotonic() >= deadline:
            return None
        await asyncio.sleep(poll_s)


DOM_EXTRACT_NON_CONVERSATION_TEXT = """
() => {
    // 1. Check for Cloudflare / bot challenge containers first
    const challenge = document.querySelector(
        '#challenge-stage, .cf-turnstile, iframe[src*="cloudflare"], iframe[src*="challenges"], iframe[src*="arkose"], iframe[src*="recaptcha"], iframe[src*="turnstile"]'
    );
    if (challenge) {
        return document.body ? (document.body.innerText || '') : '';
    }

    // 2. Selectors that represent user & assistant chat messages, inputs, thinking containers
    const excludeSelector = [
        'article',
        '[data-message-author-role]',
        '[data-message-id]',
        '[data-message-part-type]',
        '.conversation-turn',
        '[data-testid*="conversation"]',
        '[data-testid*="chat-message"]',
        '[data-testid*="user-message"]',
        '[data-testid*="assistant-message"]',
        '[data-testid*="harness"]',
        '[data-testid*="thinking"]',
        '.agent-turn',
        '#prompt-textarea',
        'textarea',
        '[contenteditable="true"]',
        '.markdown',
        '.prose',
        'pre',
        'code',
        '[data-markdown-text-style]',
        '[class*="MarkdownRoot"]',
        '[class*="markdown-container"]',
        '[class*="thinking"]',
        '[class*="canvas"]',
        '[class*="collapsible-content"]',
        '[id*="collapsible-content"]',
        '.chat-assistant',
        '[class*="chat-assistant"]',
        'div.chat-assistant'
    ].join(', ');

    const excludedNodes = document.querySelectorAll(excludeSelector);
    if (!excludedNodes || excludedNodes.length === 0) {
        return document.body ? (document.body.innerText || '') : '';
    }

    const isInsideExcluded = (el) => {
        if (!el) return false;
        if (el.nodeType === Node.TEXT_NODE) el = el.parentElement;
        return el ? Boolean(el.closest(excludeSelector)) : false;
    };

    // 3. Modals, dialogs, toasts, error banners (NEVER inside conversation/message containers!)
    const alertSelector = [
        '[role="alert"]',
        '[role="alertdialog"]',
        '[role="dialog"]:not([data-message-author-role] *)',
        'div[aria-modal="true"]',
        '.toast',
        '[data-testid*="toast"]',
        '[data-testid*="error"]',
        'div[class*="error"]:not([data-message-author-role] *)',
        'div[class*="banner"]'
    ].join(', ');

    const alertElements = Array.from(document.querySelectorAll(alertSelector))
        .filter(el => !isInsideExcluded(el));
    let alertText = alertElements.map(el => el.innerText || '').join(' ');

    // 4. Gather text from visible elements in body that are NOT inside excludeSelector
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
        acceptNode: (node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
                const tag = node.tagName.toLowerCase();
                if (['script', 'style', 'noscript', 'template'].includes(tag)) {
                    return NodeFilter.FILTER_REJECT;
                }
                if (node.matches && (node.matches(excludeSelector) || isInsideExcluded(node))) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_SKIP;
            }
            if (node.nodeType === Node.TEXT_NODE) {
                if (isInsideExcluded(node)) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
            return NodeFilter.FILTER_SKIP;
        }
    });

    let otherText = '';
    while (walker.nextNode()) {
        const val = walker.currentNode.nodeValue;
        if (val && val.trim()) {
            otherText += ' ' + val.trim();
        }
    }

    return (alertText + ' ' + otherText).trim();
}
"""


async def detect_blocking_state(page: Any, blocking: dict[str, Any]) -> BlockingState | None:
    """Check URL + visible text against blocking patterns. Never attempts bypass.

    Raises when the page/browser has been closed — callers must not treat a
    dead tab as a slow-loading page.
    """
    url = getattr(page, "url", "") or ""
    url_pattern = match_blocking_url(url, blocking.get("url_patterns", []) or [])
    if url_pattern:
        return BlockingState(kind=classify_blocking(url_pattern), detail=f"URL matched pattern {url_pattern!r}: {url}")

    text: str | None = None
    if hasattr(page, "evaluate"):
        try:
            res = await page.evaluate(DOM_EXTRACT_NON_CONVERSATION_TEXT)
            if isinstance(res, str):
                text = res
        except Exception as exc:  # noqa: BLE001
            if is_target_closed_error(exc):
                raise
            text = None

    if text is None:
        try:
            has_messages = False
            if hasattr(page, "locator"):
                try:
                    count = await page.locator(
                        "[data-message-author-role], article, [data-testid*='conversation'], .conversation-turn"
                    ).count()
                    has_messages = count > 0
                except Exception:
                    pass
            # Only fall back to body.inner_text() if NO conversation elements exist
            if not has_messages and hasattr(page, "locator"):
                res_locator = await page.locator("body").inner_text(timeout=3000)
                if isinstance(res_locator, str):
                    text = res_locator
        except Exception as exc:  # noqa: BLE001 — page may still be loading
            if is_target_closed_error(exc):
                raise
            text = ""

    text_pattern = match_blocking_text(text or "", blocking.get("text_patterns", []) or [])
    if text_pattern:
        return BlockingState(kind=classify_blocking(text_pattern), detail=f"Visible text matched pattern {text_pattern!r}")
    return None


async def _answer_text(page: Any, answer_container: SelectorChain, provider: str = "") -> str:
    locator, _ = await resolve_locator(page, answer_container)
    if locator is None:
        return ""
    try:
        count = await locator.count()
        if count == 0:
            return ""
        target = locator
        if count > 1 and hasattr(locator, "last"):
            target = locator.last
        if provider != "chatgpt":
            try:
                html = await target.inner_html(timeout=2000)
                if html and ("<" in html and ">" in html):
                    from app.browser.extraction import clean_markdown_text, html_to_markdown
                    markdown = html_to_markdown(html, provider=provider)
                    if markdown and markdown.strip():
                        return clean_markdown_text(markdown)
            except Exception:
                pass
        return (await target.inner_text(timeout=3000)).strip()
    except Exception as exc:  # noqa: BLE001
        if is_target_closed_error(exc):
            raise
        return ""


async def _indicator_visible(page: Any, chain: SelectorChain | None) -> bool:
    if not chain:
        return False
    locator, _ = await resolve_locator(page, chain)
    if locator is None:
        return False
    try:
        count = await locator.count()
        if count == 0:
            return False
        if hasattr(locator, "nth"):
            for i in range(count):
                if await locator.nth(i).is_visible(timeout=500):
                    return True
            return False
        return await locator.is_visible(timeout=500)
    except Exception as exc:  # noqa: BLE001
        if is_target_closed_error(exc):
            raise
        return False


async def _input_editable(page: Any, question_input: SelectorChain) -> bool:
    locator, _ = await resolve_locator(page, question_input)
    if locator is None:
        return False
    try:
        count = await locator.count()
        if count == 0:
            return False
        target = locator
        if count > 1 and hasattr(locator, "first"):
            target = locator.first
        return await target.is_editable(timeout=1000)
    except Exception as exc:  # noqa: BLE001
        if is_target_closed_error(exc):
            raise
        return False


from app.browser.dom_scripts import DOM_SCAN_THINKING_AND_CITATIONS


async def wait_for_completion(
    page: Any,
    *,
    provider: str = "",
    provider_cfg: dict[str, Any],
    blocking: dict[str, Any],
    completion_cfg: dict[str, Any],
    timeout_s: float,
    on_poll: Any | None = None,
    response_ready: Any | None = None,
    thinking_interval_s: float | None = None,
    response_interval_s: float | None = None,
    clock: Any = time.monotonic,
    sleep: Any = asyncio.sleep,
) -> CompletionResult:
    """Poll until the chatbot finishes generating, blocked, or timeout_s elapses."""
    stable_s = float(completion_cfg.get("stable_seconds", 5))
    poll_s = float(completion_cfg.get("poll_interval_s", 2))
    min_poll = float(completion_cfg.get("min_poll_s", poll_s))
    max_poll = float(completion_cfg.get("max_poll_s", poll_s))
    # Optional per-provider delay after done_marker appears (e.g., Mistral renders
    # copy button before answer text is populated)
    done_marker_delay_s = float(completion_cfg.get("done_marker_delay_s", 0))

    question_input = provider_cfg.get("question_input", [])
    generating_chain = provider_cfg.get("generating_indicator")
    done_chain = provider_cfg.get("done_indicator")
    answer_chain = provider_cfg.get("answer_container", [])

    tracker = StabilityTracker(stable_s, clock=clock)
    start_time = clock()
    deadline = start_time + timeout_s
    last_text = ""
    poll_count = 0

    while clock() < deadline:
        try:
            generating = await _indicator_visible(page, generating_chain)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        ready: bool | None = None
        if response_ready is not None:
            try:
                ready = await response_ready(page)
            except Exception as exc:
                if is_target_closed_error(exc):
                    return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
                raise

        is_actively_generating = generating or (ready is False)

        try:
            state = await detect_blocking_state(page, blocking)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise
        if state is not None:
            is_real_block = True
            if state.detail.startswith("Visible text") and is_actively_generating:
                has_challenge_container = False
                if hasattr(page, "locator"):
                    try:
                        challenge_loc = page.locator(
                            '#challenge-stage, .cf-turnstile, iframe[src*="cloudflare"], iframe[src*="challenges"], iframe[src*="arkose"], iframe[src*="recaptcha"]'
                        )
                        if await challenge_loc.count() > 0 and await challenge_loc.first.is_visible(timeout=200):
                            has_challenge_container = True
                    except Exception:
                        pass
                if not has_challenge_container:
                    is_real_block = False
                    logger.warning(
                        "blocking_text_pattern_suppressed_during_generation",
                        detail=state.detail,
                        provider=provider,
                    )
            if is_real_block:
                return CompletionResult(done=False, reason="blocked", text=last_text, blocking_detail=state.detail)

        try:
            editable = await _input_editable(page, question_input)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        try:
            last_text = await _answer_text(page, answer_chain, provider=provider)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        try:
            done_marker = await _indicator_visible(page, done_chain)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        text_stable = tracker.update(last_text)

        done, reason = evaluate_completion(
            input_editable=editable,
            text_stable=text_stable,
            done_marker_visible=done_marker,
            generating=generating,
        )

        if ready is False:
            done, reason = False, "in_progress"
            generating = True
        elif ready is True:
            done, reason = True, "media_ready"
            generating = False

        poll_count += 1
        elapsed = clock() - start_time
        if generating:
            state_desc = "thinking / generating"
        elif done_marker:
            state_desc = "done marker visible (copy button)"
        elif text_stable:
            state_desc = "text stable (generation finished)"
        elif last_text:
            state_desc = f"streaming text ({len(last_text)} chars)"
        else:
            state_desc = "waiting for response"

        # Check thinking & citations in DOM with provider-specific logic
        scan_data: dict[str, Any] = {"is_thinking": False, "thinking_text": "", "thinking_steps": [], "citations": []}
        try:
            raw_scan = await page.evaluate(DOM_SCAN_THINKING_AND_CITATIONS, provider)
            if isinstance(raw_scan, dict):
                scan_data = raw_scan
        except Exception as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            logger.debug("dom_scan_eval_failed", error=str(exc))

        is_thinking = bool(scan_data.get("is_thinking") or generating)
        thinking_text = str(scan_data.get("thinking_text") or "")
        thinking_steps = list(scan_data.get("thinking_steps") or [])
        citations = scan_data.get("citations", [])

        if on_poll is not None:
            try:
                await on_poll(
                    state=state_desc,
                    generating=generating,
                    is_thinking=is_thinking,
                    thinking_text=thinking_text,
                    thinking_steps=thinking_steps,
                    citations=citations,
                    last_text=last_text,
                    poll_count=poll_count,
                    elapsed_s=round(elapsed, 1),
                )
            except Exception as exc:
                logger.debug("on_poll_callback_failed", error=str(exc))

        logger.info(
            "wait_for_completion_poll",
            poll=poll_count,
            elapsed_s=round(elapsed, 1),
            state=state_desc,
            generating=generating,
            is_thinking=is_thinking,
            citations_count=len(citations),
            done_marker=done_marker,
            text_len=len(last_text),
            text_stable=text_stable,
        )

        if done:
            if reason == "done_marker" and done_marker_delay_s > 0:
                # Mistral renders the copy button skeleton before populating the
                # answer text — give the UI time to catch up, then re-read.
                logger.info("done_marker_delay", delay_s=done_marker_delay_s, provider=provider_cfg.get("name", ""))
                await sleep(done_marker_delay_s)
                last_text = await _answer_text(page, answer_chain, provider=provider)
            return CompletionResult(done=True, reason=reason, text=last_text)

        # In thinking/generating mode, use response_interval_s when answer text is streaming,
        # or thinking_interval_s when in thinking mode
        is_streaming_response = bool(last_text and not text_stable)
        if generating or is_thinking or is_streaming_response:
            if last_text and response_interval_s is not None:
                effective_interval = response_interval_s
            elif thinking_interval_s is not None:
                effective_interval = thinking_interval_s
            elif response_interval_s is not None:
                effective_interval = response_interval_s
            else:
                effective_interval = 1.0
            await sleep(effective_interval)
        else:
            await sleep(random.uniform(min_poll, max_poll))

    return CompletionResult(done=False, reason="timeout", text=last_text)
