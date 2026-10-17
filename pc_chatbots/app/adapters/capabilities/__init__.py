from __future__ import annotations

from app.adapters.capabilities.models import (
    OptionItem,
    ProviderLiveCapabilities,
    ProviderSelectionRequest,
    SupportedDataTypes,
    VoiceChatSupport,
)
from app.adapters.capabilities.base import (
    BaseProviderCapabilitiesStrategy,
    ICapabilitiesApplier,
    ICapabilitiesInspector,
    IVoiceTranscriber,
)
from app.adapters.capabilities.registry import CapabilitiesRegistry
from app.adapters.capabilities.voice import VoiceTranscriberService
from app.adapters.capabilities.chatgpt import ChatGPTCapabilitiesStrategy
from app.adapters.capabilities.copilot import CopilotCapabilitiesStrategy
from app.adapters.capabilities.gemini import GeminiCapabilitiesStrategy
from app.adapters.capabilities.qwen import QwenCapabilitiesStrategy
from app.adapters.capabilities.claude import ClaudeCapabilitiesStrategy
from app.adapters.capabilities.deepseek import DeepSeekCapabilitiesStrategy
from app.adapters.capabilities.perplexity import PerplexityCapabilitiesStrategy
from app.adapters.capabilities.kimi import KimiCapabilitiesStrategy
from app.adapters.capabilities.grok import GrokCapabilitiesStrategy
from app.adapters.capabilities.mistral import MistralCapabilitiesStrategy
from app.adapters.capabilities.zhipu import ZhipuCapabilitiesStrategy
from app.adapters.capabilities.minimax import MinimaxCapabilitiesStrategy
from app.adapters.capabilities.meta import MetaCapabilitiesStrategy

__all__ = [
    "OptionItem",
    "SupportedDataTypes",
    "VoiceChatSupport",
    "ProviderLiveCapabilities",
    "ProviderSelectionRequest",
    "ICapabilitiesInspector",
    "ICapabilitiesApplier",
    "IVoiceTranscriber",
    "BaseProviderCapabilitiesStrategy",
    "VoiceTranscriberService",
    "CapabilitiesRegistry",
    "ChatGPTCapabilitiesStrategy",
    "CopilotCapabilitiesStrategy",
    "GeminiCapabilitiesStrategy",
    "QwenCapabilitiesStrategy",
    "ClaudeCapabilitiesStrategy",
    "DeepSeekCapabilitiesStrategy",
    "PerplexityCapabilitiesStrategy",
    "KimiCapabilitiesStrategy",
    "GrokCapabilitiesStrategy",
    "MistralCapabilitiesStrategy",
    "ZhipuCapabilitiesStrategy",
    "MinimaxCapabilitiesStrategy",
    "MetaCapabilitiesStrategy",
]

