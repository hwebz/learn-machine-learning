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


class DeepSeekCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for DeepSeek (chat.deepseek.com) DOM option discovery,
    configuration, and defaults.

    Supports:
    - Model selection: DeepSeek-R1 (Reasoning / DeepThink ON), DeepSeek-V3 (Standard / DeepThink OFF).
    - Thinking Effort: DeepThink (Suy luận sâu), Tiêu chuẩn (Phản hồi nhanh).
    - File & Image uploads.
    - Voice STT microphone.
    - Clean manual combinations without a synthetic Mode dropdown.
    """

    @property
    def provider_name(self) -> str:
        return "deepseek"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for DeepSeek: only 2 toggles (DeepThink and Search)."""
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

        return ProviderLiveCapabilities(
            provider="deepseek",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=[],
            selected_model_id=None,
            thinking_levels=[],
            selected_thinking_level_id=None,
            modes=[],
            selected_mode_id=None,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
            deep_thinking=False,
            web_search=True,
        )

    async def _find_deepthink_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate the DeepThink toggle button with polling."""
        import time

        candidates = [
            ".ds-toggle-button:has-text('DeepThink')",
            "div.ds-toggle-button:has-text('DeepThink')",
            "button:has-text('DeepThink')",
            "[aria-label*='DeepThink' i]",
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

    async def _find_search_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate the Search toggle button with polling."""
        import time

        candidates = [
            ".ds-toggle-button:has-text('Search')",
            "div.ds-toggle-button:has-text('Search')",
            "button:has-text('Search')",
            "[aria-label*='Search' i]",
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
        """Inspect DeepSeek's live web DOM to extract DeepThink and Web Search toggle states."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        caps.available_models = []
        caps.selected_model_id = None
        caps.thinking_levels = []
        caps.selected_thinking_level_id = None
        caps.modes = []
        caps.selected_mode_id = None

        # 1. Inspect DeepThink toggle
        dt_btn = await self._find_deepthink_button(page)
        if dt_btn is not None:
            try:
                aria = await dt_btn.get_attribute("aria-pressed") or await dt_btn.get_attribute("aria-checked") or ""
                cls = await dt_btn.get_attribute("class") or ""
                is_dt_active = aria.lower() == "true" or "selected" in cls.lower() or "active" in cls.lower()
                caps.deep_thinking = is_dt_active
                logger.info("deepseek_inspect_deepthink_found", aria=aria, is_active=is_dt_active)
            except Exception as exc:
                logger.warning("deepseek_dom_inspect_deepthink_failed", error=str(exc))

        # 2. Inspect Search toggle
        search_btn = await self._find_search_button(page)
        if search_btn is not None:
            try:
                aria = await search_btn.get_attribute("aria-pressed") or await search_btn.get_attribute("aria-checked") or ""
                cls = await search_btn.get_attribute("class") or ""
                is_search_active = aria.lower() == "true" or "selected" in cls.lower() or "active" in cls.lower()
                caps.web_search = is_search_active
                logger.info("deepseek_inspect_search_found", aria=aria, is_active=is_search_active)
            except Exception as exc:
                logger.warning("deepseek_dom_inspect_search_failed", error=str(exc))

        caps.is_live_dom = True
        logger.info(
            "deepseek_dom_inspected_successfully",
            deep_thinking=caps.deep_thinking,
            web_search=caps.web_search,
        )
        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Apply DeepThink and Web Search toggles to DeepSeek's web interface."""
        # Determine DeepThink state
        want_deepthink = False
        if config.deep_thinking is not None:
            want_deepthink = bool(config.deep_thinking)
        else:
            target_model = (config.model_id or "").lower().strip()
            target_thinking = (config.thinking_level_id or "").lower().strip()
            mode_val = (config.mode_id or "").lower().strip()
            if "r1" in target_model or target_thinking in {"deepthink", "thinking", "high", "deep"} or mode_val in {"deep", "thinking"}:
                want_deepthink = True

        want_web_search = config.web_search

        logger.info(
            "deepseek_applying_selection",
            want_deepthink=want_deepthink,
            want_web_search=want_web_search,
        )

        # 1. Apply DeepThink toggle
        try:
            dt_btn = await self._find_deepthink_button(page)
            if dt_btn is not None:
                aria = await dt_btn.get_attribute("aria-pressed") or await dt_btn.get_attribute("aria-checked") or ""
                cls = await dt_btn.get_attribute("class") or ""
                is_dt_active = aria.lower() == "true" or "selected" in cls.lower() or "active" in cls.lower()

                if want_deepthink != is_dt_active:
                    await dt_btn.click(timeout=3000)
                    await asyncio.sleep(0.8)
                    logger.info("deepseek_deepthink_toggled", want_deepthink=want_deepthink)
                else:
                    logger.info("deepseek_deepthink_already_matched", is_active=is_dt_active)
        except Exception as exc:
            logger.warning("deepseek_apply_deepthink_failed", error=str(exc))

        # 2. Apply Web Search toggle (if explicitly specified)
        if want_web_search is not None:
            try:
                search_btn = await self._find_search_button(page)
                if search_btn is not None:
                    aria = await search_btn.get_attribute("aria-pressed") or await search_btn.get_attribute("aria-checked") or ""
                    cls = await search_btn.get_attribute("class") or ""
                    is_search_active = aria.lower() == "true" or "selected" in cls.lower() or "active" in cls.lower()

                    if want_web_search != is_search_active:
                        await search_btn.click(timeout=3000)
                        await asyncio.sleep(0.8)
                        logger.info("deepseek_search_toggled", want_web_search=want_web_search)
                    else:
                        logger.info("deepseek_search_already_matched", is_active=is_search_active)
            except Exception as exc:
                logger.warning("deepseek_apply_search_failed", error=str(exc))
