from __future__ import annotations

import pytest

from app.adapters.capabilities import (
    BaseProviderCapabilitiesStrategy,
    CapabilitiesRegistry,
    ChatGPTCapabilitiesStrategy,
    ICapabilitiesApplier,
    ICapabilitiesInspector,
    IVoiceTranscriber,
    ProviderLiveCapabilities,
    VoiceTranscriberService,
)


def test_chatgpt_strategy_satisfies_protocols() -> None:
    strategy = ChatGPTCapabilitiesStrategy()
    assert isinstance(strategy, BaseProviderCapabilitiesStrategy)
    assert isinstance(strategy, ICapabilitiesInspector)
    assert isinstance(strategy, ICapabilitiesApplier)
    assert strategy.provider_name == "chatgpt"


def test_chatgpt_default_capabilities() -> None:
    strategy = ChatGPTCapabilitiesStrategy()
    caps = strategy.get_default_capabilities()
    assert isinstance(caps, ProviderLiveCapabilities)
    assert caps.provider == "chatgpt"
    assert len(caps.available_models) >= 1
    model_ids = [m.id for m in caps.available_models]
    assert "none" in model_ids
    assert caps.selected_model_id == "none"

    # Check thinking levels (free account has auto only)
    thinking_ids = [t.id for t in caps.thinking_levels]
    assert "auto" in thinking_ids
    assert caps.selected_thinking_level_id == "auto"

    # Check modes (Standard, Thinking)
    mode_ids = [m.id for m in caps.modes]
    assert "standard" in mode_ids
    assert "thinking" in mode_ids

    # Check data types and voice
    assert caps.supported_data_types.text is True
    assert caps.supported_data_types.image is True
    assert caps.supported_data_types.file is True
    assert caps.voice_chat.supported is True
    assert caps.voice_chat.mode == "backend_stt"


@pytest.mark.asyncio
async def test_capabilities_registry_lookup_and_defaults() -> None:
    registry = CapabilitiesRegistry.instance()
    caps = await registry.get_capabilities("chatgpt", force_sync=False)
    assert caps.provider == "chatgpt"
    assert caps.selected_model_id in ["auto", "gpt-6", "default", "none"]

    # Test unknown provider gets generic fallback
    fallback_caps = await registry.get_capabilities("unknown_prov", force_sync=False)
    assert fallback_caps.provider == "unknown_prov"
    assert len(fallback_caps.available_models) > 0


@pytest.mark.asyncio
async def test_voice_transcriber_service() -> None:
    service = VoiceTranscriberService()
    assert isinstance(service, IVoiceTranscriber)

    with pytest.raises(ValueError):
        await service.transcribe(b"")

    # Offline/fallback handling
    text = await service.transcribe(b"dummy audio content", filename="test.webm")
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.asyncio
async def test_mistral_capabilities_strategy() -> None:
    from app.adapters.capabilities.mistral import MistralCapabilitiesStrategy

    strategy = MistralCapabilitiesStrategy()
    assert isinstance(strategy, BaseProviderCapabilitiesStrategy)
    assert strategy.provider_name == "mistral"

    caps = strategy.get_default_capabilities()
    assert caps.provider == "mistral"
    # Requirement 1: No model selection available
    assert caps.available_models == []
    assert caps.selected_model_id is None

    # Requirement 2: Reasoning mode (Fast vs Think)
    thinking_ids = [t.id for t in caps.thinking_levels]
    assert "fast" in thinking_ids
    assert "think" in thinking_ids
    assert caps.selected_thinking_level_id == "fast"

    # Requirement 3: Deep Research toggle support
    assert caps.deep_research is False

    registry = CapabilitiesRegistry.instance()
    reg_strat = registry.get_strategy("mistral")
    assert isinstance(reg_strat, MistralCapabilitiesStrategy)

