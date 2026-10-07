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
    lowered = (text or "").lower()
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
    """Complete when a done marker (e.g. Copy button) is visible, or when
    the model is not generating, the answer text is stable, and input is editable.
    """
    if done_marker_visible:
        return True, "done_marker"
    if generating:
        return False, "in_progress"
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


async def detect_blocking_state(page: Any, blocking: dict[str, Any]) -> BlockingState | None:
    """Check URL + visible text against blocking patterns. Never attempts bypass.

    Raises when the page/browser has been closed — callers must not treat a
    dead tab as a slow-loading page.
    """
    url = getattr(page, "url", "") or ""
    url_pattern = match_blocking_url(url, blocking.get("url_patterns", []) or [])
    if url_pattern:
        return BlockingState(kind=classify_blocking(url_pattern), detail=f"URL matched pattern {url_pattern!r}: {url}")

    text = ""
    try:
        text = await page.locator("body").inner_text(timeout=3000)
    except Exception as exc:  # noqa: BLE001 — page may still be loading
        if is_target_closed_error(exc):
            raise
        pass
    text_pattern = match_blocking_text(text, blocking.get("text_patterns", []) or [])
    if text_pattern:
        return BlockingState(kind=classify_blocking(text_pattern), detail=f"Visible text matched pattern {text_pattern!r}")
    return None


async def _answer_text(page: Any, answer_container: SelectorChain) -> str:
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


async def wait_for_completion(
    page: Any,
    *,
    provider_cfg: dict[str, Any],
    blocking: dict[str, Any],
    completion_cfg: dict[str, Any],
    timeout_s: float,
    clock: Any = time.monotonic,
    sleep: Any = asyncio.sleep,
) -> CompletionResult:
    """Poll until the chatbot finishes generating, blocked, or timeout_s elapses."""
    stable_s = float(completion_cfg.get("stable_seconds", 5))
    poll_s = float(completion_cfg.get("poll_interval_s", 2))
    min_poll = float(completion_cfg.get("min_poll_s", poll_s))
    max_poll = float(completion_cfg.get("max_poll_s", poll_s))

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
            state = await detect_blocking_state(page, blocking)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise
        if state is not None:
            return CompletionResult(done=False, reason="blocked", text=last_text, blocking_detail=state.detail)

        try:
            generating = await _indicator_visible(page, generating_chain)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        try:
            editable = await _input_editable(page, question_input)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        try:
            last_text = await _answer_text(page, answer_chain)
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

        logger.info(
            "wait_for_completion_poll",
            poll=poll_count,
            elapsed_s=round(elapsed, 1),
            state=state_desc,
            generating=generating,
            done_marker=done_marker,
            text_len=len(last_text),
            text_stable=text_stable,
        )

        if done:
            return CompletionResult(done=True, reason=reason, text=last_text)

        # jittered poll between min_poll and max_poll
        await sleep(random.uniform(min_poll, max_poll))

    return CompletionResult(done=False, reason="timeout", text=last_text)
