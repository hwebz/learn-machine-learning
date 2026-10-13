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


class ChatGPTCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for ChatGPT (chatgpt.com) DOM option discovery, configuration, and defaults.
    
    Optimized for Free account tier with Auto model & reasoning, Standard/Thinking modes,
    and Web Search / Create Image / Deep Research tools.
    """

    @property
    def provider_name(self) -> str:
        return "chatgpt"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for ChatGPT (Free Account defaults)."""
        # Free account has no model switcher; fixed to Auto
        models = [
            OptionItem(
                id="auto",
                label="Auto (Tự động)",
                description="Tự động lựa chọn mô hình phù hợp theo loại tài khoản (Free Account)",
                selected=True,
                badge="Free",
                metadata={"multimodal": True, "reasoning": True},
            ),
        ]

        # Free account has no reasoning effort picker (Low/Medium/High); fixed to Auto
        thinking_levels = [
            OptionItem(
                id="auto",
                label="Auto (Tự động)",
                description="Tự động cân bằng mức suy luận trên tài khoản Free",
                selected=True,
            ),
        ]

        # Modes: Standard (Default) or Thinking
        modes = [
            OptionItem(
                id="standard",
                label="Tiêu chuẩn (Standard)",
                description="Chế độ trò chuyện tiêu chuẩn nhanh chóng",
                selected=True,
            ),
            OptionItem(
                id="thinking",
                label="Suy luận (Thinking)",
                description="Kích hoạt nút Think để phân tích và trả lời chi tiết",
                selected=False,
                badge="Think",
            ),
        ]

        # Tools: Web Search, Create Image, Deep Research (plus menu)
        tools = [
            OptionItem(
                id="none",
                label="Không sử dụng (Mặc định)",
                description="Trò chuyện tiêu chuẩn không kèm công cụ bổ trợ",
                selected=True,
            ),
            OptionItem(
                id="web_search",
                label="Web search (Tìm kiếm web)",
                description="Duyệt web trực tiếp để cập nhật tin tức và thông tin thời gian thực",
                selected=False,
                badge="Search",
            ),
            OptionItem(
                id="create_image",
                label="Create image (Tạo ảnh)",
                description="Trực quan hóa và tạo ảnh từ mô tả",
                selected=False,
                badge="DALL-E",
            ),
            OptionItem(
                id="deep_research",
                label="Deep research (Nghiên cứu sâu)",
                description="Nghiên cứu chuyên sâu tự động đa nguồn với báo cáo chi tiết",
                selected=False,
                badge="Research",
            ),
        ]

        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=50,
            supported_mime_types=[
                "image/*",
                ".pdf",
                ".txt",
                ".csv",
                ".json",
                ".py",
                ".md",
                ".docx",
                ".xlsx",
            ],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và chuyển thành văn bản bất đồng bộ qua backend STT.",
        )

        return ProviderLiveCapabilities(
            provider="chatgpt",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=models,
            selected_model_id="auto",
            thinking_levels=thinking_levels,
            selected_thinking_level_id="auto",
            modes=modes,
            selected_mode_id="standard",
            tools=tools,
            selected_tool_id="none",
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Asynchronously query the live ChatGPT DOM to collect models, thinking, modes, and tools."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        try:
            # 1. Check if blocked by login wall or CAPTCHA
            from app.adapters.selectors_loader import load_selectors
            from app.browser.waits import detect_blocking_state

            selectors = load_selectors()
            blocking = await detect_blocking_state(page, selectors.get("blocking", {}))
            if blocking is not None:
                caps.last_error = f"Trình duyệt yêu cầu xác thực người dùng ({blocking.kind}): {blocking.detail}"
                caps.is_live_dom = False
                return caps

            # 2. Model Switcher Detection (Check if account has model switcher dropdown)
            model_triggers = [
                "button[data-testid='model-switcher-dropdown']",
                "button[id*='model-switcher']",
                "[data-testid='model-switcher'] button",
                "button[aria-haspopup='menu']:has-text('GPT')",
            ]

            has_model_switcher = False
            for sel in model_triggers:
                loc = page.locator(sel)
                if await loc.count() > 0 and await loc.first.is_visible(timeout=800):
                    has_model_switcher = True
                    break

            # If no model switcher (Free account), lock to Auto
            if not has_model_switcher:
                caps.available_models = [
                    OptionItem(
                        id="auto",
                        label="Auto (Tự động)",
                        description="Tự động lựa chọn mô hình phù hợp theo loại tài khoản (Free Account)",
                        selected=True,
                        badge="Free",
                    )
                ]
                caps.selected_model_id = "auto"
                caps.account_type = "free"
                logger.info("chatgpt_account_detected_free_no_model_picker")

            # 3. Reasoning Picker: For free account, no effort picker; lock to Auto
            caps.thinking_levels = [
                OptionItem(
                    id="auto",
                    label="Auto (Tự động)",
                    description="Tự động cân bằng mức suy luận trên tài khoản Free",
                    selected=True,
                )
            ]
            caps.selected_thinking_level_id = "auto"

            # 4. Mode: Check if Think pill is currently active in the composer
            think_loc = page.locator("button.__composer-pill:has-text('Think'), button:has-text('Think')")
            if await think_loc.count() > 0:
                is_pressed = (await self.safe_attr(think_loc.first, "aria-pressed")) == "true"
                caps.selected_mode_id = "thinking" if is_pressed else "standard"
                for m in caps.modes:
                    m.selected = (m.id == caps.selected_mode_id)

            # 5. Tools Detection (Plus menu)
            plus_btn = page.locator(
                "button[data-testid='attach-button'], button[aria-label*='Attach' i], button[aria-haspopup='menu']"
            )
            has_plus = await plus_btn.count() > 0
            if has_plus:
                for t in caps.tools:
                    if t.id != "none":
                        t.badge = "Live"

            # 6. File / Image Upload Capabilities
            attach_loc = page.locator(
                "button[data-testid='attach-button'], button[aria-label*='Attach' i], button[aria-label*='Đính kèm' i], input[type='file']"
            )
            has_attach = await attach_loc.count() > 0
            is_disabled = False
            if has_attach:
                is_disabled = (await self.safe_attr(attach_loc.first, "disabled")) is not None
                file_input = page.locator("input[type='file']")
                if await file_input.count() > 0:
                    accept_attr = await self.safe_attr(file_input.first, "accept")
                    if accept_attr:
                        caps.supported_data_types.supported_mime_types = [s.strip() for s in accept_attr.split(",") if s.strip()]

            caps.supported_data_types.text = True
            caps.supported_data_types.image = has_attach and not is_disabled
            caps.supported_data_types.file = has_attach and not is_disabled

            # 7. Voice Chat Button in DOM
            speech_loc = page.locator(
                "button[data-testid='composer-speech-button'], button[aria-label*='Dictate' i], button[aria-label*='voice' i], button[data-testid='voice-mode-button']"
            )
            has_speech = await speech_loc.count() > 0
            caps.voice_chat.supported = True
            if has_speech:
                caps.voice_chat.details = "ChatGPT web UI có nút Dictate; hệ thống hỗ trợ micro thu âm bất đồng bộ chuyển văn bản."

            caps.is_live_dom = True
            caps.last_error = None
            logger.info(
                "chatgpt_dom_inspection_success",
                account_type=caps.account_type,
                mode=caps.selected_mode_id,
                can_upload=caps.supported_data_types.image,
            )
        except Exception as exc:
            logger.warning("chatgpt_dom_inspection_failed", error=str(exc))
            caps.last_error = f"Lỗi khi quét DOM: {type(exc).__name__}: {exc}"
            caps.is_live_dom = False

        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Actuate DOM selectors to apply chosen tool, mode, and options."""
        # 1. Tools Selection via Plus Menu
        # Supported tools: web_search, create_image, deep_research
        if config.tool_id and config.tool_id != "none":
            tool_label_map = {
                "web_search": "Web search",
                "create_image": "Create image",
                "deep_research": "Deep research",
            }
            target_label = tool_label_map.get(config.tool_id)
            if target_label:
                try:
                    plus_loc = page.locator(
                        "button[data-testid='attach-button'], button[aria-label*='Attach' i], button[aria-haspopup='menu']"
                    ).first
                    if await plus_loc.count() > 0:
                        await plus_loc.click(timeout=2500)
                        await asyncio.sleep(0.35)
                        item_loc = page.locator(
                            f"[role='menuitem']:has-text('{target_label}'), "
                            f"button:has-text('{target_label}'), "
                            f"div:has-text('{target_label}')"
                        ).first
                        if await item_loc.count() > 0 and await item_loc.is_visible(timeout=1000):
                            await item_loc.click(timeout=2500)
                            logger.info("chatgpt_tool_applied", tool=config.tool_id, label=target_label)
                        else:
                            await page.keyboard.press("Escape")
                except Exception as exc:
                    logger.warning("chatgpt_apply_tool_failed", tool=config.tool_id, error=str(exc))
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:
                        pass

        # 2. Mode application (Standard vs Thinking)
        # Note: Thinking is only applicable with Deep Research or standard chat (none).
        # For other tools (Web Search, Create Image), mode is always Standard.
        is_restricted_tool = config.tool_id in {"web_search", "create_image"}
        want_thinking = (config.mode_id == "thinking") and not is_restricted_tool

        try:
            think_loc = page.locator("button.__composer-pill:has-text('Think'), button:has-text('Think')").first
            if await think_loc.count() > 0:
                is_pressed = (await self.safe_attr(think_loc, "aria-pressed")) == "true"
                if want_thinking and not is_pressed:
                    await think_loc.click(timeout=2000)
                    logger.info("chatgpt_think_mode_enabled")
                elif not want_thinking and is_pressed:
                    await think_loc.click(timeout=2000)
                    logger.info("chatgpt_think_mode_disabled")
        except Exception as exc:
            logger.warning("chatgpt_apply_think_failed", error=str(exc))
