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
    assert "WORKED_FOR_REGEX" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "skipButton" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "Worked for" in DOM_SCAN_THINKING_AND_CITATIONS


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


@pytest.mark.asyncio
async def test_wait_for_completion_chatgpt_thinking_running() -> None:
    poll_events: list[dict] = []

    async def mock_on_poll(**kwargs) -> None:
        poll_events.append(kwargs)

    mock_page = MagicMock()
    mock_page.url = "https://chatgpt.com"
    mock_page.locator.return_value.inner_text = AsyncMock(return_value="ChatGPT streaming response")
    mock_page.evaluate = AsyncMock(return_value={
        "is_thinking": True,
        "thinking_text": "Thinking about the query...\nAnalyzing dependencies",
        "thinking_steps": [
            {"title": "Thinking", "description": "Thinking about the query...\nAnalyzing dependencies", "status": "running"},
        ],
        "citations": [],
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
        provider="chatgpt",
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
    assert len(first_poll["thinking_steps"]) == 1
    assert first_poll["thinking_steps"][0]["title"] == "Thinking"
    assert first_poll["thinking_steps"][0]["status"] == "running"
    assert "Analyzing dependencies" in first_poll["thinking_steps"][0]["description"]


@pytest.mark.asyncio
async def test_wait_for_completion_chatgpt_thinking_completed() -> None:
    poll_events: list[dict] = []

    async def mock_on_poll(**kwargs) -> None:
        poll_events.append(kwargs)

    mock_page = MagicMock()
    mock_page.url = "https://chatgpt.com"
    mock_page.locator.return_value.inner_text = AsyncMock(return_value="ChatGPT final response")
    mock_page.evaluate = AsyncMock(return_value={
        "is_thinking": True,
        "thinking_text": "Finalized reasoning.\nAll edge cases validated.",
        "thinking_steps": [
            {"title": "Worked for 1m 24s", "description": "Finalized reasoning.\nAll edge cases validated.", "status": "completed"},
        ],
        "citations": [{"url": "https://openai.com/research", "title": "OpenAI Research"}],
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
        provider="chatgpt",
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
    assert len(first_poll["thinking_steps"]) == 1
    assert first_poll["thinking_steps"][0]["title"] == "Worked for 1m 24s"
    assert first_poll["thinking_steps"][0]["status"] == "completed"
    assert "edge cases" in first_poll["thinking_steps"][0]["description"]


@pytest.mark.asyncio
async def test_chatgpt_extract_sources_via_more_actions_and_modal() -> None:
    from app.adapters.chatgpt_ui import ChatGPTUIAdapter

    adapter = ChatGPTUIAdapter()

    # Mock page and elements
    mock_page = MagicMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()

    # Mock locators
    mock_turn = MagicMock()
    mock_turn.count = AsyncMock(return_value=1)
    mock_turn.scroll_into_view_if_needed = AsyncMock()
    mock_turn.hover = AsyncMock()

    mock_more_btn = MagicMock()
    mock_more_btn.count = AsyncMock(return_value=1)
    mock_more_btn.scroll_into_view_if_needed = AsyncMock()
    mock_more_btn.click = AsyncMock()

    mock_view_sources = MagicMock()
    mock_view_sources.count = AsyncMock(return_value=1)
    mock_view_sources.is_visible = AsyncMock(return_value=True)
    mock_view_sources.click = AsyncMock()

    mock_modal = MagicMock()
    mock_modal.count = AsyncMock(return_value=1)
    mock_modal.is_visible = AsyncMock(return_value=True)
    mock_modal.wait_for = AsyncMock()
    mock_modal.evaluate = AsyncMock(return_value=[
        {
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "title": "Artificial Intelligence - Wikipedia",
            "snippet": "Overview of AI and machine learning techniques.",
        },
        {
            "url": "https://arxiv.org/abs/2301.00001",
            "title": "Reasoning Models in LLMs",
            "snippet": "Research on chain of thought.",
        },
    ])

    mock_close_btn = MagicMock()
    mock_close_btn.count = AsyncMock(return_value=1)
    mock_close_btn.is_visible = AsyncMock(return_value=True)
    mock_close_btn.click = AsyncMock()
    mock_modal.locator = MagicMock(return_value=mock_close_btn)

    mock_turn.locator = MagicMock(return_value=mock_more_btn)

    def mock_locator_router(selector: str) -> Any:
        if "article" in selector or "assistant" in selector:
            turn_collection = MagicMock()
            turn_collection.count = AsyncMock(return_value=1)
            turn_collection.last = mock_turn
            return turn_collection
        if "More actions" in selector or "More action" in selector:
            btn_collection = MagicMock()
            btn_collection.count = AsyncMock(return_value=1)
            btn_collection.last = mock_more_btn
            return btn_collection
        if "View sources" in selector:
            cand = MagicMock()
            cand.count = AsyncMock(return_value=1)
            cand.is_visible = AsyncMock(return_value=True)
            cand.click = AsyncMock()
            first_mock = MagicMock()
            first_mock.first = cand
            return first_mock
        if "Sources" in selector or "Nguồn" in selector:
            modal_coll = MagicMock()
            modal_coll.first = mock_modal
            return modal_coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        empty.first = empty
        empty.last = empty
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator_router)

    sources = await adapter._extract_sources(mock_page)

    assert len(sources) == 2
    assert str(sources[0].url) == "https://en.wikipedia.org/wiki/Artificial_intelligence"
    assert sources[0].title == "Artificial Intelligence - Wikipedia"
    assert sources[0].snippet == "Overview of AI and machine learning techniques."
    assert str(sources[1].url) == "https://arxiv.org/abs/2301.00001"
    assert sources[1].title == "Reasoning Models in LLMs"
    assert sources[1].snippet == "Research on chain of thought."


def test_dom_scan_script_mistral_tokens() -> None:
    from app.browser.waits import DOM_SCAN_THINKING_AND_CITATIONS

    assert "harness-steps-summary" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "data-message-part-type='reasoning'" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "content\\s+truncated" in DOM_SCAN_THINKING_AND_CITATIONS


@pytest.mark.asyncio
async def test_mistral_response_ready_checks() -> None:
    from app.adapters.mistral_ui import MistralUIAdapter

    adapter = MistralUIAdapter()
    mock_page = MagicMock()

    # Case 1: Stop button is visible -> must return False (still generating)
    mock_stop = MagicMock()
    mock_stop.count = AsyncMock(return_value=1)
    mock_stop_item = MagicMock()
    mock_stop_item.is_visible = AsyncMock(return_value=True)
    mock_stop.nth = MagicMock(return_value=mock_stop_item)

    mock_page.locator = MagicMock(return_value=mock_stop)
    assert await adapter._response_ready(mock_page) is False

    # Case 2: Stop button gone, but Send button missing -> return False
    def mock_loc_no_send(sel: str) -> Any:
        m = MagicMock()
        m.count = AsyncMock(return_value=0)
        m.first = m
        m.is_editable = AsyncMock(return_value=False)
        m.is_visible = AsyncMock(return_value=False)
        return m

    mock_page.locator = MagicMock(side_effect=mock_loc_no_send)
    assert await adapter._response_ready(mock_page) is False

    # Case 3: Stop gone, Send ready, but action buttons missing on assistant -> return False
    mock_asst = MagicMock()
    mock_asst.count = AsyncMock(return_value=1)
    mock_asst_elem = MagicMock()
    mock_asst.last = mock_asst_elem

    empty_btn = MagicMock()
    empty_btn.count = AsyncMock(return_value=0)
    mock_asst_elem.locator = MagicMock(return_value=empty_btn)

    def mock_loc_no_actions(sel: str) -> Any:
        m = MagicMock()
        if "Stop" in sel:
            m.count = AsyncMock(return_value=0)
            return m
        if "data-step-state='running'" in sel or ".animate-spin" in sel:
            m.count = AsyncMock(return_value=0)
            return m
        if "Send" in sel or "submit" in sel:
            m.count = AsyncMock(return_value=1)
            item = MagicMock()
            item.is_visible = AsyncMock(return_value=True)
            m.nth = MagicMock(return_value=item)
            return m
        if "data-message-author-role='assistant'" in sel:
            return mock_asst
        m.count = AsyncMock(return_value=0)
        return m

    mock_page.locator = MagicMock(side_effect=mock_loc_no_actions)
    assert await adapter._response_ready(mock_page) is False

    # Case 4: Stop gone, Send ready, Action buttons present (Like, Copy, etc.) -> returns True
    visible_btn = MagicMock()
    visible_btn.count = AsyncMock(return_value=1)
    visible_btn.first = visible_btn
    visible_btn.is_visible = AsyncMock(return_value=True)
    mock_asst_elem.locator = MagicMock(return_value=visible_btn)

    assert await adapter._response_ready(mock_page) is True


    # Case 5: Stop gone, Send ready, side-panel visible -> returns True
    def mock_loc_side_panel(sel: str) -> Any:
        m = MagicMock()
        if "Stop" in sel:
            m.count = AsyncMock(return_value=0)
            return m
        if "Send" in sel or "submit" in sel:
            m.count = AsyncMock(return_value=1)
            item = MagicMock()
            item.is_visible = AsyncMock(return_value=True)
            m.nth = MagicMock(return_value=item)
            return m
        if "chat-side-panel" in sel:
            m.count = AsyncMock(return_value=1)
            m.first = m
            m.is_visible = AsyncMock(return_value=True)
            return m
        m.count = AsyncMock(return_value=0)
        return m

    mock_page.locator = MagicMock(side_effect=mock_loc_side_panel)
    assert await adapter._response_ready(mock_page) is True


@pytest.mark.asyncio
async def test_mistral_extract_deep_research_report_from_side_panel() -> None:
    from app.adapters.mistral_ui import MistralUIAdapter

    adapter = MistralUIAdapter()

    mock_page = MagicMock()

    # Mock side panel locators
    mock_side_panel = MagicMock()
    mock_side_panel.count = AsyncMock(return_value=1)
    mock_side_panel.is_visible = AsyncMock(return_value=True)
    mock_side_panel.first = mock_side_panel

    mock_editor = MagicMock()
    mock_editor.count = AsyncMock(return_value=1)
    mock_editor.is_visible = AsyncMock(return_value=True)
    mock_editor.first = mock_editor
    mock_editor.inner_html = AsyncMock(return_value="<h1>Deep Research Report</h1><p>Full detailed report content here.</p>")

    def side_panel_locator(sel: str) -> Any:
        if "ProseMirror" in sel or "canva-editor" in sel or "markdown-editor" in sel:
            return mock_editor
        m = MagicMock()
        m.count = AsyncMock(return_value=0)
        return m

    mock_side_panel.locator = MagicMock(side_effect=side_panel_locator)

    def page_locator(sel: str) -> Any:
        if "chat-side-panel" in sel:
            return mock_side_panel
        m = MagicMock()
        m.count = AsyncMock(return_value=0)
        return m

    mock_page.locator = MagicMock(side_effect=page_locator)

    report = await adapter._extract_deep_research_report(mock_page)
    assert "Deep Research Report" in report
    assert "Full detailed report content here." in report


@pytest.mark.asyncio
async def test_mistral_extract_answer_renders_report_above_final_response() -> None:
    from app.adapters.mistral_ui import MistralUIAdapter

    adapter = MistralUIAdapter()
    mock_page = MagicMock()

    adapter._extract_deep_research_report = AsyncMock(
        return_value="# Xu hướng phát triển LLM Reasoning Models 2026\n\nNội dung chi tiết báo cáo."
    )
    adapter._extract_main_chat_answer = AsyncMock(
        return_value="Tôi đã hoàn thành nghiên cứu chuyên sâu về các mô hình reasoning."
    )

    answer = await adapter._extract_answer(mock_page, prompt="so sánh reasoning models")

    # Ensure report is rendered ABOVE the final response
    assert answer.startswith("# Xu hướng phát triển LLM Reasoning Models 2026")
    assert "---" in answer
    assert answer.endswith("Tôi đã hoàn thành nghiên cứu chuyên sâu về các mô hình reasoning.")
    # Check ordering
    report_idx = answer.find("# Xu hướng phát triển LLM Reasoning Models 2026")
    chat_idx = answer.find("Tôi đã hoàn thành nghiên cứu chuyên sâu về các mô hình reasoning.")
    assert report_idx < chat_idx


@pytest.mark.asyncio
async def test_mistral_extract_answer_preserves_short_main_chat_response() -> None:
    from app.adapters.mistral_ui import MistralUIAdapter

    adapter = MistralUIAdapter()
    mock_page = MagicMock()

    adapter._extract_deep_research_report = AsyncMock(
        return_value="# Full Report\n\nExtensive data analysis."
    )
    adapter._extract_main_chat_answer = AsyncMock(
        return_value="Here is the report."
    )

    answer = await adapter._extract_answer(mock_page, prompt="report prompt")
    assert answer.startswith("# Full Report")
    assert "---" in answer
    assert answer.endswith("Here is the report.")


@pytest.mark.asyncio
async def test_mistral_extract_answer_full_ordered_three_parts() -> None:
    from app.adapters.mistral_ui import MistralUIAdapter

    adapter = MistralUIAdapter()
    mock_page = MagicMock()

    adapter._extract_thinking_steps = AsyncMock(
        return_value=[
            {
                "title": "Search queries formulation",
                "description": "Searching for recent AI benchmarks",
                "links": [{"url": "https://example.com/benchmarks", "title": "AI Benchmarks 2026"}],
            },
            {
                "title": "Synthesizing deep research data",
                "description": "Analyzing multi-agent performance",
                "links": [],
            },
        ]
    )
    adapter._extract_deep_research_report = AsyncMock(
        return_value="# Detailed Deep Research Report\n\nFull analysis and charts."
    )
    adapter._extract_main_chat_answer = AsyncMock(
        return_value="Dựa trên báo cáo chi tiết, chúng tôi kết luận mô hình mới vượt trội 15%."
    )

    answer = await adapter._extract_answer(mock_page, prompt="so sánh hiệu năng")

    # Order must strictly be:
    # 1. Thinking steps
    # 2. Deep research report
    # 3. Final conclusion
    assert "Thinking & Research Steps" in answer
    assert "Search queries formulation" in answer
    assert "https://example.com/benchmarks" in answer
    assert "# Detailed Deep Research Report" in answer
    assert "Dựa trên báo cáo chi tiết, chúng tôi kết luận mô hình mới vượt trội 15%." in answer

    idx_thinking = answer.find("Thinking & Research Steps")
    idx_report = answer.find("# Detailed Deep Research Report")
    idx_conclusion = answer.find("Dựa trên báo cáo chi tiết")

    assert idx_thinking < idx_report < idx_conclusion







