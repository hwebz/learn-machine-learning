from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
import structlog

from app.adapters.capabilities.base import BaseProviderCapabilitiesStrategy
from app.adapters.capabilities.models import (
    OptionItem,
    ProviderLiveCapabilities,
    ProviderSelectionRequest,
    SupportedDataTypes,
    VoiceChatSupport,
)

logger = structlog.get_logger(__name__)


class MetaCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Meta AI (meta.ai) DOM option discovery, configuration, and defaults.

    Key characteristics per requirements:
    1. No AI model dropdown on Meta AI.
    2. Thinking toggle: button that clicks to show a dropdown with 2 options:
       'Thinking' (on, deep_thinking=True) or 'Instant' (off, deep_thinking=False).
    """

    @property
    def provider_name(self) -> str:
        return "meta"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Meta AI: no model dropdown, 2-option Thinking toggle."""
        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=50,
            supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".py", ".md", ".docx"],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và chuyển thành văn bản thời gian thực qua backend.",
        )

        return ProviderLiveCapabilities(
            provider="meta",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=[],
            selected_model_id=None,
            thinking_levels=[
                OptionItem(id="thinking", label="Thinking (Suy luận chuyên sâu)", selected=False),
                OptionItem(id="instant", label="Instant (Phản hồi tức thì)", selected=True),
            ],
            selected_thinking_level_id="instant",
            modes=[],
            selected_mode_id=None,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
            deep_thinking=False,
            web_search=True,
            deep_research=False,
        )

    async def _find_mode_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate Meta AI composer mode button with polling."""
        import time

        candidates = [
            "button[data-testid='composer-mode-dropdown-button']",
            "button[data-testid*='composer-mode']",
            "button:has-text('Thinking')",
            "button:has-text('Instant')",
            "[aria-label*='mode' i]",
            "[data-testid='chat-main-conversation'] ~ div button:has-text('Thinking')",
            "[data-testid='chat-main-conversation'] ~ div button:has-text('Instant')",
        ]
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            for sel in candidates:
                try:
                    loc = page.locator(sel)
                    cnt = await loc.count()
                    for i in range(cnt):
                        b = loc.nth(i)
                        if await b.is_visible(timeout=200):
                            return b
                except Exception:
                    continue
            await asyncio.sleep(0.3)
        return None

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect live DOM on meta.ai:

        Check if current composer mode is 'Thinking' vs 'Instant'.
        """
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        caps.is_live_dom = True

        try:
            mode_btn = await self._find_mode_button(page, timeout_s=4.0)
            if mode_btn is not None:
                text = (await mode_btn.inner_text()).strip().lower()
                aria = (await mode_btn.get_attribute("aria-label") or "").strip().lower()
                combined = f"{text} {aria}"
                if "thinking" in combined:
                    caps.deep_thinking = True
                    caps.selected_thinking_level_id = "thinking"
                elif "instant" in combined:
                    caps.deep_thinking = False
                    caps.selected_thinking_level_id = "instant"
        except Exception as exc:  # noqa: BLE001
            logger.warning("meta_inspect_dom_failed", error=str(exc))

        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Switch Meta AI composer mode between 'Thinking' (on) and 'Instant' (off)."""
        is_thinking = None
        if config.deep_thinking is not None:
            is_thinking = bool(config.deep_thinking)
        elif config.thinking_level_id is not None:
            is_thinking = config.thinking_level_id.lower() == "thinking"

        if is_thinking is None:
            return

        target_label = "Thinking" if is_thinking else "Instant"

        btn = await self._find_mode_button(page, timeout_s=5.0)
        if btn is None:
            logger.info("meta_mode_button_not_found")
            return

        try:
            curr_text = (await btn.inner_text()).strip().lower()
            curr_aria = (await btn.get_attribute("aria-label") or "").strip().lower()
            combined = f"{curr_text} {curr_aria}"

            if is_thinking and "thinking" in combined:
                logger.info("meta_mode_already_thinking")
                return
            if not is_thinking and "instant" in combined:
                logger.info("meta_mode_already_instant")
                return

            await btn.click(timeout=4000)
            await asyncio.sleep(0.5)

            # Look for dropdown item matching target_label ("Thinking" or "Instant")
            item_selectors = [
                f"[role='menuitem']:has-text('{target_label}')",
                f"[role='option']:has-text('{target_label}')",
                f"button:has-text('{target_label}')",
                f"div:has-text('{target_label}')",
                f"[data-testid*='{target_label.lower()}']",
            ]
            for sel in item_selectors:
                try:
                    item_loc = page.locator(sel)
                    cnt = await item_loc.count()
                    for i in range(cnt):
                        item = item_loc.nth(i)
                        if await item.is_visible(timeout=300):
                            await item.click(timeout=3000)
                            logger.info("meta_mode_selected", target=target_label)
                            await asyncio.sleep(0.5)
                            return
                except Exception:
                    continue

            # Dismiss dropdown if option wasn't found
            await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001
            logger.warning("meta_mode_switch_failed", error=str(exc))
