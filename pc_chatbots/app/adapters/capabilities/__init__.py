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
]

