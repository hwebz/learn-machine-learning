from __future__ import annotations

import pytest

from app.orchestrator.pipeline import _UI_ADAPTERS

pytestmark = pytest.mark.live


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.parametrize("name,adapter_cls", sorted(_UI_ADAPTERS.items()))
async def test_ui_adapter_answers(name: str, adapter_cls: type) -> None:
    adapter = adapter_cls()
    result = await adapter.ask("Reply with the single word: pong", timeout_s=180, mode="default")
    assert result.status in {"ok", "partial", "needs_user_action", "timeout"}
    if result.status == "ok":
        assert result.answer_markdown.strip()
        if name == "perplexity":
            assert result.conversation_url is not None
            assert str(result.conversation_url).startswith("https://")
