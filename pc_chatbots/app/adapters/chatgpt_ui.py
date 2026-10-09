from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class ChatGPTUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chatgpt.com web UI via Playwright (DOM locators only)."""

    name = "chatgpt"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Best-effort model/mode switch. Failure is non-fatal."""
        if mode not in {"deep", "research", "pro"}:
            return
        chain = (self._cfg.get("mode_selectors") or {}).get("research_mode")
        if not chain:
            return
        locator, _ = await resolve_locator(page, chain)
        if locator is None:
            logger.info("chatgpt_mode_skipped", mode=mode)
            return
        try:
            await locator.click(timeout=3000)
            logger.info("chatgpt_mode_selected", mode=mode)
        except Exception as exc:  # noqa: BLE001 — mode switch is optional
            logger.warning("chatgpt_mode_click_failed", error=str(exc))
