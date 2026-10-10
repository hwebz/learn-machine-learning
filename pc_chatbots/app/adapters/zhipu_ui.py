from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)


from app.browser.locators import resolve_locator


class ZhipuUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.z.ai (Zhipu/GLM) web UI via Playwright (DOM locators only)."""

    name = "zhipu"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Zhipu mode (Thought Process toggle or GLM-5/Pro vs Flash)."""
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        cfg_modes = self._cfg.get("mode_selectors") or {}

        # 1. Try toggling "Thought Process" if available
        thought_chain = cfg_modes.get("thought_toggle")
        if thought_chain:
            locator, _ = await resolve_locator(page, thought_chain)
            if locator is not None:
                try:
                    aria_pressed = await locator.get_attribute("aria-pressed")
                    cls = await locator.get_attribute("class") or ""
                    is_active = aria_pressed == "true" or "active" in cls or "selected" in cls
                    if is_deep and not is_active:
                        await locator.click(timeout=3000)
                        logger.info("zhipu_thought_process_enabled", mode=mode)
                    elif not is_deep and is_active:
                        await locator.click(timeout=3000)
                        logger.info("zhipu_thought_process_disabled", mode=mode)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("zhipu_thought_toggle_failed", error=str(exc))

        # 2. Try model dropdown selector
        dropdown_chain = cfg_modes.get("model_dropdown")
        if dropdown_chain:
            locator, _ = await resolve_locator(page, dropdown_chain)
            if locator is not None:
                try:
                    curr_text = (await locator.inner_text()).strip().lower()
                    if is_deep and ("glm-5" in curr_text or "pro" in curr_text):
                        logger.info("zhipu_mode_already_deep")
                        return
                    if not is_deep and "flash" in curr_text:
                        logger.info("zhipu_mode_already_flash")
                        return

                    await locator.click(timeout=4000)
                    import asyncio
                    await asyncio.sleep(0.8)

                    target_key = "deep_model" if is_deep else "standard_model"
                    target_chain = cfg_modes.get(target_key)
                    if target_chain:
                        item_loc, _ = await resolve_locator(page, target_chain)
                        if item_loc is not None:
                            await item_loc.click(timeout=4000)
                            logger.info("zhipu_model_selected", mode=mode, target=target_key)
                            await asyncio.sleep(0.8)
                            return
                    await page.keyboard.press("Escape")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("zhipu_model_switch_failed", error=str(exc))

