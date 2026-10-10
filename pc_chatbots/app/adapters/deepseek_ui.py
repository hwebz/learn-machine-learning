from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class DeepSeekUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.deepseek.com web UI via Playwright (DOM locators only)."""

    name = "deepseek"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch DeepSeek mode (DeepThink R1 toggle)."""
        is_deep = mode in {"deep", "deep_research", "research"}
        chain = (self._cfg.get("mode_selectors") or {}).get("deep_think")
        if not chain:
            return
        locator, _ = await resolve_locator(page, chain)
        if locator is None:
            logger.info("deepseek_mode_skipped", mode=mode)
            return
        try:
            aria_pressed = await locator.get_attribute("aria-pressed")
            cls = await locator.get_attribute("class") or ""
            is_active = aria_pressed == "true" or "selected" in cls

            if is_deep and not is_active:
                await locator.click(timeout=3000)
                logger.info("deepseek_mode_selected", mode=mode, action="deepthink_enabled")
            elif not is_deep and is_active:
                await locator.click(timeout=3000)
                logger.info("deepseek_mode_selected", mode=mode, action="deepthink_disabled")
            else:
                logger.info("deepseek_mode_already_set", mode=mode, is_active=is_active)
        except Exception as exc:  # noqa: BLE001
            logger.warning("deepseek_mode_click_failed", error=str(exc))

