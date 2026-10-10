from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class GrokUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in grok.com web UI via Playwright (DOM locators only)."""

    name = "grok"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Grok mode (Expert / Heavy / DeepSearch vs Fast / Auto)."""
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        cfg_modes = self._cfg.get("mode_selectors") or {}

        dropdown_chain = cfg_modes.get("model_dropdown")
        if dropdown_chain:
            locator, _ = await resolve_locator(page, dropdown_chain)
            if locator is not None:
                try:
                    curr_text = (await locator.inner_text()).strip().lower()
                    if is_deep and ("expert" in curr_text or "heavy" in curr_text):
                        logger.info("grok_mode_already_deep")
                        return
                    if not is_deep and "fast" in curr_text:
                        logger.info("grok_mode_already_fast")
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
                            logger.info("grok_mode_selected", mode=mode, target=target_key)
                            await asyncio.sleep(0.8)
                            return
                    await page.keyboard.press("Escape")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("grok_mode_switch_failed", error=str(exc))

        # Fallback to deep_search button
        if is_deep:
            ds_chain = cfg_modes.get("deep_search")
            if ds_chain:
                ds_loc, _ = await resolve_locator(page, ds_chain)
                if ds_loc:
                    try:
                        await ds_loc.click(timeout=3000)
                        logger.info("grok_mode_selected", mode=mode, via="deep_search")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("grok_deep_search_click_failed", error=str(exc))

