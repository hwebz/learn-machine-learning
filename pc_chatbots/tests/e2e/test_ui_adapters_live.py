from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


@pytest.mark.live
@pytest.mark.asyncio
async def test_perplexity_ui_adapter_answers() -> None:
    from app.adapters.perplexity_ui import PerplexityUIAdapter

    adapter = PerplexityUIAdapter()
    result = await adapter.ask("Reply with the single word: pong", timeout_s=180, mode="default")
    assert result.status in {"ok", "partial", "needs_user_action", "timeout"}
    if result.status == "ok":
        assert result.answer_markdown.strip()
        assert result.conversation_url is not None
        assert str(result.conversation_url).startswith("https://")


@pytest.mark.live
@pytest.mark.asyncio
async def test_gemini_ui_adapter_answers() -> None:
    from app.adapters.gemini_ui import GeminiUIAdapter

    adapter = GeminiUIAdapter()
    result = await adapter.ask("Reply with the single word: pong", timeout_s=180, mode="default")
    assert result.status in {"ok", "partial", "needs_user_action", "timeout"}
    if result.status == "ok":
        assert result.answer_markdown.strip()
