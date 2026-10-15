from __future__ import annotations

import asyncio
import re
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


class PerplexityCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Perplexity AI (perplexity.ai) DOM option discovery and capabilities.

    Free accounts:
    - Cannot choose model (all synced models are disabled, default is 'Auto').
    - Thinking toggle is off by default and disabled.
    - No reasoning effort dropdown or mode selector.
    - Web search is always active.
    """

    @property
    def provider_name(self) -> str:
        return "perplexity"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Perplexity AI."""
        fallback_models = [
            OptionItem(
                id="auto",
                label="Auto (Tự động)",
                description="Mô hình mặc định của Perplexity (Tối ưu tự động theo ngữ cảnh)",
                selected=True,
                disabled=False,
                badge="Auto",
            ),
            OptionItem(
                id="gpt-6-1-sol",
                label="GPT-6.1 Sol",
                description="Mô hình GPT-6.1 Sol trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Pro",
            ),
            OptionItem(
                id="gpt-6-astra",
                label="GPT-6 Astra",
                description="Mô hình GPT-6 Astra trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Max",
            ),
            OptionItem(
                id="gemini-4-argon",
                label="Gemini 4 Argon",
                description="Mô hình Gemini 4 Argon trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="New",
            ),
            OptionItem(
                id="gemini-3-8-flash",
                label="Gemini 3.8 Flash",
                description="Mô hình Gemini 3.8 Flash trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Pro",
            ),
            OptionItem(
                id="claude-sonnet-5-5",
                label="Claude Sonnet 5.5",
                description="Mô hình Claude Sonnet 5.5 trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Pro",
            ),
            OptionItem(
                id="claude-opus-5-5",
                label="Claude Opus 5.5",
                description="Mô hình Claude Opus 5.5 trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Max",
            ),
            OptionItem(
                id="claude-fable-5-1",
                label="Claude Fable 5.1",
                description="Mô hình Claude Fable 5.1 trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Max",
            ),
            OptionItem(
                id="kimi-k3",
                label="Kimi K3",
                description="Mô hình Kimi K3 trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Pro",
            ),
            OptionItem(
                id="glm-5-3",
                label="GLM 5.3",
                description="Mô hình GLM 5.3 trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Pro",
            ),
            OptionItem(
                id="grok-4-7",
                label="Grok 4.7",
                description="Mô hình Grok 4.7 trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Pro",
            ),
            OptionItem(
                id="nemotron-3-ultra",
                label="Nemotron 3 Ultra",
                description="Mô hình Nemotron 3 Ultra trên Perplexity (Yêu cầu tài khoản Pro)",
                selected=False,
                disabled=True,
                badge="Pro",
            ),
        ]

        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=25,
            supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".docx", ".xlsx"],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và nhận diện văn bản qua backend.",
        )

        return ProviderLiveCapabilities(
            provider="perplexity",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=fallback_models,
            selected_model_id="auto",
            thinking_levels=[],
            selected_thinking_level_id=None,
            modes=[],
            selected_mode_id=None,
            deep_thinking=False,
            web_search=True,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect the live perplexity.ai DOM to collect models and confirm capabilities."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        # 1. Dismiss cookies/announcements if present
        try:
            got_it = page.locator("button:has-text('Got it'), button:has-text('Decline optional')").first
            if await got_it.count() > 0 and await got_it.is_visible(timeout=500):
                await got_it.click(timeout=1000)
                await asyncio.sleep(0.3)
        except Exception:
            pass

        # 2. Discover Models via Model button
        model_btn = page.locator(
            "button[aria-label='Model'], button:has-text('Model'), [data-testid*='model' i]"
        ).first

        parsed_models: list[OptionItem] = [
            OptionItem(
                id="auto",
                label="Auto (Tự động)",
                description="Mô hình mặc định của Perplexity (Tối ưu tự động theo ngữ cảnh)",
                selected=True,
                disabled=False,
                badge="Auto",
            )
        ]

        try:
            if await model_btn.count() > 0 and await model_btn.is_visible(timeout=2000):
                await model_btn.click(timeout=2000)
                await asyncio.sleep(0.8)

                raw_items = await page.locator(
                    "[role='menuitem'], [data-radix-collection-item], div[class*='hover:bg-subtle']"
                ).evaluate_all("""
                    elements => elements.map(el => el.innerText.trim()).filter(Boolean)
                """)

                seen_ids = {"auto"}
                for raw in raw_items:
                    lines = [l.strip() for l in raw.split("\n") if l.strip()]
                    if not lines:
                        continue
                    name = lines[0]
                    if any(skip in name.lower() for skip in ["access the top", "decline", "got it", "cookie", "choose", "cancel"]):
                        continue
                    badge = lines[1] if len(lines) > 1 else "Pro"
                    clean_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                    if clean_id in seen_ids:
                        continue
                    seen_ids.add(clean_id)

                    parsed_models.append(
                        OptionItem(
                            id=clean_id,
                            label=name,
                            description=f"Mô hình {name} trên Perplexity (Yêu cầu tài khoản Pro)",
                            selected=False,
                            disabled=True,  # Disable all synced models for free account
                            badge=badge,
                        )
                    )

                await page.keyboard.press("Escape")
                await asyncio.sleep(0.2)
                logger.info("perplexity_models_synced", count=len(parsed_models))
        except Exception as exc:
            logger.warning("perplexity_model_scan_failed", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

        if len(parsed_models) > 1:
            caps.available_models = parsed_models
            caps.is_live_dom = True

        # Model: default select Auto
        caps.selected_model_id = "auto"

        # Thinking: disabled & off by default
        caps.deep_thinking = False
        caps.thinking_levels = []
        caps.selected_thinking_level_id = None

        # Mode: not selectable on free account
        caps.modes = []
        caps.selected_mode_id = None

        caps.web_search = True
        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Apply selection for Perplexity. Free accounts use default Auto and no thinking toggle."""
        logger.info("perplexity_apply_selection_noop_for_free_account")
