from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.config import _parse_interval
from app.core.models import Job, Source, utc_now
from app.browser.waits import DOM_SCAN_THINKING_AND_CITATIONS, wait_for_completion


def test_parse_interval_formats() -> None:
    assert _parse_interval("1s") == 1.0
    assert _parse_interval("1.5s") == 1.5
    assert _parse_interval("500ms") == 0.5
    assert _parse_interval("2") == 2.0
    assert _parse_interval("invalid", default=1.0) == 1.0


def test_source_model_fields() -> None:
    src = Source(
        id="job-123:S1",
        run_id="job-123:copilot:run",
        job_id="job-123",
        provider="copilot",
        url="https://example.com/ai-paper",
        title="AI Paper Title",
        snippet="Snippet text",
    )
    assert src.job_id == "job-123"
    assert src.provider == "copilot"
    assert src.url == "https://example.com/ai-paper"
    assert src.title == "AI Paper Title"
    assert src.created_at is not None


def test_dom_scan_script_syntax() -> None:
    assert "thinking_text" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "thinking_steps" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "citations" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "is_thinking" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "qwen-chat-status-card-after" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "scc-ChainOfThought" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "sources-button-testid" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "fai-BebopCitation" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "data-grouped-citations" in DOM_SCAN_THINKING_AND_CITATIONS
    assert ".ds-markdown--thought" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "data-testid='citation'" in DOM_SCAN_THINKING_AND_CITATIONS


@pytest.mark.asyncio
async def test_wait_for_completion_triggers_on_poll() -> None:
    poll_events: list[dict] = []

    async def mock_on_poll(**kwargs) -> None:
        poll_events.append(kwargs)

    mock_page = MagicMock()
    mock_page.url = "https://copilot.microsoft.com"
    mock_page.locator.return_value.inner_text = AsyncMock(return_value="Some answer text")
    mock_page.evaluate = AsyncMock(return_value={
        "is_thinking": True,
        "thinking_text": "Evaluating multi-model consensus...",
        "citations": [{"url": "https://arxiv.org/abs/1234", "title": "Consensus Paper"}],
    })

    clock_val = 1000.0

    def fake_clock() -> float:
        nonlocal clock_val
        clock_val += 0.5
        return clock_val

    sleep_called_intervals: list[float] = []

    async def fake_sleep(dur: float) -> None:
        sleep_called_intervals.append(dur)

    provider_cfg = {
        "question_input": [],
        "answer_container": [],
        "generating_indicator": None,
        "done_indicator": None,
    }

    result = await wait_for_completion(
        mock_page,
        provider_cfg=provider_cfg,
        blocking={},
        completion_cfg={"stable_seconds": 0.5, "poll_interval_s": 1.0},
        timeout_s=2.0,
        on_poll=mock_on_poll,
        thinking_interval_s=1.0,
        clock=fake_clock,
        sleep=fake_sleep,
    )

    assert len(poll_events) > 0
    first_poll = poll_events[0]
    assert first_poll["is_thinking"] is True
    assert first_poll["thinking_text"] == "Evaluating multi-model consensus..."
    assert len(first_poll["citations"]) == 1
    assert first_poll["citations"][0]["url"] == "https://arxiv.org/abs/1234"
    assert 1.0 in sleep_called_intervals


@pytest.mark.asyncio
async def test_wait_for_completion_qwen_thinking_steps() -> None:
    poll_events: list[dict] = []

    async def mock_on_poll(**kwargs) -> None:
        poll_events.append(kwargs)

    mock_page = MagicMock()
    mock_page.url = "https://chat.qwenlm.ai"
    mock_page.locator.return_value.inner_text = AsyncMock(return_value="Qwen response")
    mock_page.evaluate = AsyncMock(return_value={
        "is_thinking": True,
        "thinking_text": "Searching the web:\nQuery: python\n\nReading sources...",
        "thinking_steps": [
            {"title": "Searching the web", "description": "Query: python", "status": "completed"},
            {"title": "Reading sources...", "description": "Analyzing 3 docs", "status": "running"},
        ],
        "citations": [{"url": "https://python.org", "title": "Python Official"}],
    })

    clock_val = 1000.0

    def fake_clock() -> float:
        nonlocal clock_val
        clock_val += 0.5
        return clock_val

    async def fake_sleep(dur: float) -> None:
        pass

    provider_cfg = {
        "question_input": [],
        "answer_container": [],
        "generating_indicator": None,
        "done_indicator": None,
    }

    result = await wait_for_completion(
        mock_page,
        provider="qwen",
        provider_cfg=provider_cfg,
        blocking={},
        completion_cfg={"stable_seconds": 0.5, "poll_interval_s": 1.0},
        timeout_s=2.0,
        on_poll=mock_on_poll,
        clock=fake_clock,
        sleep=fake_sleep,
    )

    assert len(poll_events) > 0
    first_poll = poll_events[0]
    assert first_poll["is_thinking"] is True
    assert len(first_poll["thinking_steps"]) == 2
    assert first_poll["thinking_steps"][0]["title"] == "Searching the web"
    assert first_poll["thinking_steps"][0]["description"] == "Query: python"
    assert first_poll["thinking_steps"][0]["status"] == "completed"
    assert first_poll["thinking_steps"][1]["title"] == "Reading sources..."


@pytest.mark.asyncio
async def test_wait_for_completion_copilot_thinking_steps() -> None:
    poll_events: list[dict] = []

    async def mock_on_poll(**kwargs) -> None:
        poll_events.append(kwargs)

    mock_page = MagicMock()
    mock_page.url = "https://m365.cloud.microsoft/chat"
    mock_page.locator.return_value.inner_text = AsyncMock(return_value="Copilot response")
    mock_page.evaluate = AsyncMock(return_value={
        "is_thinking": True,
        "thinking_text": "Understanding question\nSearching web sources",
        "thinking_steps": [
            {"title": "Understanding question", "description": "Analyzing intent", "status": "completed"},
            {"title": "Searching web sources", "description": "Querying Bing", "status": "running"},
        ],
        "citations": [{"url": "https://microsoft.com", "title": "Microsoft Official"}],
    })

    clock_val = 1000.0

    def fake_clock() -> float:
        nonlocal clock_val
        clock_val += 0.5
        return clock_val

    async def fake_sleep(dur: float) -> None:
        pass

    provider_cfg = {
        "question_input": [],
        "answer_container": [],
        "generating_indicator": None,
        "done_indicator": None,
    }

    result = await wait_for_completion(
        mock_page,
        provider="copilot",
        provider_cfg=provider_cfg,
        blocking={},
        completion_cfg={"stable_seconds": 0.5, "poll_interval_s": 1.0},
        timeout_s=2.0,
        on_poll=mock_on_poll,
        clock=fake_clock,
        sleep=fake_sleep,
    )

    assert len(poll_events) > 0
    first_poll = poll_events[0]
    assert first_poll["is_thinking"] is True
    assert len(first_poll["thinking_steps"]) == 2
    assert first_poll["thinking_steps"][0]["title"] == "Understanding question"
    assert first_poll["thinking_steps"][0]["description"] == "Analyzing intent"
    assert first_poll["thinking_steps"][0]["status"] == "completed"
    assert first_poll["thinking_steps"][1]["title"] == "Searching web sources"
    assert len(first_poll["citations"]) == 1
    assert first_poll["citations"][0]["url"] == "https://microsoft.com"


@pytest.mark.asyncio
async def test_thinking_poll_deduplication_skips_unchanged_dom() -> None:
    emitted_events: list[dict] = []

    last_thinking_snapshot: dict | None = None

    async def simulate_poll(
        state: str,
        generating: bool,
        is_thinking: bool,
        thinking_text: str,
        citations: list[dict],
        thinking_steps: list[dict] | None = None,
    ) -> bool:
        nonlocal last_thinking_snapshot
        steps_list = thinking_steps or []
        cits_list = citations or []

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
        }

        if last_thinking_snapshot is not None and current_snapshot == last_thinking_snapshot:
            return False

        last_thinking_snapshot = current_snapshot
        emitted_events.append(current_snapshot)
        return True

    # Poll 1: Searching the web (10 chars text)
    p1 = await simulate_poll(
        state="generating text (10 chars)",
        generating=True,
        is_thinking=True,
        thinking_text="",
        citations=[],
        thinking_steps=[{"title": "Searched the web", "description": "Đã tìm kiếm: youtu.be", "status": "completed"}],
    )
    assert p1 is True
    assert len(emitted_events) == 1

    # Poll 2: Text grew to 25 chars, but thinking steps & citations are UNCHANGED -> MUST BE SKIPPED
    p2 = await simulate_poll(
        state="generating text (25 chars)",
        generating=True,
        is_thinking=True,
        thinking_text="",
        citations=[],
        thinking_steps=[{"title": "Searched the web", "description": "Đã tìm kiếm: youtu.be", "status": "completed"}],
    )
    assert p2 is False
    assert len(emitted_events) == 1

    # Poll 3: New thinking step appeared in DOM
    p3 = await simulate_poll(
        state="generating text (40 chars)",
        generating=True,
        is_thinking=True,
        thinking_text="",
        citations=[],
        thinking_steps=[
            {"title": "Searched the web", "description": "Đã tìm kiếm: youtu.be", "status": "completed"},
            {"title": "Adjusting the search approach to locate the specific video.", "description": "Refining strategy", "status": "completed"},
        ],
    )
    assert p3 is True
    assert len(emitted_events) == 2

    # Poll 4: Same steps, but citation appeared
    p4 = await simulate_poll(
        state="generating text (50 chars)",
        generating=True,
        is_thinking=True,
        thinking_text="",
        citations=[{"url": "https://youtu.be/0K-nzfWmbVc", "title": "Batch of 2.4m"}],
        thinking_steps=[
            {"title": "Searched the web", "description": "Đã tìm kiếm: youtu.be", "status": "completed"},
            {"title": "Adjusting the search approach to locate the specific video.", "description": "Refining strategy", "status": "completed"},
        ],
    )
    assert p4 is True
    assert len(emitted_events) == 3

    # Poll 5: Identical to Poll 4 even with state="generating text (70 chars)" -> SKIPPED
    p5 = await simulate_poll(
        state="generating text (70 chars)",
        generating=True,
        is_thinking=True,
        thinking_text="",
        citations=[{"url": "https://youtu.be/0K-nzfWmbVc", "title": "Batch of 2.4m"}],
        thinking_steps=[
            {"title": "Searched the web", "description": "Đã tìm kiếm: youtu.be", "status": "completed"},
            {"title": "Adjusting the search approach to locate the specific video.", "description": "Refining strategy", "status": "completed"},
        ],
    )
    assert p5 is False
    assert len(emitted_events) == 3


def test_qwen_dom_scan_script_contains_sidebar_and_citations_selectors() -> None:
    assert "qwen-chat-thinking-and-sources-content" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "qwen-chat-thinking-status-card" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "qwen-chat-search-card" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "sources-item" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "host-name-text" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "content-item-des-title" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "content-item-des" in DOM_SCAN_THINKING_AND_CITATIONS


def test_gemini_dom_scan_script_contains_thinking_and_citations_selectors() -> None:
    assert "thoughts-container" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "spark-thinking-steps" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "attribution-container" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "tool-attribution" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "link-block" in DOM_SCAN_THINKING_AND_CITATIONS


@pytest.mark.asyncio
async def test_gemini_select_mode_dropdown_not_found_graceful() -> None:
    from app.adapters.gemini_ui import GeminiUIAdapter
    adapter = GeminiUIAdapter()
    mock_page = MagicMock()
    mock_page.locator.return_value.count = AsyncMock(return_value=0)
    mock_page.get_by_role.return_value.count = AsyncMock(return_value=0)
    mock_page.get_by_test_id.return_value.count = AsyncMock(return_value=0)
    mock_page.get_by_placeholder.return_value.count = AsyncMock(return_value=0)
    mock_page.get_by_text.return_value.count = AsyncMock(return_value=0)

    # When dropdown is not found within timeout, should not raise
    await adapter._select_mode(mock_page, "deep", timeout_s=0.1)


@pytest.mark.asyncio
async def test_gemini_select_mode_already_in_target_mode() -> None:
    from app.adapters.gemini_ui import GeminiUIAdapter
    adapter = GeminiUIAdapter()
    mock_page = MagicMock()

    mock_btn = AsyncMock()
    mock_btn.count = AsyncMock(return_value=1)
    mock_btn.inner_text = AsyncMock(return_value="Pro Cao")
    mock_btn.get_attribute = AsyncMock(return_value="Mở công cụ chọn chế độ, hiện tại là Pro Cao")

    mock_page.locator.return_value = mock_btn

    # Deep mode requested, already "Pro Cao", should not click to switch
    await adapter._select_mode(mock_page, "deep", timeout_s=1.0)
    assert mock_btn.click.call_count == 0



