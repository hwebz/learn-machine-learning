from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import structlog

from app.adapters.capabilities.base import BaseProviderCapabilitiesStrategy
from app.adapters.capabilities.models import (
    ProviderLiveCapabilities,
    SupportedDataTypes,
    VoiceChatSupport,
)

logger = structlog.get_logger(__name__)


class GrokCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for xAI Grok (grok.com / x.com/i/grok).

    For Free accounts, there are no configurable models, reasoning efforts, or modes.
    Everything uses default parameters directly from Grok.
    """

    @property
    def provider_name(self) -> str:
        return "grok"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Default capabilities for Free xAI Grok: empty options, all default."""
        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=25,
            supported_mime_types=["image/*", ".txt", ".pdf"],
        )

        voice = VoiceChatSupport(
            supported=False,
            mode="none",
            details="Chưa hỗ trợ nhập giọng nói trực tiếp.",
        )

        return ProviderLiveCapabilities(
            provider="grok",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=[],
            selected_model_id=None,
            thinking_levels=[],
            selected_thinking_level_id=None,
            modes=[],
            selected_mode_id=None,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Grok is on a Free account without customizable options in the DOM; returns safe defaults."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        caps.is_live_dom = True
        return caps

    async def apply_selection(self, page: Any, config: Any) -> None:
        """Grok is on a Free account, so no custom options are configured; use all default."""
        logger.info("grok_apply_selection_noop", reason="free_account_default")
        return
