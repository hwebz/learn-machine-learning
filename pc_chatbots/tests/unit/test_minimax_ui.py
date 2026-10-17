from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.capabilities.minimax import MinimaxCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest
from app.adapters.minimax_ui import MinimaxUIAdapter
from app.adapters.selectors_loader import load_selectors, provider_selectors


def test_minimax_selectors_config() -> None:
    selectors = load_selectors()
    cfg = provider_selectors(selectors, "minimax")

    # Question input
    assert "question_input" in cfg
    q_selectors = [list(item.values())[0] for item in cfg["question_input"]]
    assert any("ProseMirror" in s or "tiptap" in s or "message-textarea" in s for s in q_selectors)

    # Submit button
    assert "submit" in cfg
    sub_selectors = [list(item.values())[0] for item in cfg["submit"]]
    assert any("send-button" in s for s in sub_selectors)

    # Mode selectors: model_dropdown and attach_button
    mode_sels = cfg.get("mode_selectors", {})
    assert "model_dropdown" in mode_sels
    assert "attach_button" in mode_sels

    # Generating and done indicators
    assert "generating_indicator" in cfg
    gen_selectors = [list(item.values())[0] for item in cfg["generating_indicator"]]
    assert any("stop" in s.lower() for s in gen_selectors)

    assert "done_indicator" in cfg
    done_selectors = [list(item.values())[0] for item in cfg["done_indicator"]]
    assert any("copy" in s.lower() for s in done_selectors)


def test_minimax_capabilities_defaults() -> None:
    strategy = MinimaxCapabilitiesStrategy()
    caps = strategy.get_default_capabilities()

    assert caps.provider == "minimax"
    assert caps.selected_model_id == "m3"
    assert any(m.id == "m3" for m in caps.available_models)
    assert any(m.id == "m3.1-flash" for m in caps.available_models)
    assert caps.deep_research is False
    assert caps.deep_thinking is False
    assert caps.web_search is False


@pytest.mark.asyncio
async def test_minimax_apply_selection_model() -> None:
    strategy = MinimaxCapabilitiesStrategy()
    mock_page = MagicMock()

    # Trigger shows current model "M3"
    trigger_el = MagicMock()
    trigger_el.inner_text = AsyncMock(return_value="M3")
    trigger_el.click = AsyncMock()

    trigger_coll = MagicMock()
    trigger_coll.count = AsyncMock(return_value=1)
    trigger_coll.first = trigger_el

    # Flash model item in dropdown
    flash_item = MagicMock()
    flash_item.click = AsyncMock()
    flash_coll = MagicMock()
    flash_coll.count = AsyncMock(return_value=1)
    flash_coll.first = flash_item

    def mock_locator(sel: str) -> Any:
        if "model-selector-trigger" in sel or "mavis-model-selector-trigger" in sel:
            return trigger_coll
        if "Flash" in sel:
            return flash_coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)
    mock_page.evaluate = AsyncMock(return_value=False)  # no chip
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    # Request switch to Flash
    req = ProviderSelectionRequest(model_id="m3.1-flash", deep_research=False)
    await strategy.apply_selection(mock_page, req)

    trigger_el.click.assert_awaited_once()
    flash_item.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_minimax_apply_selection_deep_research_enable() -> None:
    strategy = MinimaxCapabilitiesStrategy()
    mock_page = MagicMock()

    # Current trigger is already M3, so no model switch needed
    trigger_el = MagicMock()
    trigger_el.inner_text = AsyncMock(return_value="M3")
    trigger_coll = MagicMock()
    trigger_coll.count = AsyncMock(return_value=1)
    trigger_coll.first = trigger_el

    # Deep research is currently NOT active
    mock_page.evaluate = AsyncMock(return_value=False)

    # Attach button (+)
    attach_el = MagicMock()
    attach_el.click = AsyncMock()
    attach_coll = MagicMock()
    attach_coll.count = AsyncMock(return_value=1)
    attach_coll.first = attach_el

    # Skills menu item
    skills_el = MagicMock()
    skills_el.click = AsyncMock()
    skills_coll = MagicMock()
    skills_coll.count = AsyncMock(return_value=1)
    skills_coll.first = skills_el

    # Deep research skill button
    deep_el = MagicMock()
    deep_el.click = AsyncMock()
    deep_coll = MagicMock()
    deep_coll.count = AsyncMock(return_value=1)
    deep_coll.first = deep_el

    def mock_locator(sel: str) -> Any:
        if "model-selector-trigger" in sel:
            return trigger_coll
        if "attach-button" in sel or "Add attachment" in sel:
            return attach_coll
        if "Skills" in sel:
            return skills_coll
        if "deep-research" in sel:
            return deep_coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    req = ProviderSelectionRequest(model_id="m3", deep_research=True)
    await strategy.apply_selection(mock_page, req)

    attach_el.click.assert_awaited_once()
    skills_el.click.assert_awaited_once()
    deep_el.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_minimax_apply_selection_deep_research_disable() -> None:
    strategy = MinimaxCapabilitiesStrategy()
    mock_page = MagicMock()

    # Chip is currently present
    mock_page.evaluate = AsyncMock(return_value=True)

    remove_el = MagicMock()
    remove_el.click = AsyncMock()
    remove_coll = MagicMock()
    remove_coll.count = AsyncMock(return_value=1)
    remove_coll.first = remove_el

    def mock_locator(sel: str) -> Any:
        if "remove" in sel.lower():
            return remove_coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)

    req = ProviderSelectionRequest(model_id="m3", deep_research=False)
    await strategy.apply_selection(mock_page, req)

    remove_el.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_minimax_enter_prompt_preserves_chip() -> None:
    adapter = MinimaxUIAdapter()
    mock_page = MagicMock()
    mock_input = MagicMock()
    mock_input.click = AsyncMock()

    # has_chip = True
    mock_page.evaluate = AsyncMock(return_value=True)
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()
    mock_page.keyboard.type = AsyncMock()

    await adapter._enter_prompt(mock_page, mock_input, "What is quantum computing?")

    mock_input.click.assert_awaited_once()
    mock_page.keyboard.press.assert_awaited_with("End")
    mock_page.keyboard.type.assert_awaited_once()
    args, kwargs = mock_page.keyboard.type.call_args
    assert "What is quantum computing?" in args[0]


@pytest.mark.asyncio
async def test_minimax_select_mode_with_json() -> None:
    adapter = MinimaxUIAdapter()
    mock_page = MagicMock()

    payload = json.dumps({"model_id": "m3.1-flash", "deep_research": True})
    with patch("app.adapters.capabilities.minimax.MinimaxCapabilitiesStrategy.apply_selection", new_callable=AsyncMock) as mock_apply:
        await adapter._select_mode(mock_page, payload)
        mock_apply.assert_awaited_once()
        req: ProviderSelectionRequest = mock_apply.call_args[0][1]
        assert req.model_id == "m3.1-flash"
        assert req.deep_research is True


def test_minimax_dom_scan_script_tokens() -> None:
    from app.browser.waits import DOM_SCAN_THINKING_AND_CITATIONS

    assert "chat-main-conversation" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "turn-process-disclosure" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "activity-group" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "activity-group-header-summary" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "turn-process-summary" in DOM_SCAN_THINKING_AND_CITATIONS


@pytest.mark.asyncio
async def test_minimax_response_ready_returns_false_when_stop_button_visible() -> None:
    adapter = MinimaxUIAdapter()
    mock_page = MagicMock()

    stop_btn = MagicMock()
    stop_btn.is_visible = AsyncMock(return_value=True)

    def mock_locator(sel: str) -> Any:
        if "stop" in sel.lower():
            coll = MagicMock()
            coll.count = AsyncMock(return_value=1)
            coll.nth = MagicMock(return_value=stop_btn)
            return coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)

    res = await adapter._response_ready(mock_page)
    assert res is False


@pytest.mark.asyncio
async def test_minimax_response_ready_returns_true_when_stop_gone_and_copy_visible() -> None:
    adapter = MinimaxUIAdapter()
    mock_page = MagicMock()

    copy_btn = MagicMock()
    copy_btn.is_visible = AsyncMock(return_value=True)

    def mock_locator(sel: str) -> Any:
        if "stop" in sel.lower():
            empty = MagicMock()
            empty.count = AsyncMock(return_value=0)
            return empty
        if "copy" in sel.lower():
            coll = MagicMock()
            coll.count = AsyncMock(return_value=1)
            coll.nth = MagicMock(return_value=copy_btn)
            return coll
        asst = MagicMock()
        asst.count = AsyncMock(return_value=1)
        return asst

    mock_page.locator = MagicMock(side_effect=mock_locator)

    res = await adapter._response_ready(mock_page)
    assert res is True


@pytest.mark.asyncio
async def test_minimax_response_ready_returns_false_when_stop_gone_but_copy_not_shown_yet() -> None:
    adapter = MinimaxUIAdapter()
    mock_page = MagicMock()

    def mock_locator(sel: str) -> Any:
        if "stop" in sel.lower():
            empty = MagicMock()
            empty.count = AsyncMock(return_value=0)
            return empty
        if "copy" in sel.lower():
            empty = MagicMock()
            empty.count = AsyncMock(return_value=0)
            return empty
        if "assistant" in sel:
            asst = MagicMock()
            asst.count = AsyncMock(return_value=1)
            return asst
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)

    res = await adapter._response_ready(mock_page)
    assert res is False


@pytest.mark.asyncio
async def test_minimax_extract_answer_clean_dom() -> None:
    adapter = MinimaxUIAdapter()
    mock_page = MagicMock()

    # Disable clipboard branch
    with patch("app.core.config.settings.work_mode", "async"):
        # DOM fallback mock
        asst_target = MagicMock()
        asst_coll = MagicMock()
        asst_coll.count = AsyncMock(return_value=1)
        asst_coll.last = asst_target

        mock_page.locator = MagicMock(return_value=asst_coll)
        mock_page.evaluate = AsyncMock(
            return_value="<p>Dưới đây là 3 xu hướng AI năm 2026: 1. Agentic workflows, 2. Multimodal reasoning, 3. On-device SLMs.</p>"
        )

        res = await adapter._extract_answer(mock_page, "Tóm tắt xu hướng AI")
        assert "Agentic workflows" in res
        assert "Multimodal reasoning" in res

