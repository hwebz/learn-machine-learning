from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.selectors_loader import load_selectors, provider_selectors
from app.adapters.zhipu_ui import ZhipuUIAdapter
from app.browser.waits import DOM_SCAN_THINKING_AND_CITATIONS


def test_zhipu_selectors_config() -> None:
    selectors = load_selectors()
    cfg = provider_selectors(selectors, "zhipu")

    # Verify generating_indicator is configured with Stop button & typing/cursor
    assert "generating_indicator" in cfg
    gen_selectors = [list(item.values())[0] for item in cfg["generating_indicator"]]
    assert any("Stop" in s for s in gen_selectors)
    assert any(".chat-assistant" in s or "chat-assistant" in s for s in gen_selectors)

    # Verify done_indicator includes .chat-assistant copy button
    assert "done_indicator" in cfg
    done_selectors = [list(item.values())[0] for item in cfg["done_indicator"]]
    assert any("chat-assistant" in s and "copy" in s for s in done_selectors)

    # Verify answer_container targets .chat-assistant
    assert "answer_container" in cfg
    ans_selectors = [list(item.values())[0] for item in cfg["answer_container"]]
    assert any("chat-assistant" in s for s in ans_selectors)


def test_zhipu_dom_scan_script_tokens() -> None:
    assert "chat-assistant" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "Confirm Preferences" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "Thought Process" in DOM_SCAN_THINKING_AND_CITATIONS


@pytest.mark.asyncio
async def test_zhipu_response_ready_returns_false_when_stop_button_visible() -> None:
    adapter = ZhipuUIAdapter()
    mock_page = MagicMock()

    # Confirm Preferences not open
    mock_page.evaluate = AsyncMock(return_value=False)

    stop_btn = MagicMock()
    stop_btn.is_visible = AsyncMock(return_value=True)

    def mock_locator(sel: str) -> Any:
        if "Stop" in sel or "stop" in sel:
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
async def test_zhipu_handle_confirm_preferences_clicks_continue() -> None:
    adapter = ZhipuUIAdapter()
    mock_page = MagicMock()

    # 1. Dialog is open, 2. Continue button is not disabled
    mock_page.evaluate = AsyncMock(side_effect=[
        True,   # initial check: is_dialog_open
        True,   # loop: still_open
        False,  # loop: is_disabled check (False = enabled)
    ])

    continue_btn = MagicMock()
    continue_btn.is_visible = AsyncMock(return_value=True)
    continue_btn.click = AsyncMock()

    continue_coll = MagicMock()
    continue_coll.count = AsyncMock(return_value=1)
    continue_coll.first = continue_btn

    mock_page.locator = MagicMock(return_value=continue_coll)

    handled = await adapter._handle_confirm_preferences(mock_page, max_wait_s=5.0)
    assert handled is True
    continue_btn.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_zhipu_handle_confirm_preferences_auto_continued() -> None:
    adapter = ZhipuUIAdapter()
    mock_page = MagicMock()

    # 1. Dialog is open initially, 2. Next poll dialog is gone (auto-continued)
    mock_page.evaluate = AsyncMock(side_effect=[
        True,   # initial check: is_dialog_open
        False,  # loop: still_open returns False (closed by itself)
    ])

    continue_coll = MagicMock()
    continue_coll.count = AsyncMock(return_value=0)
    mock_page.locator = MagicMock(return_value=continue_coll)

    handled = await adapter._handle_confirm_preferences(mock_page, max_wait_s=5.0)
    assert handled is True


@pytest.mark.asyncio
async def test_zhipu_extract_answer_clean_dom() -> None:
    adapter = ZhipuUIAdapter()
    mock_page = MagicMock()

    # Mock clipboard failure / async mode fallback
    copy_coll = MagicMock()
    copy_coll.count = AsyncMock(return_value=0)

    asst_el = MagicMock()
    asst_coll = MagicMock()
    asst_coll.count = AsyncMock(return_value=1)
    asst_coll.last = asst_el

    def mock_locator(sel: str) -> Any:
        if "copy" in sel:
            return copy_coll
        if "chat-assistant" in sel:
            return asst_coll
        empty = MagicMock()
        empty.count = AsyncMock(return_value=0)
        return empty

    mock_page.locator = MagicMock(side_effect=mock_locator)

    # evaluate returns HTML without thought blocks
    clean_html = "<div class='markdown'><p>Xin chào! Đây là câu trả lời từ GLM-5.3.</p></div>"
    mock_page.evaluate = AsyncMock(return_value=clean_html)

    answer = await adapter._extract_answer(mock_page, prompt="xin chao")
    assert "Xin chào! Đây là câu trả lời từ GLM-5.3." in answer
