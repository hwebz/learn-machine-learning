from __future__ import annotations

import pytest
from app.browser.manual import ManualBrowserManager


def test_get_provider_url():
    url = ManualBrowserManager.get_provider_url("qwen")
    assert "qwen" in url
    copilot_url = ManualBrowserManager.get_provider_url("copilot")
    assert "copilot" in copilot_url or "bing" in copilot_url or "microsoft" in copilot_url


def test_is_open_default_false():
    assert ManualBrowserManager.is_open("non_existent_provider_xyz") is False


@pytest.mark.asyncio
async def test_close_browser_idempotent():
    res = await ManualBrowserManager.close_browser("qwen")
    assert res["status"] == "closed"
    assert res["provider"] == "qwen"
