from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)


from app.browser.locators import resolve_locator


class MetaUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in meta.ai web UI via Playwright (DOM locators only)."""

    name = "meta"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Meta AI composer mode (Thinking vs Standard)."""
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        cfg_modes = self._cfg.get("mode_selectors") or {}

        dropdown_chain = cfg_modes.get("mode_dropdown")
        if not dropdown_chain:
            return
        locator, _ = await resolve_locator(page, dropdown_chain)
        if locator is None:
            logger.info("meta_mode_dropdown_not_found")
            return

        try:
            curr_text = (await locator.inner_text()).strip().lower()
            if is_deep and "thinking" in curr_text:
                logger.info("meta_mode_already_thinking")
                return
            if not is_deep and ("standard" in curr_text or "normal" in curr_text):
                logger.info("meta_mode_already_standard")
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
                    logger.info("meta_mode_selected", mode=mode, target=target_key)
                    await asyncio.sleep(0.8)
                    return
            await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001
            logger.warning("meta_mode_switch_failed", error=str(exc))

