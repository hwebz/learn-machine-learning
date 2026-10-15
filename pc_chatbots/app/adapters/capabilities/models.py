from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class OptionItem(BaseModel):
    """Generic selectable option (model, thinking level, mode)."""
    id: str
    label: str
    description: str | None = None
    selected: bool = False
    disabled: bool = False
    badge: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SupportedDataTypes(BaseModel):
    """Input modalities and file types supported by the provider/model."""
    text: bool = True
    image: bool = False
    file: bool = False
    audio: bool = False
    video: bool = False
    max_file_size_mb: int | None = 50
    supported_mime_types: list[str] = Field(default_factory=lambda: ["image/*", ".pdf", ".txt", ".csv", ".json", ".py", ".md", ".docx"])


class VoiceChatSupport(BaseModel):
    """Voice chat / speech-to-text input capability."""
    supported: bool = True
    mode: Literal["backend_stt", "browser_stt", "none"] = "backend_stt"
    details: str | None = "Hỗ trợ nhập liệu bằng giọng nói (Voice-to-Text) bất đồng bộ qua backend."


class ProviderLiveCapabilities(BaseModel):
    """Full snapshot of live or default options for an AI provider."""
    model_config = {"extra": "ignore"}

    provider: str
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_live_dom: bool = False
    available_models: list[OptionItem] = Field(default_factory=list)
    selected_model_id: str | None = None
    thinking_levels: list[OptionItem] = Field(default_factory=list)
    selected_thinking_level_id: str | None = None
    modes: list[OptionItem] = Field(default_factory=list)
    selected_mode_id: str | None = None
    account_type: str | None = None
    supported_data_types: SupportedDataTypes = Field(default_factory=SupportedDataTypes)
    voice_chat: VoiceChatSupport = Field(default_factory=VoiceChatSupport)
    deep_thinking: bool = False
    web_search: bool = True
    deep_research: bool = False
    last_error: str | None = None


class ProviderSelectionRequest(BaseModel):
    """Options chosen by user to apply during prompt execution."""
    model_config = {"extra": "ignore"}

    model_id: str | None = None
    thinking_level_id: str | None = None
    mode_id: str | None = None
    deep_thinking: bool | None = None
    web_search: bool | None = None
    deep_research: bool | None = None
    custom_params: dict[str, Any] = Field(default_factory=dict)
