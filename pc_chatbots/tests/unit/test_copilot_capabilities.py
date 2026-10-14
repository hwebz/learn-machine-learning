from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.adapters.capabilities.copilot import CopilotCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest
from app.adapters.capabilities.registry import CapabilitiesRegistry


def test_copilot_capabilities_registration() -> None:
    reg = CapabilitiesRegistry.instance()
    strat = reg.get_strategy("copilot")
    assert isinstance(strat, CopilotCapabilitiesStrategy)
    assert strat.provider_name == "copilot"


def test_copilot_default_capabilities() -> None:
    strat = CopilotCapabilitiesStrategy()
    caps = strat.get_default_capabilities()

    assert caps.provider == "copilot"
    assert len(caps.modes) == 5
    mode_ids = [m.id for m in caps.modes]
    assert mode_ids == ["auto", "quick", "think_deeper", "gpt_5_6_quick", "gpt_5_6_think"]

    mode_labels = [m.label for m in caps.modes]
    assert "Auto" in mode_labels
    assert "Quick Response" in mode_labels
    assert "Think Deeper" in mode_labels
    assert "GPT > GPT-5.6 Sol Quick Response" in mode_labels
    assert "GPT > GPT-5.6 Sol Think Deeper" in mode_labels

    assert caps.selected_mode_id == "auto"
    assert len(caps.available_models) == 1
    assert caps.available_models[0].id == "auto"
    assert len(caps.thinking_levels) == 1
    assert caps.thinking_levels[0].id == "auto"
    assert caps.supported_data_types.image is True
    assert caps.supported_data_types.file is True
    assert caps.voice_chat.supported is True


@pytest.mark.asyncio
async def test_copilot_apply_selection_root_mode() -> None:
    strat = CopilotCapabilitiesStrategy()
    mock_page = MagicMock()

    # Mock mode switcher button
    mock_btn = MagicMock()
    mock_btn.count = AsyncMock(return_value=1)
    mock_btn.inner_text = AsyncMock(return_value="Auto")
    mock_btn.click = AsyncMock()

    # Mock menu item
    mock_item = MagicMock()
    mock_item.count = AsyncMock(return_value=1)
    mock_item.is_visible = AsyncMock(return_value=True)
    mock_item.click = AsyncMock()

    def locator_side_effect(selector: str, *args, **kwargs):
        loc = MagicMock()
        if "gptModeSwitcher" in selector:
            loc.first = mock_btn
            return loc
        if "Think Deeper" in selector:
            loc.first = mock_item
            return loc
        loc.count = AsyncMock(return_value=0)
        loc.first = loc
        return loc

    mock_page.locator.side_effect = locator_side_effect

    req = ProviderSelectionRequest(mode_id="think_deeper")
    await strat.apply_selection(mock_page, req)

    mock_btn.click.assert_awaited_once()
    mock_item.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_copilot_apply_selection_gpt_subitem() -> None:
    strat = CopilotCapabilitiesStrategy()
    mock_page = MagicMock()

    mock_btn = MagicMock()
    mock_btn.count = AsyncMock(return_value=1)
    mock_btn.inner_text = AsyncMock(return_value="Auto")
    mock_btn.click = AsyncMock()

    mock_gpt = MagicMock()
    mock_gpt.count = AsyncMock(return_value=1)
    mock_gpt.is_visible = AsyncMock(return_value=True)
    mock_gpt.hover = AsyncMock()

    mock_sub = MagicMock()
    mock_sub.count = AsyncMock(return_value=1)
    mock_sub.is_visible = AsyncMock(return_value=True)
    mock_sub.click = AsyncMock()

    def locator_side_effect(selector: str, *args, **kwargs):
        loc = MagicMock()
        if "gptModeSwitcher" in selector:
            loc.first = mock_btn
            return loc
        if "GPT" in selector and "Sol" not in selector:
            loc.first = mock_gpt
            return loc
        if "Quick Response" in selector:
            loc.last = mock_sub
            return loc
        loc.count = AsyncMock(return_value=0)
        loc.first = loc
        return loc

    mock_page.locator.side_effect = locator_side_effect

    req = ProviderSelectionRequest(mode_id="gpt_5_6_quick")
    await strat.apply_selection(mock_page, req)

    mock_btn.click.assert_awaited_once()
    mock_gpt.hover.assert_awaited_once()
    mock_sub.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_copilot_inspect_dom() -> None:
    strat = CopilotCapabilitiesStrategy()
    mock_page = MagicMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.keyboard.press = AsyncMock()

    mock_tile = MagicMock()
    mock_tile.count = AsyncMock(return_value=0)

    mock_comm = MagicMock()
    mock_comm.count = AsyncMock(return_value=1)
    mock_comm.is_visible = AsyncMock(return_value=True)

    mock_btn = MagicMock()
    mock_btn.count = AsyncMock(return_value=1)
    mock_btn.is_visible = AsyncMock(return_value=True)
    mock_btn.inner_text = AsyncMock(return_value="Auto")
    mock_btn.get_attribute = AsyncMock(return_value="Auto, Model Selector")
    mock_btn.click = AsyncMock()

    mock_plus = MagicMock()
    mock_plus.count = AsyncMock(return_value=1)
    mock_plus.is_visible = AsyncMock(return_value=True)
    mock_plus.click = AsyncMock()

    mock_dict = MagicMock()
    mock_dict.count = AsyncMock(return_value=1)

    def locator_side_effect(selector: str, *args, **kwargs):
        loc = MagicMock()
        if "Pick an account" in selector or "div.row.tile" in selector:
            loc.first = mock_tile
            return loc
        if "Commercial" in selector:
            loc.first = mock_comm
            return loc
        if "gptModeSwitcher" in selector:
            loc.first = mock_btn
            return loc
        if "PlusMenuButton" in selector:
            loc.first = mock_plus
            return loc
        if "dictation" in selector:
            loc.first = mock_dict
            return loc
        loc.count = AsyncMock(return_value=0)
        loc.first = loc
        return loc

    mock_page.locator.side_effect = locator_side_effect

    mock_page.evaluate = AsyncMock(side_effect=[
        # Root items in mode dropdown
        [
            {"text": "Auto", "aria": "", "hasPopup": False, "isChecked": True},
            {"text": "Quick Response", "aria": "", "hasPopup": False, "isChecked": False},
            {"text": "Think Deeper", "aria": "", "hasPopup": False, "isChecked": False},
            {"text": "GPT", "aria": "", "hasPopup": True, "isChecked": False},
        ],
        # Sub-items under GPT
        [
            {"text": "GPT-5.6 Sol Quick Response", "aria": "", "isChecked": False},
            {"text": "GPT-5.6 Sol Think Deeper", "aria": "", "isChecked": False},
        ],
        # Plus menu options
        ["Upload images and files", "Add from OneDrive"],
    ])

    caps = await strat.inspect_dom(mock_page)
    assert caps.is_live_dom is True
    assert caps.account_type == "commercial"
    assert caps.selected_mode_id == "auto"
    assert len(caps.modes) == 5
    assert caps.supported_data_types.image is True
    assert caps.supported_data_types.file is True
