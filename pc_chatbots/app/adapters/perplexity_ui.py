from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class PerplexityUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in perplexity.ai web UI via Playwright (DOM locators only)."""

    name = "perplexity"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Perplexity mode (Pro vs standard Search)."""
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        mode_selectors = self._cfg.get("mode_selectors") or {}

        # Check pro_toggle
        pro_chain = mode_selectors.get("pro_toggle")
        if pro_chain:
            locator, _ = await resolve_locator(page, pro_chain)
            if locator is not None:
                try:
                    aria_pressed = await locator.get_attribute("aria-pressed")
                    cls = await locator.get_attribute("class") or ""
                    is_active = aria_pressed == "true" or "selected" in cls or "active" in cls

                    if is_deep and not is_active:
                        await locator.click(timeout=3000)
                        logger.info("perplexity_mode_selected", mode=mode, action="pro_enabled")
                        return
                    if not is_deep and is_active:
                        await locator.click(timeout=3000)
                        logger.info("perplexity_mode_selected", mode=mode, action="pro_disabled")
                        return
                    if (is_deep and is_active) or (not is_deep and not is_active):
                        logger.info("perplexity_mode_already_set", mode=mode, is_active=is_active)
                        return
                except Exception as exc:  # noqa: BLE001
                    logger.warning("perplexity_pro_toggle_failed", error=str(exc))

        # Fallback for deep mode
        if is_deep:
            res_chain = mode_selectors.get("research_mode")
            if res_chain:
                r_loc, _ = await resolve_locator(page, res_chain)
                if r_loc:
                    try:
                        await r_loc.click(timeout=3000)
                        logger.info("perplexity_mode_selected", mode=mode, via="research_mode")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("perplexity_mode_click_failed", error=str(exc))

