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


class ClaudeCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Anthropic Claude (claude.ai) DOM option discovery,
    configuration, and defaults.

    Supports:
    - Model selection: Sonnet 5.5, Haiku 5.5, Opus 5.5, Fable 5.1.
    - Thinking Effort submenu: Low, Medium (Recommended), High, Extra, Max.
    - File & Image uploads.
    - Voice STT microphone.
    - Clean manual combinations without a synthetic Mode dropdown.
    """

    @property
    def provider_name(self) -> str:
        return "claude"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Anthropic Claude."""
        models = [
            OptionItem(
                id="claude-sonnet-5.5",
                label="Claude Sonnet 5.5 (Cân bằng & thông minh)",
                description="Mô hình cân bằng hoàn hảo giữa trí tuệ suy luận sâu sắc và tốc độ xử lý.",
                selected=True,
                disabled=False,
                badge="Sonnet",
                metadata={"reasoning": True, "multimodal": True},
            ),
            OptionItem(
                id="claude-haiku-5.5",
                label="Claude Haiku 5.5 (Phản hồi nhanh)",
                description="Mô hình tối ưu tốc độ phản hồi nhanh nhất cho các câu hỏi ngắn và tác vụ gọn.",
                selected=False,
                disabled=False,
                badge="Haiku",
                metadata={"speed": "fast"},
            ),
            OptionItem(
                id="claude-opus-5.5",
                label="Claude Opus 5.5 (Pro)",
                description="Dành cho tài khoản Pro (Yêu cầu nâng cấp gói)",
                selected=False,
                disabled=True,
                badge="Upgrade",
                metadata={"reasoning": True, "pro": True, "upgrade": True},
            ),
            OptionItem(
                id="claude-fable-5.1",
                label="Claude Fable 5.1 (Max)",
                description="Dành cho tài khoản Pro hoặc Max (Yêu cầu nâng cấp gói)",
                selected=False,
                disabled=True,
                badge="Upgrade",
                metadata={"pro": True, "upgrade": True},
            ),
        ]

        thinking_levels = [
            OptionItem(
                id="medium",
                label="Trung bình (Medium - Khuyên dùng)",
                description="Cân bằng tối ưu giữa độ sâu suy luận và giới hạn tin nhắn.",
                selected=True,
                badge="Med",
            ),
            OptionItem(
                id="low",
                label="Thấp (Low - Nhanh & tiết kiệm)",
                description="Giảm thiểu các bước suy nghĩ để tăng tốc độ phản hồi.",
                selected=False,
                badge="Low",
            ),
            OptionItem(
                id="high",
                label="Cao (High - Kỹ lưỡng)",
                description="Kích hoạt phân tích đa bước mở rộng cho bài toán hóc búa.",
                selected=False,
                badge="High",
            ),
            OptionItem(
                id="extra",
                label="Rất cao (Extra)",
                description="Độ sâu suy luận mở rộng chuyên biệt cho nghiên cứu chuyên sâu.",
                selected=False,
                badge="Extra",
            ),
            OptionItem(
                id="max",
                label="Tối đa (Max - 8x giới hạn)",
                description="Mức suy luận tối đa cho các công trình nghiên cứu và lập trình quy mô lớn.",
                selected=False,
                badge="Max",
            ),
        ]

        modes: list[OptionItem] = []

        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=30,
            supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".docx", ".xlsx", ".py", ".md"],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và chuyển thành văn bản thời gian thực qua backend.",
        )

        return ProviderLiveCapabilities(
            provider="claude",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=models,
            selected_model_id="claude-sonnet-5.5",
            thinking_levels=thinking_levels,
            selected_thinking_level_id="medium",
            modes=modes,
            selected_mode_id=None,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def _find_model_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate the Claude model & effort dropdown trigger button with polling."""
        import time

        candidates = [
            "button[data-testid='model-selector-dropdown']",
            "button[aria-label*='Model:']",
            "button[aria-label*='Model']",
            "button:has-text('Sonnet')",
            "button:has-text('Haiku')",
            "button:has-text('Opus')",
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
        """Inspect Claude's live web DOM to extract active and available models & thinking effort levels."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        caps.modes = []
        caps.selected_mode_id = None

        # 1. Detect account type
        try:
            body_text = await page.evaluate("() => document.body.innerText || ''")
            if "Pro plan" in body_text or "Claude Pro" in body_text:
                caps.account_type = "pro"
            elif "Max plan" in body_text or "Claude Max" in body_text:
                caps.account_type = "max"
            elif "Free plan" in body_text or "Upgrade" in body_text:
                caps.account_type = "free"
        except Exception:
            pass

        # 2. Inspect Model & Thinking from dropdown
        model_btn = await self._find_model_button(page)
        if model_btn is not None:
            try:
                curr_btn_text = (await model_btn.inner_text()).strip()
                logger.info("claude_inspect_model_button_found", text=curr_btn_text)
                await model_btn.click(timeout=3000)
                await asyncio.sleep(0.8)

                # Find menu items in the main dropdown
                items = page.locator("[role='menuitemradio'], [role='menuitem']")
                cnt = await items.count()
                discovered_models: list[OptionItem] = []
                seen_m_ids: set[str] = set()

                for i in range(cnt):
                    item = items.nth(i)
                    if not await item.is_visible(timeout=100):
                        continue
                    txt = (await item.inner_text()).strip()
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    if not lines:
                        continue
                    first_line = lines[0]

                    m_id = None
                    badge = None
                    if "sonnet" in first_line.lower():
                        m_id = "claude-sonnet-5.5"
                        badge = "Sonnet"
                    elif "haiku" in first_line.lower():
                        m_id = "claude-haiku-5.5"
                        badge = "Haiku"
                    elif "opus" in first_line.lower():
                        m_id = "claude-opus-5.5"
                        badge = "Opus"
                    elif "fable" in first_line.lower():
                        m_id = "claude-fable-5.1"
                        badge = "Fable"

                    if not m_id or m_id in seen_m_ids:
                        continue
                    seen_m_ids.add(m_id)

                    is_upgrade = "upgrade" in txt.lower() or (caps.account_type == "free" and m_id in {"claude-opus-5.5", "claude-fable-5.1"})
                    desc = lines[1] if len(lines) > 1 and "upgrade" not in lines[1].lower() else f"Mô hình {first_line} (Yêu cầu nâng cấp gói)"
                    is_sel = not is_upgrade and (
                        badge.lower() in curr_btn_text.lower() or await item.locator("svg, [data-icon='check']").count() > 0
                    )

                    discovered_models.append(
                        OptionItem(
                            id=m_id,
                            label=first_line,
                            description=desc,
                            selected=is_sel,
                            disabled=is_upgrade,
                            badge="Upgrade" if is_upgrade else badge,
                            metadata={"pro": is_upgrade, "upgrade": is_upgrade},
                        )
                    )

                if discovered_models:
                    caps.available_models = discovered_models
                    selectable = [dm for dm in discovered_models if not dm.disabled]
                    for dm in selectable:
                        if dm.selected:
                            caps.selected_model_id = dm.id
                            break
                    else:
                        caps.selected_model_id = selectable[0].id if selectable else discovered_models[0].id

                # Now inspect Effort submenu
                effort_item = page.locator("[role='menuitem']:has-text('Effort')")
                if await effort_item.count() > 0 and await effort_item.first.is_visible():
                    await effort_item.first.click(timeout=3000)
                    await asyncio.sleep(0.8)

                    sub_radios = page.locator("[role='menuitemradio']")
                    sub_cnt = await sub_radios.count()
                    discovered_efforts: list[OptionItem] = []
                    seen_e: set[str] = set()

                    for si in range(sub_cnt):
                        sub_el = sub_radios.nth(si)
                        if not await sub_el.is_visible(timeout=100):
                            continue
                        sub_t = (await sub_el.inner_text()).strip()
                        sub_lines = [l.strip() for l in sub_t.split("\n") if l.strip()]
                        if not sub_lines:
                            continue
                        e_name = sub_lines[0]
                        e_lower = e_name.lower()

                        e_id = None
                        e_badge = None
                        e_desc = ""
                        if "low" in e_lower:
                            e_id = "low"
                            e_badge = "Low"
                            e_desc = "Thấp - Phản hồi nhanh & tiết kiệm giới hạn tin nhắn"
                        elif "medium" in e_lower:
                            e_id = "medium"
                            e_badge = "Med"
                            e_desc = "Trung bình - Khuyên dùng, cân bằng độ sâu suy luận"
                        elif "high" in e_lower:
                            e_id = "high"
                            e_badge = "High"
                            e_desc = "Cao - Phân tích đa bước kỹ lưỡng cho bài toán phức tạp"
                        elif "extra" in e_lower:
                            e_id = "extra"
                            e_badge = "Extra"
                            e_desc = "Rất cao - Suy luận chuyên sâu cho nghiên cứu phức tạp"
                        elif "max" in e_lower:
                            e_id = "max"
                            e_badge = "Max"
                            e_desc = "Tối đa - 8x hoặc nhiều hơn mức sử dụng giới hạn"

                        if not e_id or e_id in seen_e:
                            continue
                        seen_e.add(e_id)

                        is_e_sel = e_badge.lower() in curr_btn_text.lower() or (
                            await sub_el.locator("svg, [data-icon='check']").count() > 0
                        )

                        discovered_efforts.append(
                            OptionItem(
                                id=e_id,
                                label=e_name,
                                description=e_desc,
                                selected=is_e_sel,
                                badge=e_badge,
                            )
                        )

                    if discovered_efforts:
                        caps.thinking_levels = discovered_efforts
                        for de in discovered_efforts:
                            if de.selected:
                                caps.selected_thinking_level_id = de.id
                                break
                        else:
                            caps.selected_thinking_level_id = discovered_efforts[0].id

                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
            except Exception as exc:
                logger.warning("claude_dom_inspect_failed", error=str(exc))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass

        caps.is_live_dom = True
        logger.info(
            "claude_dom_inspected_successfully",
            models_count=len(caps.available_models),
            selected_model=caps.selected_model_id,
            thinking_levels_count=len(caps.thinking_levels),
            selected_thinking=caps.selected_thinking_level_id,
        )
        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Apply target model and thinking effort to Claude's web interface."""
        target_model = (config.model_id or "").lower().strip()
        target_thinking = (config.thinking_level_id or "").lower().strip()
        mode_val = (config.mode_id or "").lower().strip()

        # Handle backward-compatible string modes
        if mode_val in {"deep", "deep_research", "research", "thinking"}:
            if not target_thinking:
                target_thinking = "high"
            if not target_model:
                target_model = "claude-sonnet-5.5"

        logger.info(
            "claude_applying_selection",
            target_model=target_model,
            target_thinking=target_thinking,
        )

        try:
            model_btn = await self._find_model_button(page)
            if model_btn is None:
                logger.warning("claude_model_button_not_found_skipping_selection")
                return

            curr_text = (await model_btn.inner_text()).strip().lower()

            # 1. Switch Model if needed
            need_model_switch = False
            model_keyword = None
            if "sonnet" in target_model:
                model_keyword = "Sonnet"
                if "sonnet" not in curr_text:
                    need_model_switch = True
            elif "haiku" in target_model:
                model_keyword = "Haiku"
                if "haiku" not in curr_text:
                    need_model_switch = True
            elif "opus" in target_model:
                model_keyword = "Opus"
                if "opus" not in curr_text:
                    need_model_switch = True
            elif "fable" in target_model:
                model_keyword = "Fable"
                if "fable" not in curr_text:
                    need_model_switch = True

            if need_model_switch and model_keyword:
                await model_btn.click(timeout=3000)
                await asyncio.sleep(0.8)
                m_opt = page.locator("[role='menuitemradio'], [role='menuitem']").filter(has_text=model_keyword)
                if await m_opt.count() > 0:
                    await m_opt.first.click(timeout=3000)
                    logger.info("claude_model_switched", target=model_keyword)
                    await asyncio.sleep(1.0)
                else:
                    await page.keyboard.press("Escape")

            # Refresh button text
            curr_text = (await model_btn.inner_text()).strip().lower()

            # 2. Switch Thinking Effort if needed
            need_effort_switch = False
            effort_keyword = None
            if target_thinking in {"low", "fast"}:
                effort_keyword = "Low"
                if "low" not in curr_text:
                    need_effort_switch = True
            elif target_thinking in {"medium", "med", "auto", "default"}:
                effort_keyword = "Medium"
                if "medium" not in curr_text:
                    need_effort_switch = True
            elif target_thinking in {"high", "deep"}:
                effort_keyword = "High"
                if "high" not in curr_text:
                    need_effort_switch = True
            elif target_thinking in {"extra"}:
                effort_keyword = "Extra"
                if "extra" not in curr_text:
                    need_effort_switch = True
            elif target_thinking in {"max"}:
                effort_keyword = "Max"
                if "max" not in curr_text:
                    need_effort_switch = True

            if need_effort_switch and effort_keyword:
                await model_btn.click(timeout=3000)
                await asyncio.sleep(0.8)
                effort_item = page.locator("[role='menuitem']:has-text('Effort')")
                if await effort_item.count() > 0:
                    await effort_item.first.click(timeout=3000)
                    await asyncio.sleep(0.8)
                    e_opt = page.locator("[role='menuitemradio']").filter(has_text=effort_keyword)
                    if await e_opt.count() > 0:
                        await e_opt.first.click(timeout=3000)
                        logger.info("claude_effort_switched", target=effort_keyword)
                        await asyncio.sleep(1.0)
                    else:
                        await page.keyboard.press("Escape")
                else:
                    await page.keyboard.press("Escape")
        except Exception as exc:
            logger.warning("claude_apply_selection_failed", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
