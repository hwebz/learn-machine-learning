from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class KimiUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in kimi.ai web UI via Playwright (DOM locators only)."""

    name = "kimi"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Kimi model/effort (Thinking / K1.5 vs Instant / Standard)."""
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        cfg_modes = self._cfg.get("mode_selectors") or {}

        # 1. Try model dropdown trigger
        dropdown_chain = cfg_modes.get("model_dropdown")
        if dropdown_chain:
            locator, _ = await resolve_locator(page, dropdown_chain)
            if locator is not None:
                try:
                    curr_text = (await locator.inner_text()).strip().lower()
                    if is_deep and ("thinking" in curr_text or "k1" in curr_text):
                        logger.info("kimi_mode_already_deep")
                        return
                    if not is_deep and "instant" in curr_text:
                        logger.info("kimi_mode_already_instant")
                        return

                    await locator.click(timeout=4000)
                    import asyncio
                    await asyncio.sleep(0.8)

                    target_key = "deep_mode" if is_deep else "standard_mode"
                    target_chain = cfg_modes.get(target_key)
                    if target_chain:
                        item_loc, _ = await resolve_locator(page, target_chain)
                        if item_loc is not None:
                            await item_loc.click(timeout=4000)
                            logger.info("kimi_mode_selected", mode=mode, target=target_key)
                            await asyncio.sleep(0.8)
                            return
                    await page.keyboard.press("Escape")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("kimi_mode_switch_failed", error=str(exc))

        # 2. Fallback to search_mode button
        if is_deep:
            search_chain = cfg_modes.get("search_mode")
            if search_chain:
                s_loc, _ = await resolve_locator(page, search_chain)
                if s_loc:
                    try:
                        await s_loc.click(timeout=3000)
                        logger.info("kimi_mode_selected", mode=mode, via="search_mode")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("kimi_search_mode_click_failed", error=str(exc))

