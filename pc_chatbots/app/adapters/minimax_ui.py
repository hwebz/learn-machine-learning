from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)


class MinimaxUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in agent.minimax.io web UI via Playwright (DOM locators only)."""

    name = "minimax"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """No mode switching for Minimax in V1."""
        return
