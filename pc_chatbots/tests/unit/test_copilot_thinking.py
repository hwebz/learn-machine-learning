from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.browser.waits import DOM_SCAN_THINKING_AND_CITATIONS, wait_for_completion


def test_copilot_cot_syntax_and_tokens() -> None:
    assert "scc-ChainOfThought" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "scc-BebopChainOfThought" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "scc-BebopChainOfThoughtItem" in DOM_SCAN_THINKING_AND_CITATIONS
    assert "r1fgiwrn" in DOM_SCAN_THINKING_AND_CITATIONS

    # If node is installed, verify JS syntax
    if shutil.which("node"):
        js_code = f"function test(provider) {{\n{DOM_SCAN_THINKING_AND_CITATIONS}\n}}"
        res = subprocess.run(
            ["node", "--input-type=module", "--check"],
            input=js_code,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        assert res.returncode == 0, f"JS Syntax check failed: {res.stderr}"


@pytest.mark.asyncio
async def test_wait_for_completion_copilot_cot_streaming() -> None:
    poll_events: list[dict] = []

    async def mock_on_poll(**kwargs) -> None:
        poll_events.append(kwargs)

    mock_page = MagicMock()
    mock_page.url = "https://copilot.microsoft.com"
    mock_page.locator.return_value.inner_text = AsyncMock(return_value="Copilot response")
    mock_page.evaluate = AsyncMock(return_value={
        "is_thinking": True,
        "thinking_text": "Identifying web requirements:\nI am considering...",
        "thinking_steps": [
            {
                "title": "Identifying web requirements",
                "description": "I am considering...",
                "status": "completed",
            },
            {
                "title": "Searching for model details",
                "description": "Looking up details...",
                "status": "running",
            },
        ],
        "citations": [
            {"url": "https://support.microsoft.com/copilot", "title": "Microsoft Copilot"}
        ],
    })

    clock_val = 1000.0

    def fake_clock() -> float:
        nonlocal clock_val
        clock_val += 0.5
        return clock_val

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
        completion_cfg={"stable_seconds": 0.5, "poll_interval_s": 0.5},
        timeout_s=1.0,
        on_poll=mock_on_poll,
        thinking_interval_s=0.5,
        clock=fake_clock,
    )

    assert len(poll_events) > 0
    first_poll = poll_events[0]
    assert first_poll["is_thinking"] is True
    assert len(first_poll["thinking_steps"]) == 2
    assert first_poll["thinking_steps"][0]["title"] == "Identifying web requirements"
    assert first_poll["thinking_steps"][0]["status"] == "completed"
    assert first_poll["thinking_steps"][1]["title"] == "Searching for model details"
    assert first_poll["thinking_steps"][1]["status"] == "running"
    assert len(first_poll["citations"]) == 1


SAMPLE_COPILOT_COT_HTML = """
<div class="scc-ChainOfThought scc-BebopChainOfThought">
    <div>
        <button class="scc-ChainOfThought__expandButton" aria-expanded="true">
            <span class="scc-ChainOfThought__headerText">Reasoning completed in 2 steps</span>
        </button>
    </div>
    <div class="scc-ChainOfThought__activitiesPanel">
        <div role="list" class="scc-ChainOfThought__activitiesAccordion">
            <div role="listitem" class="scc-BebopChainOfThoughtItem">
                <div class="scc-BebopChainOfThoughtItem__header">
                    <span class="scc-BebopChainOfThoughtItem__statusIndicator">
                        <svg viewBox="0 0 20 20"><path d="M10 2a8 8 0 1 1 0 16 8 8 0 0 1 0-16"></path></svg>
                    </span>
                    <h3 class="scc-BebopChainOfThoughtItem__headerText">Analyzing query context</h3>
                </div>
                <div class="scc-BebopChainOfThoughtItem__content">
                    <div class="scc-BebopChainOfThoughtItem__contentText">
                        <p>First step analysis details here.</p>
                    </div>
                </div>
            </div>
            <div role="listitem" class="scc-BebopChainOfThoughtItem">
                <div class="scc-BebopChainOfThoughtItem__header">
                    <span class="scc-BebopChainOfThoughtItem__statusIndicator">
                        <svg viewBox="0 0 20 20"><path d="M10 2a8 8 0 1 1 0 16 8 8 0 0 1 0-16"></path></svg>
                    </span>
                    <h3 class="scc-BebopChainOfThoughtItem__headerText">Searches</h3>
                </div>
                <div class="scc-BebopChainOfThoughtItem__content">
                    <div class="scc-BebopChainOfThoughtItem__contentText">
                        <div class="scc-BebopChainOfThoughtItem__interstitialPillsContainer">
                            <span class="r1rkpcak"><span class="r1fgiwrn">Copilot reasoning official</span></span>
                            <span class="r1rkpcak"><span class="r1fgiwrn">M365 Copilot deep think</span></span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
"""


@pytest.mark.asyncio
async def test_copilot_cot_dom_scan_evaluation() -> None:
    from playwright.async_api import async_playwright
    from app.core.config import settings

    channel = settings.browser_channel if settings.browser_channel != "chromium" else None
    try:
        async with async_playwright() as p:
            launch_args = {"headless": True}
            if channel:
                launch_args["channel"] = channel
            browser = await p.chromium.launch(**launch_args)
            page = await browser.new_page()
            await page.set_content(SAMPLE_COPILOT_COT_HTML)

            result = await page.evaluate(DOM_SCAN_THINKING_AND_CITATIONS, "copilot")
            await browser.close()

            assert result["is_thinking"] is True
            assert len(result["thinking_steps"]) == 2
            assert result["thinking_steps"][0]["title"] == "Analyzing query context"
            assert "First step analysis" in result["thinking_steps"][0]["description"]
            assert result["thinking_steps"][1]["title"] == "Searches"
            assert "Copilot reasoning official" in result["thinking_steps"][1]["description"]
            assert "M365 Copilot deep think" in result["thinking_steps"][1]["description"]
    except Exception as exc:
        if "Executable doesn't exist" in str(exc) or "browserType.launch" in str(exc):
            pytest.skip(f"Browser not available in this test environment: {exc}")
        raise
