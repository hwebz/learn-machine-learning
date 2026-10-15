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


class GeminiCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Google Gemini (gemini.google.com/app) DOM option discovery,
    configuration, and defaults.

    Supports:
    - Mode/Model dropdown: 3.5 Flash-Lite, 3.8 Flash, 3.1 Pro, 4 Argon.
    - Thinking Effort submenu (Cấp độ tư duy): Thấp (Low), Trung bình (Medium), Cao (High).
    - File & Image uploads.
    - Voice STT microphone.
    """

    @property
    def provider_name(self) -> str:
        return "gemini"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Google Gemini."""
        models = [
            OptionItem(
                id="gemini-3.8-flash",
                label="3.8 Flash (Trợ giúp toàn diện)",
                description="Mô hình cân bằng tối ưu giữa tốc độ và trí tuệ",
                selected=True,
                badge="Flash",
                metadata={"speed": "fast", "multimodal": True},
            ),
            OptionItem(
                id="gemini-3.1-pro",
                label="3.1 Pro (Suy luận nâng cao)",
                description="Mô hình suy luận sâu và xử lý logic phức tạp",
                selected=False,
                badge="Pro",
                metadata={"reasoning": True, "multimodal": True},
            ),
            OptionItem(
                id="gemini-4-argon",
                label="4 Argon (Nhiệm vụ phức tạp)",
                description="Mô hình thế hệ mới nhất cho các bài toán chuyên sâu",
                selected=False,
                badge="Argon",
                metadata={"experimental": True, "reasoning": True},
            ),
            OptionItem(
                id="gemini-3.5-flash-lite",
                label="3.5 Flash-Lite (Câu trả lời nhanh nhất)",
                description="Tối ưu độ trễ cho các câu hỏi ngắn gọn",
                selected=False,
                badge="Fast",
            ),
        ]

        thinking_levels = [
            OptionItem(
                id="high",
                label="Cao (Cực kỳ kỹ lưỡng)",
                description="Kích hoạt tư duy đa bước chuyên sâu và kiểm chứng phản biện",
                selected=False,
                badge="High",
            ),
            OptionItem(
                id="medium",
                label="Trung bình (Độ sâu cân bằng)",
                description="Cân bằng lý tưởng giữa thời gian suy nghĩ và độ sâu nội dung",
                selected=True,
                badge="Med",
            ),
            OptionItem(
                id="low",
                label="Thấp (Nhanh chóng và hiệu quả)",
                description="Suy luận cơ bản, phản hồi nhanh chóng",
                selected=False,
                badge="Low",
            ),
        ]

        modes = [
            OptionItem(
                id="standard",
                label="Standard (Tiêu chuẩn)",
                description="Chế độ trò chuyện tiêu chuẩn nhanh chóng",
                selected=True,
                badge="Standard",
            ),
            OptionItem(
                id="deep",
                label="Deep Reasoning",
                description="Kích hoạt mô hình 3.1 Pro với mức suy luận Cao",
                selected=False,
                badge="Deep",
            ),
        ]

        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=True,
            video=True,
            max_file_size_mb=100,
            supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".docx", ".xlsx", "audio/*", "video/*"],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và chuyển thành văn bản thời gian thực.",
        )

        return ProviderLiveCapabilities(
            provider="gemini",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=models,
            selected_model_id="gemini-3.8-flash",
            thinking_levels=thinking_levels,
            selected_thinking_level_id="medium",
            modes=modes,
            selected_mode_id="standard",
            account_type="pro",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def _find_dropdown_button(self, page: Any, timeout_s: float = 8.0) -> Any | None:
        """Locate the Gemini mode/model dropdown trigger button with polling for SPA hydration."""
        import time

        candidates = [
            "button:has-text('Flash-Lite')",
            "button:has-text('3.8 Flash')",
            "button:has-text('3.1 Pro')",
            "button:has-text('4 Argon')",
            "button:has-text('Flash')",
            "button:has-text('Pro')",
            "button:has-text('Argon')",
            "button[data-test-id='bard-mode-menu-button']",
            "bard-mode-switcher button",
            ".input-area-switch",
            "button[aria-label*='chế độ' i]",
            "button[aria-label*='mode' i]",
            "button:has(mat-icon[data-mat-icon-name='keyboard_arrow_down'])",
        ]
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            for sel in candidates:
                try:
                    loc = page.locator(sel)
                    cnt = await loc.count()
                    for i in range(cnt):
                        b = loc.nth(i)
                        if await b.is_visible(timeout=300):
                            return b
                except Exception:
                    continue
            await asyncio.sleep(0.4)
        return None

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect Gemini's live web DOM to extract active and available models & thinking levels."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        btn = await self._find_dropdown_button(page)
        if btn is None:
            logger.info("gemini_dropdown_button_not_found_fallback")
            caps.is_live_dom = False
            return caps

        try:
            # Check button text/aria to determine currently selected model
            btn_text = (await btn.inner_text()).strip()
            btn_aria = (await btn.get_attribute("aria-label")) or ""
            combo_text = f"{btn_text} {btn_aria}".lower()

            logger.info("gemini_inspect_dropdown_found", text=btn_text, aria=btn_aria)

            # Open menu
            await btn.click(timeout=3000)
            await asyncio.sleep(0.8)

            # 1. Read models from first-level menu
            menu_items = page.locator("[role='menuitem'], .mat-mdc-menu-item")
            item_cnt = await menu_items.count()
            discovered_models: list[OptionItem] = []
            selected_model_id = caps.selected_model_id
            thinking_menu_item = None

            for i in range(item_cnt):
                item = menu_items.nth(i)
                if not await item.is_visible(timeout=200):
                    continue
                raw_text = (await item.inner_text()).strip()
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                title = lines[0] if lines else raw_text
                subtitle = lines[1] if len(lines) > 1 else ""

                lower_title = title.lower()

                # Check if this is the thinking submenu trigger
                if "tư duy" in lower_title or "thinking" in lower_title:
                    thinking_menu_item = item
                    continue

                # It's a model option!
                # Generate clean ID
                if "flash-lite" in lower_title or "3.5" in lower_title:
                    m_id = "gemini-3.5-flash-lite"
                    badge = "Lite"
                elif "3.8" in lower_title or "flash" in lower_title:
                    m_id = "gemini-3.8-flash"
                    badge = "Flash"
                elif "3.1" in lower_title or "pro" in lower_title:
                    m_id = "gemini-3.1-pro"
                    badge = "Pro"
                elif "argon" in lower_title or "4" in lower_title:
                    m_id = "gemini-4-argon"
                    badge = "Argon"
                else:
                    m_id = f"gemini-{lower_title.replace(' ', '-')}"
                    badge = "AI"

                # Check if selected
                has_check = "✓" in raw_text or await item.locator(".mat-icon:has-text('check'), [data-mat-icon-name='check']").count() > 0
                if has_check or (btn_text and btn_text.lower() in lower_title):
                    selected_model_id = m_id

                discovered_models.append(
                    OptionItem(
                        id=m_id,
                        label=title,
                        description=subtitle or f"Mô hình {title}",
                        selected=(m_id == selected_model_id),
                        badge=badge,
                    )
                )

            if discovered_models:
                caps.available_models = discovered_models
                caps.selected_model_id = selected_model_id

            # 2. Inspect Thinking Levels submenu if available
            if thinking_menu_item is not None:
                try:
                    await thinking_menu_item.hover()
                    await asyncio.sleep(0.3)
                    await thinking_menu_item.click(timeout=2000)
                    await asyncio.sleep(0.8)

                    sub_items = page.locator("[role='menuitem'], .mat-mdc-menu-item")
                    sub_cnt = await sub_items.count()
                    discovered_thinking: list[OptionItem] = []
                    selected_thinking_id = caps.selected_thinking_level_id
                    seen_thinking_ids: set[str] = set()

                    for j in range(sub_cnt):
                        s_item = sub_items.nth(j)
                        if not await s_item.is_visible(timeout=100):
                            continue
                        s_raw = (await s_item.inner_text()).strip()
                        s_lines = [l.strip() for l in s_raw.split("\n") if l.strip()]
                        first_line = s_lines[0].lower() if s_lines else ""

                        if first_line.startswith("thấp") or first_line == "low":
                            t_id = "low"
                            t_label = "Thấp (Nhanh chóng & hiệu quả)"
                            t_badge = "Low"
                        elif first_line.startswith("trung bình") or first_line == "medium" or first_line == "vừa":
                            t_id = "medium"
                            t_label = "Trung bình (Độ sâu cân bằng)"
                            t_badge = "Med"
                        elif first_line.startswith("cao") or first_line == "high":
                            t_id = "high"
                            t_label = "Cao (Cực kỳ kỹ lưỡng)"
                            t_badge = "High"
                        else:
                            continue

                        if t_id in seen_thinking_ids:
                            continue
                        seen_thinking_ids.add(t_id)

                        s_has_check = "✓" in s_raw or await s_item.locator(".mat-icon:has-text('check'), [data-mat-icon-name='check']").count() > 0
                        if s_has_check:
                            selected_thinking_id = t_id

                        discovered_thinking.append(
                            OptionItem(
                                id=t_id,
                                label=t_label,
                                description=s_raw.replace("\n", " - "),
                                selected=(t_id == selected_thinking_id),
                                badge=t_badge,
                            )
                        )

                    if discovered_thinking:
                        caps.thinking_levels = discovered_thinking
                        caps.selected_thinking_level_id = selected_thinking_id
                except Exception as sub_err:
                    logger.warning("gemini_thinking_submenu_inspect_failed", error=str(sub_err))

            # Close menu
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            await page.keyboard.press("Escape")

            caps.is_live_dom = True
            logger.info(
                "gemini_dom_inspected_successfully",
                models_count=len(caps.available_models),
                selected_model=caps.selected_model_id,
                thinking_levels_count=len(caps.thinking_levels),
                selected_thinking=caps.selected_thinking_level_id,
            )
            return caps
        except Exception as exc:
            logger.warning("gemini_inspect_dom_error", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            caps.is_live_dom = False
            caps.last_error = str(exc)
            return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Apply target model and thinking effort to Gemini's web interface."""
        btn = await self._find_dropdown_button(page)
        if btn is None:
            logger.info("gemini_apply_button_not_found")
            return

        target_model = (config.model_id or "").lower().strip()
        target_thinking = (config.thinking_level_id or "").lower().strip()
        mode_val = (config.mode_id or "").lower().strip()

        if mode_val in {"deep", "deep_research"} and not target_thinking:
            target_thinking = "high"
            if not target_model:
                target_model = "pro"

        logger.info(
            "gemini_applying_selection",
            target_model=target_model,
            target_thinking=target_thinking,
        )

        try:
            # 1. Select Model if target_model specified
            if target_model and target_model != "auto" and target_model != "default":
                btn = await self._find_dropdown_button(page)
                if btn:
                    curr_txt = (await btn.inner_text()).lower()
                    # Check if already on target model
                    already_selected = (
                        ("argon" in target_model and "argon" in curr_txt)
                        or ("pro" in target_model and "pro" in curr_txt)
                        or ("flash-lite" in target_model and "lite" in curr_txt)
                        or ("flash" in target_model and "flash" in curr_txt and "lite" not in curr_txt)
                    )
                    if not already_selected:
                        await btn.click(timeout=3000)
                        await asyncio.sleep(0.6)

                        # Determine selector for target model
                        if "argon" in target_model or "4" in target_model:
                            pattern = "Argon"
                        elif "pro" in target_model or "3.1" in target_model:
                            pattern = "3.1 Pro"
                        elif "lite" in target_model or "3.5" in target_model:
                            pattern = "Flash-Lite"
                        else:
                            pattern = "3.8 Flash"

                        target_item = page.locator(f"[role='menuitem']:has-text('{pattern}'), .mat-mdc-menu-item:has-text('{pattern}')").first
                        if await target_item.is_visible(timeout=2000):
                            await target_item.click(timeout=3000)
                            logger.info("gemini_model_clicked", target=pattern)
                            await asyncio.sleep(1.0)
                        else:
                            await page.keyboard.press("Escape")
                            await asyncio.sleep(0.3)

            # 2. Select Thinking level if target_thinking specified
            if target_thinking and target_thinking != "auto":
                btn = await self._find_dropdown_button(page)
                if btn:
                    await btn.click(timeout=3000)
                    await asyncio.sleep(0.6)

                    # Hover/click "Cấp độ tư duy" or "Thinking"
                    thinking_trigger = page.locator("[role='menuitem']:has-text('Cấp độ tư duy'), [role='menuitem']:has-text('tư duy'), [role='menuitem']:has-text('Thinking')").first
                    if await thinking_trigger.is_visible(timeout=2000):
                        await thinking_trigger.hover()
                        await asyncio.sleep(0.3)
                        await thinking_trigger.click(timeout=2000)
                        await asyncio.sleep(0.6)

                        # Select High, Medium, or Low
                        if target_thinking in {"high", "cao", "deep"}:
                            lvl_text = "Cao"
                        elif target_thinking in {"medium", "trung bình", "vừa", "med"}:
                            lvl_text = "Trung bình"
                        else:
                            lvl_text = "Thấp"

                        lvl_items = page.locator("[role='menuitem'], .mat-mdc-menu-item")
                        cnt = await lvl_items.count()
                        clicked = False
                        for k in range(cnt):
                            cand = lvl_items.nth(k)
                            if not await cand.is_visible(timeout=100):
                                continue
                            txt = (await cand.inner_text()).strip()
                            first_line = txt.split("\n")[0].strip()
                            if first_line.lower().startswith(lvl_text.lower()):
                                await cand.click(timeout=3000)
                                logger.info("gemini_thinking_level_clicked", level=lvl_text)
                                clicked = True
                                await asyncio.sleep(1.0)
                                break
                        if not clicked:
                            await page.keyboard.press("Escape")
                            await asyncio.sleep(0.3)
                    else:
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.3)

            # Final cleanup: ensure popup menu is dismissed
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)
        except Exception as exc:
            logger.warning("gemini_apply_selection_failed", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
