from __future__ import annotations

import pytest

from app.browser.waits import (
    StabilityTracker,
    classify_blocking,
    evaluate_completion,
    is_target_closed_error,
    match_blocking_text,
    match_blocking_url,
)


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_match_blocking_url_detects_login_redirect() -> None:
    patterns = ["accounts.google.com", "/login", "/signin"]
    assert match_blocking_url("https://accounts.google.com/v3/signin/identifier", patterns) == "accounts.google.com"
    assert match_blocking_url("https://gemini.google.com/app", patterns) is None


def test_match_blocking_text_detects_captcha() -> None:
    patterns = ["Verify you are human", "captcha", "rate limit"]
    assert match_blocking_text("Please Verify you are human to continue", patterns) == "Verify you are human"
    assert match_blocking_text("Rate limit exceeded", patterns) == "rate limit"
    assert match_blocking_text("Here is an answer about solar panels.", patterns) is None


def test_classify_blocking_kinds() -> None:
    assert classify_blocking("Verify you are human") == "captcha"
    assert classify_blocking("rate limit") == "rate_limit"
    assert classify_blocking("/login") == "login"
    assert classify_blocking("accounts.google.com") == "login"
    assert classify_blocking("/auth/login") == "login"


def test_evaluate_completion_signals() -> None:
    # (1) input enabled AND (2) stable
    assert evaluate_completion(input_editable=True, text_stable=True, done_marker_visible=False) == (True, "stable")
    # done marker mid-generation does NOT complete (ChatGPT renders the user's
    # copy button while still streaming the answer)
    assert evaluate_completion(input_editable=False, text_stable=False, done_marker_visible=True, generating=True) == (False, "in_progress")
    # done marker after generation finishes completes
    assert evaluate_completion(input_editable=False, text_stable=False, done_marker_visible=True, generating=False) == (True, "done_marker")
    # generating indicator active suppresses stable
    assert evaluate_completion(input_editable=True, text_stable=True, done_marker_visible=False, generating=True) == (False, "in_progress")
    # input still disabled (submitting)
    assert evaluate_completion(input_editable=False, text_stable=True, done_marker_visible=False) == (False, "in_progress")
    # text still changing
    assert evaluate_completion(input_editable=True, text_stable=False, done_marker_visible=False) == (False, "in_progress")


def test_stability_tracker_requires_elapsed_and_unchanged_text() -> None:
    clock = FakeClock()
    tracker = StabilityTracker(stable_seconds=8, clock=clock)

    assert tracker.update("") is False  # empty text never counts as stable
    assert tracker.update("Hello") is False  # first observation
    clock.advance(5)
    assert tracker.update("Hello") is False  # only 5s elapsed
    clock.advance(4)
    assert tracker.update("Hello") is True  # 9s unchanged

    # text change resets the window
    clock.advance(1)
    assert tracker.update("Hello world") is False
    clock.advance(3)
    assert tracker.update("Hello world") is False
    clock.advance(6)
    assert tracker.update("Hello world") is True


def test_is_target_closed_error_detects_closed_tab() -> None:
    assert is_target_closed_error(RuntimeError("Target page, context or browser has been closed")) is True
    assert is_target_closed_error(Exception("Target closed")) is True
    assert is_target_closed_error(ValueError("Browser has been closed")) is True
    assert is_target_closed_error(RuntimeError("Timeout")) is False
    assert is_target_closed_error(Exception("Other error")) is False


@pytest.mark.asyncio
async def test_wait_for_completion_stable_text_completes() -> None:
    from app.browser.waits import wait_for_completion

    clock = FakeClock()

    class FakeLocator:
        def __init__(self, *, visible: bool = False, editable: bool = False, text: str = "") -> None:
            self._visible = visible
            self._editable = editable
            self._text = text

        async def count(self) -> int:
            return 1

        async def is_visible(self, timeout: int | None = None) -> bool:
            return self._visible

        async def is_editable(self, timeout: int | None = None) -> bool:
            return self._editable

        async def inner_text(self, timeout: int | None = None) -> str:
            return self._text

    class FakePage:
        url = "https://www.perplexity.ai/"

        def get_by_role(self, role: str, name: str | None = None, **kwargs: object) -> FakeLocator:
            if role == "textbox":
                return FakeLocator(editable=True)
            return FakeLocator()

        def get_by_test_id(self, testid: str) -> FakeLocator:
            if testid == "answer":
                return FakeLocator(text="The A320 is an airliner.")
            return FakeLocator()

        def locator(self, css: str) -> FakeLocator:
            if "prose" in css or "markdown" in css:
                return FakeLocator(text="The A320 is an airliner.")
            return FakeLocator()

        def get_by_placeholder(self, placeholder: str) -> FakeLocator:
            return FakeLocator(editable=True)

    provider_cfg = {
        "question_input": [{"role": "textbox", "name": "Ask anything"}],
        "generating_indicator": [{"testid": "generating"}],
        "answer_container": [{"testid": "answer"}, {"css": "div.prose"}],
        "done_indicator": [],
    }
    blocking = {"url_patterns": [], "text_patterns": []}
    completion_cfg = {"stable_seconds": 8, "poll_interval_s": 2, "min_poll_s": 1, "max_poll_s": 2}

    async def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    result = await wait_for_completion(
        FakePage(),
        provider_cfg=provider_cfg,
        blocking=blocking,
        completion_cfg=completion_cfg,
        timeout_s=30,
        clock=clock,
        sleep=fake_sleep,
    )
    assert result.done is True
    assert result.reason == "stable"
    assert "A320" in result.text


@pytest.mark.asyncio
async def test_wait_for_completion_page_closed_returns_immediately() -> None:
    """A closed tab must abort the wait, not poll until timeout."""
    from app.browser.waits import wait_for_completion

    clock = FakeClock()

    class ClosedLocator:
        async def count(self) -> int:
            return 1

        async def is_editable(self, timeout: int | None = None) -> bool:
            raise RuntimeError("Page.is_editable: Target page, context or browser has been closed")

        async def is_visible(self, timeout: int | None = None) -> bool:
            raise RuntimeError("Page.is_visible: Target page, context or browser has been closed")

        async def inner_text(self, timeout: int | None = None) -> str:
            raise RuntimeError("Page.inner_text: Target page, context or browser has been closed")

    class ClosedPage:
        url = "https://www.perplexity.ai/"

        def get_by_role(self, role: str, name: str | None = None, **kwargs: object) -> ClosedLocator:
            return ClosedLocator()

        def get_by_test_id(self, testid: str) -> ClosedLocator:
            return ClosedLocator()

        def locator(self, css: str) -> ClosedLocator:
            return ClosedLocator()

        def get_by_placeholder(self, placeholder: str) -> ClosedLocator:
            return ClosedLocator()

        def get_by_text(self, text: str, **kwargs: object) -> ClosedLocator:
            return ClosedLocator()

    provider_cfg = {
        "question_input": [{"role": "textbox"}],
        "answer_container": [{"css": "div.prose"}],
        "done_indicator": [],
    }
    blocking = {"url_patterns": [], "text_patterns": []}
    completion_cfg = {"stable_seconds": 8, "poll_interval_s": 2, "min_poll_s": 1, "max_poll_s": 2}

    sleep_calls = 0

    async def fake_sleep(seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        clock.advance(seconds)

    result = await wait_for_completion(
        ClosedPage(),
        provider_cfg=provider_cfg,
        blocking=blocking,
        completion_cfg=completion_cfg,
        timeout_s=1200,
        clock=clock,
        sleep=fake_sleep,
    )
    assert result.done is False
    assert result.reason == "page_closed"
    assert sleep_calls == 0  # aborted on first poll, never slept
