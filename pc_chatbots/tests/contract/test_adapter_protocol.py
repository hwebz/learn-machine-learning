from __future__ import annotations

import inspect

import pytest

from app.adapters.gemini_ui import GeminiUIAdapter
from app.adapters.perplexity_ui import PerplexityUIAdapter


@pytest.mark.parametrize("adapter_cls,name", [(PerplexityUIAdapter, "perplexity"), (GeminiUIAdapter, "gemini")])
def test_ui_adapter_satisfies_provider_adapter_protocol(adapter_cls, name: str) -> None:
    adapter = adapter_cls()
    # Structural check against the ProviderAdapter Protocol (not runtime_checkable,
    # so we assert the members exist rather than using isinstance()).
    assert hasattr(adapter, "health") and callable(adapter.health)
    assert hasattr(adapter, "ask") and callable(adapter.ask)
    assert adapter.name == name

    health_sig = inspect.signature(adapter.health)
    assert list(health_sig.parameters) == []  # health() takes no args

    ask_sig = inspect.signature(adapter.ask)
    assert "prompt" in ask_sig.parameters
    assert "timeout_s" in ask_sig.parameters
    assert ask_sig.parameters["prompt"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert ask_sig.parameters["timeout_s"].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.asyncio
async def test_ui_adapters_health_is_static_and_safe() -> None:
    """health() must never launch a browser; it only inspects config + profile dir."""
    for adapter_cls in (PerplexityUIAdapter, GeminiUIAdapter):
        adapter = adapter_cls()
        result = await adapter.health()
        assert result.selectors_ok is True  # selectors.yaml is validated at load
        assert isinstance(result.logged_in, bool)
        assert result.detail is not None
