from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)


class PiUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in pi.ai web UI via Playwright (DOM locators only)."""

    name = "pi"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """No mode switching for Pi AI in V1."""
        return
