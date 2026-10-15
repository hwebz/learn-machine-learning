from __future__ import annotations

from typing import Any

import structlog

from app.adapters.base import Source
from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class GeminiUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in gemini.google.com web UI via Playwright (DOM locators only)."""

    name = "gemini"

    async def _extract_sources(self, page: Any) -> list[Source]:
        """Ensure thought toggles or attribution containers are open before extraction."""
        try:
            toggles = page.locator(
                ".thoughts-container button[aria-expanded='false'], "
                ".thoughts-wrapper button[aria-expanded='false'], "
                "button.thoughts-header[aria-expanded='false'], "
                "button.thoughts-toggle[aria-expanded='false'], "
                "button[aria-label*='suy nghĩ' i][aria-expanded='false'], "
                "button[aria-label*='thought' i][aria-expanded='false']"
            )
            count = await toggles.count()
            for idx in range(count):
                toggle = toggles.nth(idx)
                if await toggle.is_visible(timeout=500):
                    await toggle.click(timeout=1000)
        except Exception:  # noqa: BLE001
            pass
        return await super()._extract_sources(page)

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Configure Gemini model (3.8 Flash, 3.1 Pro, 4 Argon, 3.5 Flash-Lite) and thinking effort (Cao, Trung bình, Thấp)."""
        from app.adapters.capabilities.gemini import GeminiCapabilitiesStrategy
        from app.adapters.capabilities.models import ProviderSelectionRequest

        strategy = GeminiCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                        thinking_level_id=parsed.get("thinking_level_id"),
                        mode_id=parsed.get("mode_id"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("gemini_selection_parse_failed", error=str(exc))

        # Fallback string mode
        is_deep = mode in {"deep", "deep_research", "research", "pro", "thinking"}
        config = ProviderSelectionRequest(
            model_id="gemini-3.1-pro" if is_deep else "gemini-3.8-flash",
            thinking_level_id="high" if is_deep else "medium",
            mode_id=mode,
        )
        await strategy.apply_selection(page, config)
