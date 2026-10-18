from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import httpx
import structlog

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
    ("nvidia/nemotron-3-ultra-550b-a55b", "Nemotron 3 Ultra 550B", "Mô hình 550B lý luận toán học và logic chuyên sâu"),
]


class RouterCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for 9Router local API provider (Pure API, no browser / DOM)."""

    is_api_only: bool = True

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
                badge=mid if mid in ("Smartest", "Smarter", "Daily") else "Reasoning",
                metadata={"reasoning": True, "thinking_format": "openai"},
            )
            for i, (mid, lbl, desc) in enumerate(DEFAULT_ROUTER_MODELS)
        ]

        thinking_levels = [
            OptionItem(
                id="auto",
                label="Auto Thinking",
                description="Tự động suy luận theo yêu cầu câu hỏi (nếu model hỗ trợ reasoning)",
                selected=True,
                badge="Tự động",
            ),
            OptionItem(
                id="high",
                label="Deep Thinking (High)",
                description="Bật suy luận logic tối đa với reasoning tokens",
                selected=False,
                badge="Chuyên sâu",
            ),
            OptionItem(
                id="medium",
                label="Balanced Thinking",
                description="Suy luận mức trung bình cân bằng tốc độ",
                selected=False,
            ),
            OptionItem(
                id="off",
                label="No Thinking (Tắt)",
                description="Tắt chế độ suy luận, trả lời trực tiếp",
                selected=False,
            ),
        ]

        modes = [
            OptionItem(
                id="standard",
                label="Standard",
                description="Chế độ nghiên cứu tiêu chuẩn qua 9Router",
                selected=True,
            ),
            OptionItem(
                id="deep_research",
                label="Deep Research",
                description="Nghiên cứu đào sâu đa bước với 9Router",
                selected=False,
                badge="Pro",
            ),
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

    async def inspect_dom(self, page: Any = None) -> ProviderLiveCapabilities:
        """Inspect live models and capabilities dynamically via 9Router local API (no DOM needed)."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        base_url = settings.router_base_url.rstrip("/")
        url = f"{base_url}/models"
        headers = {
            "Authorization": f"Bearer {settings.router_api_key or 'local-token'}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                res = await client.get(url, headers=headers)

            if res.status_code == 200:
                payload = res.json()
                raw_models: list[dict[str, Any]] = payload.get("data", []) if isinstance(payload, dict) else []

                if raw_models:
                    parsed_models: list[OptionItem] = []
                    default_map = {mid: (lbl, desc) for mid, lbl, desc in DEFAULT_ROUTER_MODELS}

                    has_any_reasoning = False
                    has_any_vision = False
                    has_any_search = False

                    for item in raw_models:
                        if not isinstance(item, dict):
                            continue
                        mid = item.get("id")
                        if not mid:
                            continue

                        model_caps = item.get("capabilities") or {}
                        owned_by = item.get("owned_by") or ""
                        reasoning = bool(model_caps.get("reasoning", False))
                        if reasoning:
                            has_any_reasoning = True
                        thinking_format = model_caps.get("thinkingFormat")
                        thinking_can_disable = bool(model_caps.get("thinkingCanDisable", True))
                        thinking_effort_supported = bool(model_caps.get("thinkingEffortSupported", False))
                        vision = bool(model_caps.get("vision", False))
                        if vision:
                            has_any_vision = True
                        pdf = bool(model_caps.get("pdf", False))
                        tools = bool(model_caps.get("tools", False))
                        search = bool(model_caps.get("search", False))
                        if search:
                            has_any_search = True

                        context_window = model_caps.get("contextWindow") or item.get("context_length")
                        max_output = model_caps.get("maxOutput") or item.get("max_completion_tokens")

                        # Determine badge
                        if mid in ("Smartest", "Smarter", "Daily"):
                            badge = mid
                        elif reasoning:
                            badge = "🧠 Reasoning"
                        elif vision:
                            badge = "👁️ Vision"
                        elif owned_by:
                            badge = owned_by.capitalize()
                        else:
                            badge = None

                        # Determine label & description
                        if mid in default_map:
                            label, base_desc = default_map[mid]
                        else:
                            label = mid
                            base_desc = f"Mô hình {mid} từ 9Router"

                        desc_parts: list[str] = [base_desc]
                        specs: list[str] = []
                        if reasoning:
                            fmt_str = f"format: {thinking_format}" if thinking_format else "native"
                            specs.append(f"Lý luận sâu ({fmt_str})")
                        if context_window:
                            specs.append(f"{context_window // 1000}k context" if context_window >= 1000 else f"{context_window} tokens")
                        if vision:
                            specs.append("Vision")
                        if search:
                            specs.append("Web Search")

                        if specs:
                            desc_parts.append(" • ".join(specs))

                        full_description = " | ".join(desc_parts)

                        metadata: dict[str, Any] = {
                            "owned_by": owned_by,
                            "reasoning": reasoning,
                            "thinking_format": thinking_format,
                            "thinking_can_disable": thinking_can_disable,
                            "thinking_effort_supported": thinking_effort_supported,
                            "context_window": context_window,
                            "max_output": max_output,
                            "vision": vision,
                            "pdf": pdf,
                            "tools": tools,
                            "search": search,
                        }

                        parsed_models.append(OptionItem(
                            id=mid,
                            label=label,
                            description=full_description,
                            selected=False,
                            badge=badge,
                            metadata=metadata,
                        ))

                    if parsed_models:
                        # Prioritize lead model from settings (e.g. Smartest) or first model
                        target_lead = settings.router_model_lead or "Smartest"
                        lead_found = False
                        for m in parsed_models:
                            if m.id == target_lead:
                                m.selected = True
                                lead_found = True
                                break
                        if not lead_found and parsed_models:
                            parsed_models[0].selected = True

                        caps.available_models = parsed_models
                        caps.selected_model_id = next(m.id for m in parsed_models if m.selected)
                        caps.deep_thinking = has_any_reasoning
                        caps.web_search = has_any_search
                        caps.supported_data_types.image = has_any_vision
                        caps.is_live_dom = True
                        caps.last_error = None
                        logger.info("9router_live_models_synced", count=len(parsed_models), base_url=base_url)
            else:
                caps.last_error = f"9Router API trả về HTTP {res.status_code}: {res.text[:100]}"
                logger.warning("9router_api_error_response", status_code=res.status_code, body=res.text[:100])
        except Exception as exc:
            caps.last_error = f"Không thể kết nối đến 9Router tại {base_url} ({type(exc).__name__}: {exc})"
            logger.debug("9router_live_models_fetch_fallback", error=str(exc))

        return caps

    async def apply_selection(self, page: Any, config: Any) -> None:
        logger.info("router_apply_selection", provider=self._name, config=config)
