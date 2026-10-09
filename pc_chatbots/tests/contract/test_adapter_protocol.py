from __future__ import annotations

import inspect

import pytest

from app.adapters.chatgpt_ui import ChatGPTUIAdapter
from app.adapters.claude_ui import ClaudeUIAdapter
from app.adapters.copilot_ui import CopilotUIAdapter
from app.adapters.deepseek_ui import DeepSeekUIAdapter
from app.adapters.gemini_ui import GeminiUIAdapter
from app.adapters.grok_ui import GrokUIAdapter
from app.adapters.kimi_ui import KimiUIAdapter
from app.adapters.meta_ui import MetaUIAdapter
from app.adapters.minimax_ui import MinimaxUIAdapter
from app.adapters.mistral_ui import MistralUIAdapter
from app.adapters.perplexity_ui import PerplexityUIAdapter
from app.adapters.pi_ui import PiUIAdapter
from app.adapters.qwen_ui import QwenUIAdapter
from app.adapters.zhipu_ui import ZhipuUIAdapter

ALL_UI_ADAPTERS = [
    (PerplexityUIAdapter, "perplexity"),
    (GeminiUIAdapter, "gemini"),
    (ChatGPTUIAdapter, "chatgpt"),
    (ClaudeUIAdapter, "claude"),
    (CopilotUIAdapter, "copilot"),
    (DeepSeekUIAdapter, "deepseek"),
    (GrokUIAdapter, "grok"),
    (KimiUIAdapter, "kimi"),
    (MetaUIAdapter, "meta"),
    (MinimaxUIAdapter, "minimax"),
    (MistralUIAdapter, "mistral"),
    (PiUIAdapter, "pi"),
    (QwenUIAdapter, "qwen"),
    (ZhipuUIAdapter, "zhipu"),
]


@pytest.mark.parametrize("adapter_cls,name", ALL_UI_ADAPTERS)
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
@pytest.mark.parametrize("adapter_cls,name", ALL_UI_ADAPTERS)
async def test_ui_adapters_health_is_static_and_safe(adapter_cls, name: str) -> None:
    """health() must never launch a browser; it only inspects config + profile dir."""
    adapter = adapter_cls()
    result = await adapter.health()
    assert result.selectors_ok is True  # selectors.yaml is validated at load
    assert isinstance(result.logged_in, bool)
    assert result.detail is not None
