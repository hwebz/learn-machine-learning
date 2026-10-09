from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)


class ZhipuUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.z.ai (Zhipu/GLM) web UI via Playwright (DOM locators only)."""

    name = "zhipu"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """No mode switching for Zhipu in V1."""
        return
