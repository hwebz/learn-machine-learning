from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class ClaudeUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in claude.ai web UI via Playwright (DOM locators only)."""

    name = "claude"

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Configure Claude model (Sonnet 5.5, Haiku 5.5, Opus 5.5) and thinking effort (Low, Medium, High, Extra, Max)."""
        from app.adapters.capabilities.claude import ClaudeCapabilitiesStrategy
        from app.adapters.capabilities.models import ProviderSelectionRequest

        strategy = ClaudeCapabilitiesStrategy()

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
                logger.warning("claude_selection_parse_failed", error=str(exc))

        # Fallback string mode
        is_deep = mode in {"deep", "deep_research", "research", "thinking", "pro"}
        config = ProviderSelectionRequest(
            model_id="claude-sonnet-5.5" if is_deep else "claude-haiku-5.5",
            thinking_level_id="high" if is_deep else "medium",
            mode_id=mode,
        )
        await strategy.apply_selection(page, config)


