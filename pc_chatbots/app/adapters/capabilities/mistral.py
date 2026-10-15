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


class MistralCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Mistral Le Chat (chat.mistral.ai).

    Requirements:
    1. No model selection available (available_models = []).
    2. Reasoning mode: Dropdown button nearby Send button with Fast ("Get answers fast") and Think ("Handle complex tasks").
    3. Deep Research toggle: Supported, enabled by typing @deep-research and selecting the skill.
    """

    @property
    def provider_name(self) -> str:
        return "mistral"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Mistral Le Chat."""
        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=50,
            supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".docx", ".xlsx", ".py", ".md"],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và chuyển thành văn bản thời gian thực qua backend.",
        )

        thinking_levels = [
            OptionItem(
                id="fast",
                label="Fast (Nhanh)",
                description="Get answers fast — Phản hồi nhanh cho câu hỏi thường ngày",
                selected=True,
                badge="Fast",
            ),
            OptionItem(
                id="think",
                label="Think (Suy luận)",
                description="Handle complex tasks — Suy luận sâu cho tác vụ phức tạp",
                selected=False,
                badge="Think",
            ),
        ]

        return ProviderLiveCapabilities(
            provider="mistral",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=[],
            selected_model_id=None,
            thinking_levels=thinking_levels,
            selected_thinking_level_id="fast",
            modes=[],
            selected_mode_id=None,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
            deep_thinking=False,
            web_search=True,
            deep_research=False,
        )

    async def _find_reasoning_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate the reasoning mode button (Fast / Think) nearby the Send button."""
        import time

        candidates = [
            "button:has-text('Fast')",
            "button:has-text('Think')",
            "button[aria-label='Choose model']",
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
        """Inspect live Mistral DOM to detect current reasoning mode (Fast vs Think)."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        try:
            btn = await self._find_reasoning_button(page, timeout_s=4.0)
            if btn is not None:
                txt = (await btn.inner_text()).strip()
                logger.info("mistral_dom_reasoning_btn_found", text=txt)
                is_think = "think" in txt.lower()
                selected_id = "think" if is_think else "fast"
                caps.selected_thinking_level_id = selected_id
                for item in caps.thinking_levels:
                    item.selected = (item.id == selected_id)
                caps.is_live_dom = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("mistral_inspect_dom_failed", error=str(exc))

        return caps

    async def apply_selection(self, page: Any, config: Any) -> None:
        """Apply reasoning mode selection (Fast vs Think) in live DOM."""
        if not isinstance(config, ProviderSelectionRequest):
            if isinstance(config, dict):
                config = ProviderSelectionRequest.model_validate(config)
            else:
                config = ProviderSelectionRequest()

        target_level = (config.thinking_level_id or "").lower()
        if not target_level:
            if config.deep_thinking:
                target_level = "think"
            else:
                target_level = "fast"

        btn = await self._find_reasoning_button(page, timeout_s=5.0)
        if btn is None:
            logger.warning("mistral_reasoning_button_not_found")
            return

        try:
            curr_text = (await btn.inner_text()).strip().lower()
            if target_level == "think" and "think" in curr_text:
                logger.info("mistral_already_in_think_mode")
                return
            if target_level == "fast" and "fast" in curr_text:
                logger.info("mistral_already_in_fast_mode")
                return

            logger.info("mistral_switching_reasoning_mode", target=target_level, current=curr_text)
            await btn.click(timeout=4000)
            await asyncio.sleep(0.6)

            menu_sel = "[role='menuitem']:has-text('Think')" if target_level == "think" else "[role='menuitem']:has-text('Fast')"
            menu_item = page.locator(menu_sel).first
            if await menu_item.is_visible(timeout=3000):
                await menu_item.click()
                logger.info("mistral_reasoning_mode_clicked", target=target_level)
                await asyncio.sleep(0.5)
            else:
                logger.warning("mistral_reasoning_menuitem_not_visible", target=target_level)
                await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001
            logger.warning("mistral_apply_selection_failed", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
