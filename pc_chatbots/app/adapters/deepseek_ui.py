from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class DeepSeekUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.deepseek.com web UI via Playwright (DOM locators only)."""

    name = "deepseek"

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Configure DeepSeek model (DeepSeek-R1 vs DeepSeek-V3) and thinking effort (DeepThink vs Tiêu chuẩn)."""
        from app.adapters.capabilities.deepseek import DeepSeekCapabilitiesStrategy
        from app.adapters.capabilities.models import ProviderSelectionRequest

        strategy = DeepSeekCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                        thinking_level_id=parsed.get("thinking_level_id"),
                        mode_id=parsed.get("mode_id"),
                        deep_thinking=parsed.get("deep_thinking"),
                        web_search=parsed.get("web_search"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("deepseek_selection_parse_failed", error=str(exc))

        # Fallback string mode
        is_deep = mode in {"deep", "deep_research", "research", "thinking", "r1"}
        config = ProviderSelectionRequest(
            model_id="",
            thinking_level_id="",
            mode_id=mode,
            deep_thinking=is_deep,
            web_search=True,
        )
        await strategy.apply_selection(page, config)


