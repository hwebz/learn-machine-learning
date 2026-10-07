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
        """Best-effort mode switch (pro/research). Failure is non-fatal."""
        if mode not in {"deep", "research", "pro"}:
            return
        mode_selectors = self._cfg.get("mode_selectors") or {}
        for key in ("research_mode", "pro_toggle"):
            chain = mode_selectors.get(key)
            if not chain:
                continue
            locator, _ = await resolve_locator(page, chain)
            if locator is None:
                continue
            try:
                await locator.click(timeout=3000)
                logger.info("perplexity_mode_selected", mode=mode, via=key)
                return
            except Exception as exc:  # noqa: BLE001 — mode switch is optional
                logger.warning("perplexity_mode_click_failed", via=key, error=str(exc))
        logger.info("perplexity_mode_skipped", mode=mode)
