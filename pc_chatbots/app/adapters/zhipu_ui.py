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
        """Switch Zhipu model via capabilities strategy (top-left dropdown)."""
        from app.adapters.capabilities.models import ProviderSelectionRequest
        from app.adapters.capabilities.zhipu import ZhipuCapabilitiesStrategy

        strategy = ZhipuCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("zhipu_selection_parse_failed", error=str(exc))

        # Handle direct model IDs or legacy mode strings
        target_model = "glm-5.3-flash"
        if mode:
            lower = mode.strip().lower()
            if "5.3" in lower and "flash" in lower:
                target_model = "glm-5.3-flash"
            elif "5.3" in lower:
                target_model = "glm-5.3"
            elif "5.2" in lower:
                target_model = "glm-5.2"
            elif lower in {"deep", "pro", "research", "deep_research", "flagship"}:
                target_model = "glm-5.3"
            elif lower in {"flash", "standard", "fast"}:
                target_model = "glm-5.3-flash"
            elif "plus" in lower:
                target_model = "glm-4-plus"
            elif "air" in lower:
                target_model = "glm-4-air"
            elif "zero" in lower:
                target_model = "glm-zero"
            elif lower.startswith("glm-"):
                target_model = lower

        config = ProviderSelectionRequest(model_id=target_model)
        await strategy.apply_selection(page, config)


