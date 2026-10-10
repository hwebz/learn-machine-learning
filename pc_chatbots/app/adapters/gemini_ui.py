from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class GeminiUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in gemini.google.com web UI via Playwright (DOM locators only)."""

    name = "gemini"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Configure Gemini model (Pro vs Flash) and thinking effort (Cao vs Thấp)."""
        import asyncio

        cfg_modes = self._cfg.get("mode_selectors") or {}
        dropdown_chain = cfg_modes.get("mode_dropdown")
        if not dropdown_chain:
            return
        btn, _ = await resolve_locator(page, dropdown_chain)
        if btn is None:
            logger.info("gemini_mode_dropdown_not_found")
            return
        is_deep = mode in {"deep", "deep_research"}
        try:
            curr_text = (await btn.inner_text()).strip().lower()

            # 1. Select Pro / Flash if needed
            target_model = "pro_model" if is_deep else "flash_model"
            need_model_switch = (is_deep and "pro" not in curr_text) or (not is_deep and "flash" not in curr_text and "pro" in curr_text)
            if need_model_switch:
                await btn.click(timeout=4000)
                await asyncio.sleep(0.5)
                m_loc, _ = await resolve_locator(page, cfg_modes.get(target_model, []))
                if m_loc is not None:
                    await m_loc.click(timeout=4000)
                    logger.info("gemini_model_selected", target=target_model)
                    await asyncio.sleep(1.0)
                else:
                    await page.keyboard.press("Escape")

            # 2. Select Thinking effort Cao (High) if deep mode is requested
            if is_deep:
                curr_text = (await btn.inner_text()).strip().lower()
                if "cao" not in curr_text and "high" not in curr_text:
                    await btn.click(timeout=4000)
                    await asyncio.sleep(0.5)
                    t_loc, _ = await resolve_locator(page, cfg_modes.get("thinking_high", []))
                    if t_loc is not None:
                        await t_loc.click(timeout=4000)
                        logger.info("gemini_thinking_selected", target="thinking_high")
                        await asyncio.sleep(1.0)
                    else:
                        await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001 — mode switch is best-effort
            logger.warning("gemini_mode_click_failed", error=str(exc))
