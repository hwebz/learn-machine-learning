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


class CopilotCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Microsoft 365 Copilot (m365.cloud.microsoft/chat) DOM option discovery,
    configuration, and defaults.

    Supports:
    - Mode dropdown at the top-left: Auto, Quick Response, Think Deeper,
      GPT > GPT-5.6 Sol Quick Response, GPT > GPT-5.6 Sol Think Deeper.
    - Plus button inside textbox: Upload images and files, data sources.
    - Dictation / Voice STT.
    """

    @property
    def provider_name(self) -> str:
        return "copilot"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Microsoft 365 Copilot."""
        modes = [
            OptionItem(
                id="auto",
                label="Auto",
                description="Tự động cân bằng giữa tốc độ và độ chính xác (Mặc định)",
                selected=True,
                badge="Auto",
            ),
            OptionItem(
                id="quick",
                label="Quick Response",
                description="Ưu tiên tốc độ phản hồi nhanh cho các câu hỏi ngắn gọn",
                selected=False,
                badge="Fast",
            ),
            OptionItem(
                id="think_deeper",
                label="Think Deeper",
                description="Kích hoạt mô hình suy luận đa bước chuyên sâu cho bài toán phức tạp",
                selected=False,
                badge="Think",
            ),
            OptionItem(
                id="gpt_5_6_quick",
                label="GPT > GPT-5.6 Sol Quick Response",
                description="Mô hình GPT-5.6 Sol tối ưu tốc độ phản hồi",
                selected=False,
                badge="GPT-5.6",
            ),
            OptionItem(
                id="gpt_5_6_think",
                label="GPT > GPT-5.6 Sol Think Deeper",
                description="Mô hình GPT-5.6 Sol với khả năng suy luận chuyên sâu",
                selected=False,
                badge="GPT-5.6",
            ),
        ]

        models = [
            OptionItem(
                id="auto",
                label="Auto (Mặc định)",
                description="Copilot tự động chọn mô hình và định tuyến qua Chế độ (Mode)",
                selected=True,
                badge="Auto",
                metadata={"multimodal": True, "reasoning": True},
            ),
        ]

        thinking_levels = [
            OptionItem(
                id="auto",
                label="Auto (Tự động)",
                description="Copilot quản lý mức suy luận qua Chế độ (Mode)",
                selected=True,
                badge="Auto",
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
                ".docx",
                ".xlsx",
                ".pptx",
                ".py",
                ".md",
            ],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và chuyển thành văn bản bất đồng bộ qua backend STT.",
        )

        return ProviderLiveCapabilities(
            provider="copilot",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=models,
            selected_model_id="auto",
            thinking_levels=thinking_levels,
            selected_thinking_level_id="auto",
            modes=modes,
            selected_mode_id="auto",
            account_type="personal",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Asynchronously query the live Microsoft 365 Copilot DOM to collect modes,
        models, plus menu options, and capabilities."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        try:
            # 1. Wait for main chat input or composer container to mount
            try:
                await page.wait_for_selector(
                    "#searchbox, textarea, [data-testid='chat-input-container'], [data-testid='PlusMenuButton']",
                    timeout=12000,
                )
            except Exception:
                pass
            await asyncio.sleep(1.0)

            # 2. Check for login / OAuth recovery wall
            from app.adapters.selectors_loader import load_selectors
            from app.browser.waits import detect_blocking_state

            selectors = load_selectors()
            blocking = await detect_blocking_state(page, selectors.get("blocking", {}))
            if blocking is not None:
                caps.last_error = f"Trình duyệt yêu cầu xác thực người dùng ({blocking.kind}): {blocking.detail}"
                caps.is_live_dom = False
                return caps

            # Check if bounced to "Pick an account" screen
            tile_loc = page.locator("div.row.tile div.table[role='button']:not(#otherTile)").first
            if await tile_loc.count() > 0 and await tile_loc.is_visible(timeout=800):
                caps.last_error = "Trình duyệt đang ở màn hình chọn tài khoản đăng nhập (Pick an account)."
                caps.is_live_dom = False
                return caps

            # 3. Detect Account Plan (Commercial data protection vs Personal)
            commercial_badge = page.locator(
                "button[aria-label*='Commercial data protection' i], "
                "[aria-label*='Commercial data protection' i], "
                "span:has-text('Work'), div:has-text('Commercial')"
            ).first
            if await commercial_badge.count() > 0 and await commercial_badge.is_visible(timeout=800):
                caps.account_type = "commercial"
            else:
                caps.account_type = "personal"

            # 4. Mode Switcher Inspection (#gptModeSwitcher)
            mode_btn = page.locator(
                "#gptModeSwitcher, button[aria-label*='Model Selector' i], [data-testid='mode-switcher'] button"
            ).first

            discovered_modes: list[OptionItem] = []
            current_mode_id = "auto"

            if await mode_btn.count() > 0 and await mode_btn.is_visible(timeout=1500):
                try:
                    curr_label = (await self.safe_inner_text(mode_btn, timeout=1000) or "").strip()
                    aria_label = (await self.safe_attr(mode_btn, "aria-label") or "").strip()
                    full_label = curr_label or aria_label

                    await mode_btn.click(timeout=2500)
                    await asyncio.sleep(0.5)

                    # Scan root menu items
                    root_items = await page.evaluate('''() => {
                        const items = Array.from(document.querySelectorAll('[role="menuitem"], [role="menuitemradio"], .fui-MenuItem'));
                        return items.map(el => {
                            const text = (el.innerText || el.textContent || '').trim();
                            const aria = el.getAttribute('aria-label') || '';
                            const hasPopup = el.getAttribute('aria-haspopup') === 'menu';
                            const isChecked = el.getAttribute('aria-checked') === 'true';
                            return { text, aria, hasPopup, isChecked };
                        });
                    }''')

                    # If there is a submenu trigger like "GPT", hover/click to inspect sub-options
                    sub_items = []
                    gpt_menu_item = page.locator("[role='menuitem']:has-text('GPT'), .fui-MenuItem:has-text('GPT')").first
                    if await gpt_menu_item.count() > 0 and await gpt_menu_item.is_visible(timeout=800):
                        try:
                            await gpt_menu_item.hover(timeout=1500)
                            await asyncio.sleep(0.4)
                            sub_items = await page.evaluate('''() => {
                                const allMenus = document.querySelectorAll('[role="menu"]');
                                if (allMenus.length > 1) {
                                    const subMenu = allMenus[allMenus.length - 1];
                                    const items = Array.from(subMenu.querySelectorAll('[role="menuitem"], [role="menuitemradio"], .fui-MenuItem'));
                                    return items.map(el => ({
                                        text: (el.innerText || el.textContent || '').trim(),
                                        aria: el.getAttribute('aria-label') || '',
                                        isChecked: el.getAttribute('aria-checked') === 'true',
                                    }));
                                }
                                return [];
                            }''')
                        except Exception:
                            pass

                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.2)

                    # Build discovered modes list
                    seen_ids = set()
                    for item in root_items:
                        txt = item.get("text") or item.get("aria") or ""
                        clean_txt = txt.split("\n")[0].strip()
                        if not clean_txt or item.get("hasPopup"):
                            continue
                        low = clean_txt.lower()
                        item_id = "auto"
                        badge = "Auto"
                        desc = "Chế độ tự động"
                        if "think" in low:
                            item_id = "think_deeper"
                            badge = "Think"
                            desc = "Kích hoạt mô hình suy luận đa bước chuyên sâu"
                        elif "quick" in low:
                            item_id = "quick"
                            badge = "Fast"
                            desc = "Ưu tiên tốc độ phản hồi nhanh"

                        is_active = (clean_txt.lower() in full_label.lower()) or item.get("isChecked", False)
                        if is_active:
                            current_mode_id = item_id

                        if item_id not in seen_ids:
                            seen_ids.add(item_id)
                            discovered_modes.append(OptionItem(
                                id=item_id,
                                label=clean_txt,
                                description=desc,
                                selected=is_active,
                                badge=badge,
                            ))

                    # Append sub-items (e.g. GPT > GPT-5.6 Sol Quick/Think)
                    for s_item in sub_items:
                        s_txt = s_item.get("text") or s_item.get("aria") or ""
                        clean_s = s_txt.split("\n")[0].strip()
                        if not clean_s:
                            continue
                        low_s = clean_s.lower()
                        s_id = "gpt_5_6_think" if "think" in low_s else "gpt_5_6_quick"
                        is_active = (clean_s.lower() in full_label.lower()) or s_item.get("isChecked", False)
                        if is_active:
                            current_mode_id = s_id

                        if s_id not in seen_ids:
                            seen_ids.add(s_id)
                            discovered_modes.append(OptionItem(
                                id=s_id,
                                label=f"GPT > {clean_s}",
                                description=f"Mô hình GPT-5.6 Sol ({clean_s})",
                                selected=is_active,
                                badge="GPT-5.6",
                            ))

                except Exception as exc:
                    logger.warning("copilot_mode_scan_failed", error=str(exc))
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:
                        pass

            if discovered_modes:
                # Ensure all 5 standard modes are present if any were missing from DOM scan
                base_modes = caps.modes
                existing_ids = {m.id for m in discovered_modes}
                for bm in base_modes:
                    if bm.id not in existing_ids:
                        discovered_modes.append(bm)
                caps.modes = discovered_modes
                caps.selected_mode_id = current_mode_id

            # 5. Plus Icon Button Inside Textbox Inspection (`+` button)
            plus_btn = page.locator(
                "button[data-testid='PlusMenuButton'], "
                "[data-testid='chat-input-container'] button[aria-label*='Add' i], "
                "button[aria-label*='Add and manage sources' i], "
                "button[aria-label*='Add files' i], "
                "button[aria-label*='Upload' i]"
            ).first

            can_upload_files = True
            if await plus_btn.count() > 0 and await plus_btn.is_visible(timeout=1500):
                try:
                    await plus_btn.click(timeout=2500)
                    await asyncio.sleep(0.4)

                    plus_options = await page.evaluate('''() => {
                        const items = Array.from(document.querySelectorAll('[role="menuitem"], .fui-MenuItem, div[class*="MenuPopover"] *'));
                        return items.map(i => (i.innerText || i.textContent || '').trim()).filter(Boolean);
                    }''')

                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.2)

                    logger.info("copilot_plus_menu_discovered", options=plus_options[:6])
                    if any("upload" in opt.lower() or "file" in opt.lower() or "image" in opt.lower() or "tệp" in opt.lower() for opt in plus_options):
                        can_upload_files = True
                except Exception as exc:
                    logger.warning("copilot_plus_menu_scan_failed", error=str(exc))
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:
                        pass

            caps.supported_data_types.text = True
            caps.supported_data_types.image = can_upload_files
            caps.supported_data_types.file = can_upload_files

            # 6. Dictation / Voice Button Inspection
            dictate_btn = page.locator(
                "button[aria-label*='Start dictation' i], button[aria-label*='dictation' i], button[aria-label*='microphone' i]"
            ).first
            has_dictate = await dictate_btn.count() > 0
            caps.voice_chat.supported = True
            if has_dictate:
                caps.voice_chat.details = "Copilot web UI có nút Dictate; hệ thống hỗ trợ micro thu âm bất đồng bộ chuyển văn bản."

            caps.is_live_dom = True
            caps.last_error = None
            logger.info(
                "copilot_dom_inspection_success",
                account_type=caps.account_type,
                mode=caps.selected_mode_id,
                modes_count=len(caps.modes),
                can_upload=caps.supported_data_types.image,
            )
        except Exception as exc:
            logger.warning("copilot_dom_inspection_failed", error=str(exc))
            caps.last_error = f"Lỗi khi quét DOM: {type(exc).__name__}: {exc}"
            caps.is_live_dom = False

        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Actuate DOM selectors on Microsoft 365 Copilot to apply chosen mode / model."""
        target_mode = (config.mode_id or config.model_id or "auto").lower()

        # Map mode_id to matching button / menu item text
        target_text_map = {
            "auto": "Auto",
            "standard": "Auto",
            "quick": "Quick Response",
            "think_deeper": "Think Deeper",
            "deep": "Think Deeper",
            "gpt_5_6_quick": "Quick Response",
            "gpt_5_6_think": "Think Deeper",
        }
        target_label = target_text_map.get(target_mode, "Auto")
        is_gpt_subitem = "gpt_5_6" in target_mode

        try:
            mode_btn = page.locator(
                "#gptModeSwitcher, button[aria-label*='Model Selector' i], [data-testid='mode-switcher'] button"
            ).first
            if await mode_btn.count() == 0:
                logger.info("copilot_mode_switcher_not_found")
                return

            curr_text = (await self.safe_inner_text(mode_btn, timeout=1000) or "").strip().lower()
            if not is_gpt_subitem and target_label.lower() in curr_text:
                logger.info("copilot_mode_already_active", mode=target_mode, current=curr_text)
                return

            await mode_btn.click(timeout=3000)
            await asyncio.sleep(0.5)

            if is_gpt_subitem:
                gpt_item = page.locator("[role='menuitem']:has-text('GPT'), .fui-MenuItem:has-text('GPT')").first
                if await gpt_item.count() > 0 and await gpt_item.is_visible(timeout=1500):
                    await gpt_item.hover(timeout=1500)
                    await asyncio.sleep(0.4)

                    sub_item = page.locator(
                        f"[role='menuitem']:has-text('{target_label}'), .fui-MenuItem:has-text('{target_label}')"
                    ).last
                    if await sub_item.count() > 0 and await sub_item.is_visible(timeout=1500):
                        try:
                            await sub_item.click(force=True, timeout=2500)
                        except Exception:
                            await sub_item.dispatch_event("click")
                        logger.info("copilot_mode_applied_gpt_subitem", target=target_label)
                        await asyncio.sleep(0.5)
                        return

            # Direct root menu items
            menu_item = page.locator(
                f"[role='menuitem']:has-text('{target_label}'), "
                f".fui-MenuItem:has-text('{target_label}')"
            ).first
            if await menu_item.count() > 0 and await menu_item.is_visible(timeout=2000):
                try:
                    await menu_item.click(force=True, timeout=2500)
                except Exception:
                    await menu_item.dispatch_event("click")
                logger.info("copilot_mode_applied", target=target_label)
                await asyncio.sleep(0.5)
            else:
                await page.keyboard.press("Escape")
        except Exception as exc:
            logger.warning("copilot_apply_mode_failed", mode=target_mode, error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
