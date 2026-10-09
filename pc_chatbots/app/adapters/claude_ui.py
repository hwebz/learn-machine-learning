from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class ClaudeUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in claude.ai web UI via Playwright (DOM locators only)."""

    name = "claude"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Best-effort model switch. Failure is non-fatal."""
        if mode not in {"deep", "research", "pro"}:
            return
        chain = (self._cfg.get("mode_selectors") or {}).get("extended_thinking")
        if not chain:
            return
        locator, _ = await resolve_locator(page, chain)
        if locator is None:
            logger.info("claude_mode_skipped", mode=mode)
            return
        try:
            await locator.click(timeout=3000)
            logger.info("claude_mode_selected", mode=mode)
        except Exception as exc:  # noqa: BLE001 — mode switch is optional
            logger.warning("claude_mode_click_failed", error=str(exc))
