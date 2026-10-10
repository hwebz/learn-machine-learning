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
        """Switch Claude model (Sonnet / Extended thinking vs Haiku)."""
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        cfg_modes = self._cfg.get("mode_selectors") or {}

        dropdown_chain = cfg_modes.get("model_dropdown")
        if not dropdown_chain:
            return
        locator, _ = await resolve_locator(page, dropdown_chain)
        if locator is None:
            # Fallback directly to extended_thinking toggle if dropdown not visible
            ext_chain = cfg_modes.get("extended_thinking")
            if is_deep and ext_chain:
                ext_loc, _ = await resolve_locator(page, ext_chain)
                if ext_loc:
                    await ext_loc.click(timeout=3000)
            return

        try:
            curr_text = (await locator.inner_text()).strip().lower()
            if is_deep and ("sonnet" in curr_text or "thinking" in curr_text):
                logger.info("claude_mode_already_deep")
                return
            if not is_deep and "haiku" in curr_text:
                logger.info("claude_mode_already_haiku")
                return

            await locator.click(timeout=4000)
            import asyncio
            await asyncio.sleep(0.8)

            target_key = "sonnet_model" if is_deep else "haiku_model"
            target_chain = cfg_modes.get(target_key)
            if target_chain:
                item_loc, _ = await resolve_locator(page, target_chain)
                if item_loc is not None:
                    await item_loc.click(timeout=4000)
                    logger.info("claude_mode_selected", mode=mode, target=target_key)
                    await asyncio.sleep(0.8)
                    return
            await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001
            logger.warning("claude_mode_switch_failed", error=str(exc))

