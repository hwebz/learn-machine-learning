from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)


class MistralUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.mistral.ai web UI via Playwright (DOM locators only)."""

    name = "mistral"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """No mode switching for Mistral in V1."""
        return
