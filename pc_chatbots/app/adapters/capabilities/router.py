from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import structlog
from openai import AsyncOpenAI

from app.adapters.capabilities.base import BaseProviderCapabilitiesStrategy
from app.adapters.capabilities.models import (
    OptionItem,
    ProviderLiveCapabilities,
    SupportedDataTypes,
    VoiceChatSupport,
)
from app.core.config import settings

logger = structlog.get_logger(__name__)

DEFAULT_ROUTER_MODELS = [
    ("Smartest", "Smartest (Auto Best Reasoning)", "Tự động chọn mô hình suy luận tốt nhất (DeepSeek-R1 / Qwen / Claude)"),
    ("Smarter", "Smarter (Balanced Synthesis)", "Mô hình cân bằng tốc độ và chất lượng suy luận cao"),
    ("Daily", "Daily (Fast & Efficient)", "Tốc độ phản hồi cực nhanh cho câu hỏi thường ngày"),
    ("cx/gpt-6.1-sol", "cx/gpt-6.1-sol", "Mô hình frontier tổng hợp đa chiều"),
    ("nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3-ultra-550b-a55b", "Mô hình 550B lý luận toán học và logic chuyên sâu"),
]


class RouterCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for 9Router local API provider."""

    def __init__(self, name: str = "9router") -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        models = [
            OptionItem(
                id=mid,
                label=lbl,
                description=desc,
                selected=(i == 0),
            )
            for i, (mid, lbl, desc) in enumerate(DEFAULT_ROUTER_MODELS)
        ]

        thinking_levels = [
            OptionItem(id="auto", label="Auto Thinking", description="Tự động suy luận theo yêu cầu câu hỏi", selected=True),
            OptionItem(id="high", label="Deep Thinking", description="Bật suy luận logic tối đa với reasoning tokens"),
            OptionItem(id="off", label="No Thinking", description="Trả lời trực tiếp không qua reasoning"),
        ]

        modes = [
            OptionItem(id="standard", label="Standard", description="Chế độ nghiên cứu tiêu chuẩn", selected=True),
            OptionItem(id="deep_research", label="Deep Research", description="Nghiên cứu đào sâu đa góc nhìn"),
        ]

        return ProviderLiveCapabilities(
            provider=self._name,
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=models,
            selected_model_id="Smartest",
            thinking_levels=thinking_levels,
            selected_thinking_level_id="auto",
            modes=modes,
            selected_mode_id="standard",
            deep_thinking=True,
            web_search=True,
            supported_data_types=SupportedDataTypes(
                text=True,
                image=True,
                file=True,
                audio=False,
                video=False,
                max_file_size_mb=50,
                supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".py", ".md", ".docx"],
            ),
            voice_chat=VoiceChatSupport(
                supported=True,
                mode="backend_stt",
                details="Hỗ trợ ghi âm microphone và chuyển thành văn bản bất đồng bộ qua backend.",
            ),
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect live models dynamically from 9Router local OpenAI-compatible endpoint."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        client = AsyncOpenAI(
            base_url=settings.router_base_url,
            api_key=settings.router_api_key or "local-token",
            timeout=3.0,
        )
        try:
            resp = await client.models.list()
            fetched_ids = [m.id for m in resp.data if m.id]
            if fetched_ids:
                # Merge dynamically fetched models
                existing_keys = {m.id: m for m in caps.available_models}
                merged_models: list[OptionItem] = []
                for fid in fetched_ids:
                    if fid in existing_keys:
                        merged_models.append(existing_keys[fid])
                    else:
                        merged_models.append(OptionItem(
                            id=fid,
                            label=fid,
                            description=f"Model {fid} from 9Router",
                            selected=False,
                        ))
                if merged_models:
                    if not any(m.selected for m in merged_models):
                        merged_models[0].selected = True
                    caps.available_models = merged_models
                    caps.selected_model_id = next(m.id for m in merged_models if m.selected)
                caps.is_live_dom = True
        except Exception as exc:
            logger.debug("9router_live_models_fetch_fallback", error=str(exc))
        finally:
            await client.close()
        return caps

    async def apply_selection(self, page: Any, config: Any) -> None:
        logger.info("router_apply_selection", provider=self._name, config=config)
