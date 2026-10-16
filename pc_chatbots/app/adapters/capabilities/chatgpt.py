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
    
    Optimized for Free account tier with Auto model & reasoning, and Standard/Thinking modes.
    """

    @property
    def provider_name(self) -> str:
        return "chatgpt"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for ChatGPT (Free Account defaults with 3 toggles: Web search, Deep research, Thinking)."""
        models = [
            OptionItem(
                id="none",
                label="Auto (Default)",
                description="Tự động chọn mô hình phù hợp theo tài khoản",
                selected=True,
            )
        ]
        thinking_levels = [
            OptionItem(
                id="auto",
                label="Auto Reasoning",
                description="Tự động kích hoạt tư duy khi câu hỏi phức tạp",
                selected=True,
            )
        ]
        modes = [
            OptionItem(
                id="standard",
                label="Standard",
                description="Chế độ trò chuyện tiêu chuẩn tốc độ cao",
                selected=True,
            ),
            OptionItem(
                id="thinking",
                label="Thinking",
                description="Kích hoạt tư duy và giải thích các bước lý luận",
                selected=False,
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
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
            web_search=True,
            deep_research=False,
            deep_thinking=False,
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Asynchronously query the live ChatGPT DOM to collect models, thinking, and modes."""
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
                caps.available_models = []
                caps.selected_model_id = None

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
                caps.thinking_levels = []
                caps.selected_thinking_level_id = None

            # 5. Plus Menu Discovery: Click '+' button to discover all options ChatGPT provides
            plus_btn = page.locator(
                "button[aria-label*='Add files and more' i], "
                "button[aria-label*='Add files' i], "
                "button[data-testid='attach-button'], "
                "button[data-testid='composer-attach-button'], "
                "button[aria-label*='Attach' i], "
                "button[aria-label*='Đính kèm' i], "
                "button[aria-label*='Upload' i], "
                "button[aria-haspopup='menu']"
            ).first

            discovered_plus_items: list[dict[str, Any]] = []
            has_attach = False

            if await plus_btn.count() > 0 and await plus_btn.is_visible(timeout=1500):
                has_attach = True
                is_disabled = await self.is_disabled(plus_btn)
                if not is_disabled:
                    try:
                        await plus_btn.click(timeout=2500)
                        await asyncio.sleep(0.5)

                        menu = page.locator(
                            "div[class*='composer-home-top-menu'], div[class*='ComposerTopMenuShell'], div[class*='suggestionMenu'], [role='menu']"
                        ).first
                        if await menu.count() > 0 and await menu.is_visible(timeout=1500):
                            buttons = menu.locator("button, [role='menuitem']")
                            b_count = await buttons.count()
                            for i in range(b_count):
                                b = buttons.nth(i)
                                raw_text = await self.safe_inner_text(b, timeout=800)
                                if not raw_text or len(raw_text) > 120:
                                    continue
                                lines = [s.strip() for s in raw_text.split("\n") if s.strip()]
                                title = lines[0] if lines else ""
                                desc = " - ".join(lines[1:]) if len(lines) > 1 else ""
                                is_sel = "selected" in raw_text.lower() or (await self.safe_attr(b, "aria-checked")) == "true"
                                discovered_plus_items.append({
                                    "title": title,
                                    "description": desc,
                                    "selected": is_sel,
                                })

                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.2)
                        logger.info("chatgpt_plus_menu_discovered", items=[it["title"] for it in discovered_plus_items])
                    except Exception as exc:
                        logger.warning("chatgpt_plus_menu_scan_failed", error=str(exc))
                        try:
                            await page.keyboard.press("Escape")
                        except Exception:
                            pass
            else:
                file_input = page.locator("input[type='file']").first
                has_attach = (await file_input.count() > 0) or (caps.account_type in {"plus", "free"})

            # 6. Toggles Detection: Web search, Deep research, Thinking
            think_loc = page.locator(
                "button:has-text('Think'), "
                "[role='button']:has-text('Think'), "
                "button[aria-label*='Think' i]"
            ).first
            try:
                await think_loc.wait_for(state="visible", timeout=1500)
            except Exception:
                pass

            is_think_pressed = False
            if await think_loc.count() > 0:
                is_think_pressed = (await self.safe_attr(think_loc, "aria-pressed")) == "true"
            else:
                for it in discovered_plus_items:
                    if "think" in it["title"].lower() and it.get("selected"):
                        is_think_pressed = True
                        break

            search_pill = page.locator(
                "[data-testid*='search-pill'], button[aria-label*='Remove Web search' i], "
                "button:has-text('Search'), div[class*='pill']:has-text('Search')"
            ).first
            is_web_search_active = (await search_pill.count() > 0) or any("web search" in it["title"].lower() and it.get("selected") for it in discovered_plus_items)

            research_pill = page.locator(
                "[data-testid*='research-pill'], button[aria-label*='Remove Deep research' i], "
                "button:has-text('Deep research'), div[class*='pill']:has-text('Deep research')"
            ).first
            is_deep_research_active = (await research_pill.count() > 0) or any("deep research" in it["title"].lower() and it.get("selected") for it in discovered_plus_items)

            caps.modes = []
            caps.selected_mode_id = None
            caps.available_models = []
            caps.selected_model_id = None
            caps.thinking_levels = []
            caps.selected_thinking_level_id = None

            caps.deep_thinking = is_think_pressed
            caps.web_search = True if is_web_search_active else True
            caps.deep_research = is_deep_research_active

            # 7. File / Image Upload Capabilities
            has_photos_or_files = any(
                any(kw in it["title"].lower() or kw in it["description"].lower() for kw in ["photo", "file", "tệp", "ảnh", "computer", "máy tính", "library", "upload", "tải lên", "drive"])
                for it in discovered_plus_items
            ) or has_attach

            caps.supported_data_types.text = True
            caps.supported_data_types.image = has_photos_or_files
            caps.supported_data_types.file = has_photos_or_files
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
                web_search=caps.web_search,
                deep_research=caps.deep_research,
                deep_thinking=caps.deep_thinking,
                can_upload=caps.supported_data_types.image,
            )
        except Exception as exc:
            logger.warning("chatgpt_dom_inspection_failed", error=str(exc))
            caps.last_error = f"Lỗi khi quét DOM: {type(exc).__name__}: {exc}"
            caps.is_live_dom = False

        return caps

    async def _click_plus_menu_item(self, page: Any, item_name: str) -> bool:
        """Open composer + menu, find matching item by name, click it, or dismiss."""
        try:
            plus_btn = page.locator(
                "button[aria-label*='Add files and more' i], "
                "button[aria-label*='Add files' i], "
                "button[data-testid='attach-button'], "
                "button[data-testid='composer-attach-button'], "
                "button[aria-label*='Attach' i], "
                "button[aria-haspopup='menu']"
            ).first
            if await plus_btn.count() == 0:
                return False

            await plus_btn.click(timeout=2500)
            await asyncio.sleep(0.35)

            menu = page.locator(
                "div[class*='composer-home-top-menu'], div[class*='ComposerTopMenuShell'], div[class*='suggestionMenu'], [role='menu']"
            ).first
            target_btn = menu.locator(
                f"button:has-text('{item_name}'), [role='menuitem']:has-text('{item_name}')"
            ).first

            if await target_btn.count() > 0 and await target_btn.is_visible(timeout=1500):
                try:
                    await target_btn.click(force=True, timeout=2000)
                except Exception:
                    await target_btn.dispatch_event("click")
                logger.info("chatgpt_plus_menu_item_clicked", item=item_name)
                await asyncio.sleep(0.3)
                return True
            else:
                await page.keyboard.press("Escape")
                return False
        except Exception as exc:
            logger.warning("chatgpt_click_plus_item_failed", item=item_name, error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            return False

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Actuate DOM selectors to apply chosen toggles: Web search, Deep research, Thinking."""
        # 1. Thinking Toggle (deep_thinking or mode_id == "thinking")
        want_thinking = config.deep_thinking if config.deep_thinking is not None else (config.mode_id == "thinking" if config.mode_id else None)
        if want_thinking is not None:
            try:
                think_loc = page.locator(
                    "button:has-text('Think'), "
                    "[role='button']:has-text('Think'), "
                    "button[aria-label*='Think' i]"
                ).first
                try:
                    await think_loc.wait_for(state="visible", timeout=1500)
                except Exception:
                    pass

                if await think_loc.count() > 0:
                    is_pressed = (await self.safe_attr(think_loc, "aria-pressed")) == "true"
                    if want_thinking and not is_pressed:
                        await think_loc.click(timeout=2500)
                        logger.info("chatgpt_think_mode_enabled")
                    elif not want_thinking and is_pressed:
                        await think_loc.click(timeout=2500)
                        logger.info("chatgpt_think_mode_disabled")
                elif want_thinking:
                    await self._click_plus_menu_item(page, "Thinking")
            except Exception as exc:
                logger.warning("chatgpt_apply_think_failed", error=str(exc))

        # 2. Web Search Toggle (web_search)
        if config.web_search is not None:
            try:
                search_pill = page.locator(
                    "[data-testid*='search-pill'], button[aria-label*='Remove Web search' i], "
                    "button:has-text('Search'), div[class*='pill']:has-text('Search')"
                ).first
                is_active = (await search_pill.count() > 0) and (await search_pill.is_visible(timeout=500))
                if (config.web_search and not is_active) or (not config.web_search and is_active):
                    await self._click_plus_menu_item(page, "Web search")
            except Exception as exc:
                logger.warning("chatgpt_apply_web_search_failed", error=str(exc))

        # 3. Deep Research Toggle (deep_research)
        if config.deep_research is not None:
            try:
                research_pill = page.locator(
                    "[data-testid*='research-pill'], button[aria-label*='Remove Deep research' i], "
                    "button:has-text('Deep research'), div[class*='pill']:has-text('Deep research')"
                ).first
                is_active = (await research_pill.count() > 0) and (await research_pill.is_visible(timeout=500))
                if (config.deep_research and not is_active) or (not config.deep_research and is_active):
                    await self._click_plus_menu_item(page, "Deep research")
            except Exception as exc:
                logger.warning("chatgpt_apply_deep_research_failed", error=str(exc))
