from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class QwenUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.qwen.ai web UI via Playwright (DOM locators only)."""

    name = "qwen"

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Configure Qwen model (Qwen3.8-Max, Qwen3.7-Plus, Qwen3.8-Omni-Flash) and thinking effort (Auto, Thinking, Fast)."""
        from app.adapters.capabilities.qwen import QwenCapabilitiesStrategy
        from app.adapters.capabilities.models import ProviderSelectionRequest

        strategy = QwenCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                        thinking_level_id=parsed.get("thinking_level_id"),
                        mode_id=parsed.get("mode_id"),
                        deep_research=parsed.get("deep_research", False),
                        web_search=parsed.get("web_search", True),
                        research_mode=parsed.get("research_mode", "normal"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("qwen_selection_parse_failed", error=str(exc))

        # Fallback string mode
        is_deep = mode in {"deep", "deep_research", "research", "thinking"}
        config = ProviderSelectionRequest(
            model_id="qwen-3.8-max" if is_deep else "qwen-3.7-plus",
            thinking_level_id="auto" if is_deep else "auto",
            mode_id=mode,
            deep_research=is_deep,
            web_search=True,
            research_mode="normal",
        )
        await strategy.apply_selection(page, config)

