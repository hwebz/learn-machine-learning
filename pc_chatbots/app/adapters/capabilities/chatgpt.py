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
                id="none",
                label="Auto (Mặc định)",
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
            selected_model_id="none",
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
            # Wait for main page / composer to mount
            try:
                await page.wait_for_selector("#prompt-textarea, [contenteditable='true']", timeout=12000)
            except Exception:
                pass
            await asyncio.sleep(1.0)

            # 1. Check if blocked by login wall or CAPTCHA
            from app.adapters.selectors_loader import load_selectors
            from app.browser.waits import detect_blocking_state

            selectors = load_selectors()
            blocking = await detect_blocking_state(page, selectors.get("blocking", {}))
            if blocking is not None:
                caps.last_error = f"Trình duyệt yêu cầu xác thực người dùng ({blocking.kind}): {blocking.detail}"
                caps.is_live_dom = False
                return caps

            # 2. Account Type Detection (Plus vs Free)
            is_plus_account = False
            plus_loc = page.locator(
                "span:has-text('Plus'), div:has-text('Plus'), [data-testid*='profile']:has-text('Plus'), "
                "button[aria-label*='Select ChatGPT model' i]"
            )
            if await plus_loc.count() > 0:
                is_plus_account = True
            else:
                try:
                    profile_plan = await page.evaluate('''() => {
                        const els = Array.from(document.querySelectorAll('nav *, [data-testid*="profile"] *'));
                        return els.some(e => e.innerText && e.innerText.trim() === 'Plus') ? 'plus' : 'free';
                    }''')
                    is_plus_account = (profile_plan == 'plus')
                except Exception:
                    pass

            caps.account_type = "plus" if is_plus_account else "free"
            logger.info("chatgpt_account_type_detected", account_type=caps.account_type)

            # 3. Model Switcher & Available Models Detection
            model_btn = page.locator(
                "button[aria-label*='Select ChatGPT model' i], "
                "button[data-testid='model-switcher-dropdown'], "
                "button[id*='model-switcher']"
            ).first

            discovered_models: list[OptionItem] = []
            selected_model_id = "default"

            if await model_btn.count() > 0 and await model_btn.is_visible(timeout=800):
                caps.account_type = "plus"
                try:
                    await model_btn.click(timeout=2500)
                    await asyncio.sleep(0.6)
                    menu_items = await page.evaluate('''() => {
                        const radios = Array.from(document.querySelectorAll('[role="menuitemradio"]'));
                        return radios.map(r => {
                            const fullText = r.innerText.trim();
                            const parts = fullText.split('\\n').map(s => s.trim()).filter(Boolean);
                            const name = parts[0] || '';
                            const desc = parts.slice(1).join(' - ') || '';
                            const isChecked = r.getAttribute('aria-checked') === 'true';
                            return { name, desc, isChecked };
                        });
                    }''')
                    if menu_items:
                        for m in menu_items:
                            clean_id = m['name'].lower().replace(' ', '-').replace('.', '_')
                            is_sel = m['isChecked']
                            if is_sel:
                                selected_model_id = clean_id
                            discovered_models.append(OptionItem(
                                id=clean_id,
                                label=m['name'],
                                description=m['desc'] or f"Mô hình {m['name']} trên tài khoản Plus",
                                selected=is_sel,
                                badge="Plus",
                            ))
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
                except Exception as exc:
                    logger.warning("chatgpt_model_menu_scan_failed", error=str(exc))
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:
                        pass

            if discovered_models:
                caps.available_models = discovered_models
                caps.selected_model_id = selected_model_id
            elif caps.account_type == "plus":
                caps.available_models = [
                    OptionItem(id="gpt-6", label="GPT-6", description="Mô hình suy luận và thông minh hàng đầu", selected=True, badge="Plus"),
                    OptionItem(id="gpt-5_6-sol", label="GPT-5.6 Sol", description="Tốc độ cao và tối ưu tác vụ hàng ngày", selected=False, badge="Plus"),
                    OptionItem(id="gpt-5_5", label="GPT-5.5", description="Mô hình tiêu chuẩn Plus", selected=False, badge="Plus"),
                ]
                caps.selected_model_id = "gpt-6"
            else:
                caps.available_models = [
                    OptionItem(
                        id="none",
                        label="Auto (Mặc định)",
                        description="Tự động lựa chọn mô hình phù hợp theo loại tài khoản (Free Account)",
                        selected=True,
                        badge="Free",
                    )
                ]
                caps.selected_model_id = "none"

            # 4. Reasoning Picker (Thinking Effort)
            if caps.account_type == "plus":
                caps.thinking_levels = [
                    OptionItem(id="auto", label="Auto (Tự động)", description="Tự động cân bằng mức suy luận theo độ phức tạp", selected=True),
                    OptionItem(id="high", label="High (Cao)", description="Suy luận sâu tối đa cho bài toán phức tạp", selected=False, badge="Deep"),
                    OptionItem(id="medium", label="Medium (Vừa)", description="Suy luận tiêu chuẩn cân bằng tốc độ", selected=False),
                    OptionItem(id="low", label="Low (Thấp)", description="Suy luận tối thiểu ưu tiên tốc độ phản hồi", selected=False),
                ]
                caps.selected_thinking_level_id = "auto"
            else:
                caps.thinking_levels = [
                    OptionItem(
                        id="auto",
                        label="Auto (Tự động)",
                        description="Tự động cân bằng mức suy luận trên tài khoản Free",
                        selected=True,
                    )
                ]
                caps.selected_thinking_level_id = "auto"

            # 5. Mode: Check if Think pill is currently active in the composer
            think_loc = page.locator(
                "button:has-text('Think'), "
                "[role='button']:has-text('Think'), "
                "button[aria-label*='Think' i]"
            ).first
            try:
                await think_loc.wait_for(state="visible", timeout=2000)
            except Exception:
                pass

            if await think_loc.count() > 0:
                is_pressed = (await self.safe_attr(think_loc, "aria-pressed")) == "true"
                caps.selected_mode_id = "thinking" if is_pressed else "standard"
                for m in caps.modes:
                    m.selected = (m.id == caps.selected_mode_id)

            # 6. Tools Detection (Plus menu)
            plus_btn = page.locator(
                "button[aria-label*='Add files' i], "
                "button[data-testid='attach-button'], "
                "button[aria-label*='Attach' i], "
                "button[aria-haspopup='menu']"
            )
            has_plus = await plus_btn.count() > 0
            if has_plus:
                for t in caps.tools:
                    if t.id != "none":
                        t.badge = "Live"

            # 7. File / Image Upload Capabilities
            attach_loc = page.locator(
                "button[aria-label*='Add files' i], "
                "button[data-testid='attach-button'], "
                "button[aria-label*='Attach' i], "
                "button[aria-label*='Đính kèm' i], "
                "button[aria-label*='files' i], "
                "input[type='file']"
            ).first
            has_attach = await attach_loc.count() > 0
            is_disabled = False
            if has_attach:
                dis = await self.safe_attr(attach_loc, "disabled")
                aria_dis = await self.safe_attr(attach_loc, "aria-disabled")
                is_disabled = (dis is not None) or (aria_dis == "true")

            can_upload = (has_attach and not is_disabled) or (caps.account_type == "plus")
            caps.supported_data_types.text = True
            caps.supported_data_types.image = can_upload
            caps.supported_data_types.file = can_upload
            caps.supported_data_types.max_file_size_mb = 512 if caps.account_type == "plus" else 50
            caps.supported_data_types.supported_mime_types = [
                "image/*",
                ".pdf",
                ".txt",
                ".csv",
                ".json",
                ".py",
                ".md",
                ".docx",
                ".xlsx",
                ".zip",
            ]

            # 8. Voice Chat Button in DOM
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
                models_count=len(caps.available_models),
            )
        except Exception as exc:
            logger.warning("chatgpt_dom_inspection_failed", error=str(exc))
            caps.last_error = f"Lỗi khi quét DOM: {type(exc).__name__}: {exc}"
            caps.is_live_dom = False

        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Actuate DOM selectors to apply chosen model, tool, mode, and options."""
        # 0. Model Selection (For Plus accounts with model switcher)
        if config.model_id and config.model_id not in {"none", "auto", "default"}:
            try:
                model_btn = page.locator(
                    "button[aria-label*='Select ChatGPT model' i], "
                    "button[data-testid='model-switcher-dropdown']"
                ).first
                if await model_btn.count() > 0:
                    await model_btn.click(timeout=2500)
                    await asyncio.sleep(0.4)
                    target_query = config.model_id.replace('-', ' ').replace('_', '.').lower()
                    target_loc = page.locator(
                        f"[role='menuitemradio']:has-text('{config.model_id}'), "
                        f"[role='menuitemradio']:has-text('{target_query}')"
                    ).first
                    if await target_loc.count() == 0:
                        clean_terms = [t for t in config.model_id.replace('_', '.').split('-') if len(t) > 2]
                        for term in clean_terms:
                            cand = page.locator(f"[role='menuitemradio']:has-text('{term}' i)").first
                            if await cand.count() > 0:
                                target_loc = cand
                                break
                    if await target_loc.count() > 0:
                        try:
                            await target_loc.click(force=True, timeout=2500)
                        except Exception:
                            await target_loc.dispatch_event("click")
                        logger.info("chatgpt_model_applied", model=config.model_id)
                        await asyncio.sleep(0.35)
                    else:
                        await page.keyboard.press("Escape")
            except Exception as exc:
                logger.warning("chatgpt_apply_model_failed", model=config.model_id, error=str(exc))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass

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
                        "button[aria-label*='Add files' i], button[data-testid='attach-button'], button[aria-label*='Attach' i], button[aria-haspopup='menu']"
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
                            try:
                                await item_loc.click(force=True, timeout=2500)
                            except Exception:
                                await item_loc.dispatch_event("click")
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
        is_restricted_tool = config.tool_id in {"web_search", "create_image"}
        want_thinking = (config.mode_id == "thinking") and not is_restricted_tool

        try:
            think_loc = page.locator(
                "button:has-text('Think'), "
                "[role='button']:has-text('Think'), "
                "button[aria-label*='Think' i]"
            ).first
            try:
                await think_loc.wait_for(state="visible", timeout=3000)
            except Exception:
                pass

            if await think_loc.count() > 0:
                is_pressed = (await self.safe_attr(think_loc, "aria-pressed")) == "true"
                if want_thinking and not is_pressed:
                    await think_loc.click(timeout=3000)
                    await asyncio.sleep(0.35)
                    logger.info("chatgpt_think_mode_enabled")
                elif not want_thinking and is_pressed:
                    await think_loc.click(timeout=3000)
                    await asyncio.sleep(0.35)
                    logger.info("chatgpt_think_mode_disabled")
            elif want_thinking:
                try:
                    plus_loc = page.locator(
                        "button[aria-label*='Add files' i], button[data-testid='attach-button'], button[aria-label*='Attach' i], button[aria-haspopup='menu']"
                    ).first
                    if await plus_loc.count() > 0:
                        await plus_loc.click(timeout=2000)
                        await asyncio.sleep(0.35)
                        item_loc = page.locator(
                            "[role='menuitem']:has-text('Thinking'), button:has-text('Thinking')"
                        ).first
                        if await item_loc.count() > 0 and await item_loc.is_visible(timeout=1500):
                            try:
                                await item_loc.click(force=True, timeout=2000)
                            except Exception:
                                await item_loc.dispatch_event("click")
                            logger.info("chatgpt_think_mode_enabled_via_menu")
                        else:
                            await page.keyboard.press("Escape")
                except Exception:
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("chatgpt_apply_think_failed", error=str(exc))
