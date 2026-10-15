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
        """Switch Kimi model (Instant, K3, K2.8), thinking effort (Standard, High), and Deep Research."""
        from app.adapters.capabilities.kimi import KimiCapabilitiesStrategy
        from app.adapters.capabilities.models import ProviderSelectionRequest

        strategy = KimiCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                        thinking_level_id=parsed.get("thinking_level_id"),
                        mode_id=parsed.get("mode_id"),
                        deep_research=parsed.get("deep_research"),
                        deep_thinking=parsed.get("deep_thinking"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("kimi_selection_parse_failed", error=str(exc))

        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        config = ProviderSelectionRequest(
            model_id="k3" if is_deep else "instant",
            thinking_level_id="high" if is_deep else "standard",
            deep_research=is_deep,
        )
        await strategy.apply_selection(page, config)


