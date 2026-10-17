from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.capabilities.meta import MetaCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest
from app.adapters.meta_ui import MetaUIAdapter
from app.adapters.selectors_loader import load_selectors, provider_selectors


def test_meta_selectors_config() -> None:
    selectors = load_selectors()
    cfg = provider_selectors(selectors, "meta")

    # Question input
    assert "question_input" in cfg
    q_selectors = [list(item.values())[0] for item in cfg["question_input"]]
    assert any("chat-main-conversation" in s or "contenteditable" in s for s in q_selectors)

    # Submit button
    assert "submit" in cfg
    sub_selectors = [list(item.values())[0] for item in cfg["submit"]]
    assert any("Send" in s or "composer-send-button" in s for s in sub_selectors)

    # Mode selectors: mode_dropdown, deep_mode (Thinking), standard_mode (Instant)
    mode_sels = cfg.get("mode_selectors", {})
    assert "mode_dropdown" in mode_sels
    assert "deep_mode" in mode_sels
    assert "standard_mode" in mode_sels

    # Generating and done indicators
    assert "generating_indicator" in cfg
    gen_selectors = [list(item.values())[0] for item in cfg["generating_indicator"]]
    assert any("stop" in s.lower() for s in gen_selectors)

    assert "done_indicator" in cfg
    done_selectors = [list(item.values())[0] for item in cfg["done_indicator"]]
    assert any("copy" in s.lower() for s in done_selectors)


def test_meta_capabilities_defaults() -> None:
    strategy = MetaCapabilitiesStrategy()
    caps = strategy.get_default_capabilities()

    assert caps.provider == "meta"
    # Requirement 1: There is no AI model dropdown, no need this one on our side also
    assert caps.available_models == []
    assert caps.selected_model_id is None
    # Requirement 2: Thinking toggle: off = Instant, on = Thinking
    assert caps.deep_thinking is False
    assert caps.web_search is True
    assert caps.deep_research is False


@pytest.mark.asyncio
async def test_meta_inspect_dom_thinking_mode() -> None:
    strategy = MetaCapabilitiesStrategy()
    mock_page = MagicMock()

    btn = MagicMock()
    btn.inner_text = AsyncMock(return_value="Thinking")
    btn.get_attribute = AsyncMock(return_value="Composer mode: Thinking")
    btn.is_visible = AsyncMock(return_value=True)

    btn_coll = MagicMock()
    btn_coll.count = AsyncMock(return_value=1)
    btn_coll.nth = MagicMock(return_value=btn)

    mock_page.locator = MagicMock(return_value=btn_coll)

    caps = await strategy.inspect_dom(mock_page)
    assert caps.deep_thinking is True


@pytest.mark.asyncio
async def test_meta_apply_selection_switch_to_thinking() -> None:
    strategy = MetaCapabilitiesStrategy()
    mock_page = MagicMock()

    # Current button shows "Instant"
    btn = MagicMock()
    btn.inner_text = AsyncMock(return_value="Instant")
    btn.get_attribute = AsyncMock(return_value="Mode Instant")
    btn.is_visible = AsyncMock(return_value=True)
    btn.click = AsyncMock()

    btn_coll = MagicMock()
    btn_coll.count = AsyncMock(return_value=1)
    btn_coll.nth = MagicMock(return_value=btn)

    # Menuitem for "Thinking"
    thinking_item = MagicMock()
    thinking_item.is_visible = AsyncMock(return_value=True)
    thinking_item.click = AsyncMock()

    item_coll = MagicMock()
    item_coll.count = AsyncMock(return_value=1)
    item_coll.nth = MagicMock(return_value=thinking_item)

    def mock_locator(sel: str) -> Any:
        if "composer-mode" in sel or "Thinking" in sel or "Instant" in sel:
            if "menuitem" in sel or "option" in sel:
                return item_coll
            return btn_coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.press = AsyncMock()

    req = ProviderSelectionRequest(deep_thinking=True)
    await strategy.apply_selection(mock_page, req)

    btn.click.assert_awaited_once()
    thinking_item.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_meta_response_ready_generating_and_done() -> None:
    adapter = MetaUIAdapter(session=MagicMock())
    mock_page = MagicMock()

    # 1. When Stop button is visible -> returns False (still generating)
    stop_item = MagicMock()
    stop_item.is_visible = AsyncMock(return_value=True)
    stop_coll = MagicMock()
    stop_coll.count = AsyncMock(return_value=1)
    stop_coll.nth = MagicMock(return_value=stop_item)

    empty_coll = MagicMock()
    empty_coll.count = AsyncMock(return_value=0)

    def mock_loc_generating(sel: str) -> Any:
        if "stop" in sel.lower():
            return stop_coll
        return empty_coll

    mock_page.locator = MagicMock(side_effect=mock_loc_generating)
    assert await adapter._response_ready(mock_page) is False

    # 2. When Stop button is gone AND Copy button is visible -> returns True (done)
    copy_item = MagicMock()
    copy_item.is_visible = AsyncMock(return_value=True)
    copy_coll = MagicMock()
    copy_coll.count = AsyncMock(return_value=1)
    copy_coll.nth = MagicMock(return_value=copy_item)

    def mock_loc_done(sel: str) -> Any:
        if "copy" in sel.lower():
            return copy_coll
        return empty_coll

    mock_page.locator = MagicMock(side_effect=mock_loc_done)
    assert await adapter._response_ready(mock_page) is True


@pytest.mark.asyncio
async def test_meta_extract_answer_with_html_asset() -> None:
    adapter = MetaUIAdapter(session=MagicMock())
    mock_page = MagicMock()

    # Mock HTML asset block
    view_btn = MagicMock()
    view_btn.is_visible = AsyncMock(return_value=True)
    view_btn.click = AsyncMock()
    view_coll = MagicMock()
    view_coll.count = AsyncMock(return_value=1)
    view_coll.first = view_btn

    asset_el = MagicMock()
    asset_el.locator = MagicMock(return_value=view_coll)
    asset_coll = MagicMock()
    asset_coll.count = AsyncMock(return_value=1)
    asset_coll.nth = MagicMock(return_value=asset_el)

    # Mock ecto-code-source-panel
    panel_el = MagicMock()
    panel_el.is_visible = AsyncMock(return_value=True)
    panel_coll = MagicMock()
    panel_coll.count = AsyncMock(return_value=1)
    panel_coll.first = panel_el

    # Mock copy button
    copy_btn = MagicMock()
    copy_btn.click = AsyncMock()
    copy_coll = MagicMock()
    copy_coll.count = AsyncMock(return_value=1)
    copy_coll.first = copy_btn
    copy_coll.last = copy_btn

    def mock_locator(sel: str) -> Any:
        if "data-asset-type='HTML'" in sel or "data-language='html'" in sel:
            return asset_coll
        if "ecto-code-source-panel" in sel:
            return panel_coll
        if "copy" in sel.lower():
            return copy_coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)

    async def mock_eval(script: str, *args: Any) -> Any:
        if "ecto-code-source-panel" in script or "codeEl" in script:
            return "<!DOCTYPE html><html><body><h1>Hello World</h1></body></html>"
        if "readText" in script:
            return "Here is the web page design you requested:"
        return ""

    mock_page.evaluate = AsyncMock(side_effect=mock_eval)

    with patch("app.adapters.meta_ui.settings") as mock_settings:
        mock_settings.work_mode = "sync"
        result = await adapter._extract_answer(mock_page, prompt="Make a webpage")

    # Assert that HTML asset code was extracted and embedded
    assert "Here is the web page design you requested:" in result
    assert "```html" in result
    assert "<h1>Hello World</h1>" in result
