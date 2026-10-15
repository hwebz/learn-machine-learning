from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.adapters.capabilities.mistral import MistralCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest

logger = structlog.get_logger(__name__)


class MistralUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.mistral.ai (Le Chat) web UI via Playwright (DOM locators only).

    Supported:
    1. No model selection available (available_models = []).
    2. Reasoning mode: Dropdown button nearby Send button with Fast and Think options.
    3. Deep Research toggle: Enabled by typing '@deep-research', selecting the first skill from
       the autocomplete popup, and continuing to enter the prompt.
    """

    name = "mistral"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._deep_research_active = False

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Switch Mistral reasoning mode (Fast vs Think) and configure Deep Research status."""
        strategy = MistralCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        thinking_level_id=parsed.get("thinking_level_id"),
                        deep_research=parsed.get("deep_research"),
                        deep_thinking=parsed.get("deep_thinking"),
                    )
                    self._deep_research_active = bool(config.deep_research)
                    logger.info("mistral_config_applied", thinking_level=config.thinking_level_id, deep_research=self._deep_research_active)
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("mistral_selection_parse_failed", error=str(exc))

        # Fallback string mode
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        self._deep_research_active = is_deep
        target_thinking = "think" if (is_deep or mode in {"think", "thinking"}) else "fast"
        config = ProviderSelectionRequest(
            thinking_level_id=target_thinking,
            deep_research=is_deep,
        )
        logger.info("mistral_fallback_mode_applied", target_thinking=target_thinking, deep_research=self._deep_research_active)
        await strategy.apply_selection(page, config)

    async def _enter_prompt(self, page: Any, input_locator: Any, prompt: str) -> None:
        """Enter prompt into Mistral Le Chat ProseMirror editor.

        If Deep Research toggle is active:
        1. Types '@deep-research' into the input
        2. Selects the first skill from the autocomplete popup
        3. Enters the user's prompt after the skill tag
        """
        try:
            await input_locator.click(timeout=5000)
        except Exception:  # noqa: BLE001
            pass

        if self._deep_research_active:
            logger.info("mistral_entering_prompt_with_deep_research", prompt_prefix=prompt[:30])
            # Step 1: Type @deep-research to trigger skill autocomplete
            await input_locator.type("@deep-research", delay=40)
            await asyncio.sleep(1.2)

            # Step 2: Select the first skill from the autocomplete popup
            first_skill = page.locator("[role='listbox'] [role='option'], [role='option'], button[role='option'], div:has-text('deep-research')").first
            if await first_skill.count() > 0 and await first_skill.is_visible(timeout=1500):
                await page.keyboard.press("Enter")
            else:
                await page.keyboard.press("Enter")
            await asyncio.sleep(0.8)

            # Step 3: Continue to enter the prompt with a leading space
            await input_locator.type(f" {prompt}", delay=15)
        else:
            logger.info("mistral_entering_standard_prompt", prompt_prefix=prompt[:30])
            try:
                await input_locator.fill(prompt, timeout=5000)
            except Exception:  # noqa: BLE001
                await input_locator.type(prompt, delay=15)
