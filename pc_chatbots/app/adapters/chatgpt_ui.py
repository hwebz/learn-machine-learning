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
        """Switch ChatGPT thinking mode (Think button pill) or Deep research."""
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        cfg_modes = self._cfg.get("mode_selectors") or {}

        # 1. Try toggling the "Think" button pill first
        think_chain = cfg_modes.get("think_toggle")
        if think_chain:
            locator, _ = await resolve_locator(page, think_chain)
            if locator is not None:
                try:
                    aria_pressed = await locator.get_attribute("aria-pressed")
                    is_pressed = aria_pressed == "true"
                    if is_deep and not is_pressed:
                        await locator.click(timeout=3000)
                        logger.info("chatgpt_mode_selected", mode=mode, action="think_enabled")
                        return
                    if not is_deep and is_pressed:
                        await locator.click(timeout=3000)
                        logger.info("chatgpt_mode_selected", mode=mode, action="think_disabled")
                        return
                    if (is_deep and is_pressed) or (not is_deep and not is_pressed):
                        logger.info("chatgpt_mode_already_set", mode=mode, is_pressed=is_pressed)
                        return
                except Exception as exc:  # noqa: BLE001
                    logger.warning("chatgpt_think_toggle_failed", error=str(exc))

        # 2. Fallback to research_mode if deep_research is requested
        if is_deep:
            chain = cfg_modes.get("research_mode")
            if not chain:
                return
            locator, _ = await resolve_locator(page, chain)
            if locator is None:
                logger.info("chatgpt_mode_skipped", mode=mode)
                return
            try:
                await locator.click(timeout=3000)
                logger.info("chatgpt_mode_selected", mode=mode)
            except Exception as exc:  # noqa: BLE001
                logger.warning("chatgpt_mode_click_failed", error=str(exc))

