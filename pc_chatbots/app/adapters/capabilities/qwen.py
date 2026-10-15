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


class QwenCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Alibaba Qwen (chat.qwen.ai / chat.qwenlm.ai) DOM option discovery,
    configuration, and defaults.

    Supports:
    - Model dropdown: Qwen3.8-Max, Qwen3.7-Plus, Qwen3.8-Omni-Flash.
    - Thinking Effort dropdown: Auto (Tự động cân bằng), Thinking (Suy luận sâu), Fast (Phản hồi nhanh).
    - File & Image uploads.
    - Voice STT microphone.
    - Clean manual combinations without a synthetic Mode dropdown.
    """

    @property
    def provider_name(self) -> str:
        return "qwen"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Alibaba Qwen."""
        models = [
            OptionItem(
                id="qwen-3.8-max",
                label="Qwen3.8-Max (Flagship)",
                description="Mô hình cờ đầu thế hệ mới nhất mang lại hiệu năng suy luận và logic vượt trội.",
                selected=True,
                badge="Max",
                metadata={"reasoning": True, "multimodal": True},
            ),
            OptionItem(
                id="qwen-3.7-plus",
                label="Qwen3.7-Plus (High Performance)",
                description="Mô hình hiệu năng cao cân bằng hoàn hảo giữa tốc độ và khả năng xử lý đa phương tiện.",
                selected=False,
                badge="Plus",
                metadata={"speed": "fast", "multimodal": True},
            ),
            OptionItem(
                id="qwen-3.8-omni-flash",
                label="Qwen3.8-Omni-Flash (Multimodal)",
                description="Mô hình đa phương tiện tự nhiên hỗ trợ văn bản, hình ảnh, âm thanh và nghe nhìn tốc độ cao.",
                selected=False,
                badge="Omni",
                metadata={"speed": "fast", "multimodal": True, "omni": True},
            ),
        ]

        thinking_levels = [
            OptionItem(
                id="auto",
                label="Auto (Tự động cân bằng)",
                description="Qwen tự động điều chỉnh mức độ suy luận phù hợp với độ phức tạp của câu hỏi.",
                selected=True,
                badge="Auto",
            ),
            OptionItem(
                id="thinking",
                label="Thinking (Suy luận sâu đa bước)",
                description="Kích hoạt chuỗi tư duy mở rộng (Chain of Thought) để giải bài toán phức tạp và lập luận chuyên sâu.",
                selected=False,
                badge="Think",
            ),
            OptionItem(
                id="fast",
                label="Fast (Phản hồi nhanh)",
                description="Bỏ qua tư duy đa bước, ưu tiên thời gian phản hồi nhanh nhất.",
                selected=False,
                badge="Fast",
            ),
        ]

        modes: list[OptionItem] = []

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
            provider="qwen",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=models,
            selected_model_id="qwen-3.8-max",
            thinking_levels=thinking_levels,
            selected_thinking_level_id="auto",
            modes=modes,
            selected_mode_id=None,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def _find_model_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate the Qwen model dropdown trigger button with polling."""
        import time

        candidates = [
            "div.wms-trigger",
            "[class*='mode-select'] div.wms-trigger",
            "button:has-text('Qwen3.')",
            "div:has-text('Qwen3.')",
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

    async def _find_thinking_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate the Qwen thinking effort dropdown button."""
        import time

        candidates = [
            ".qwen-thinking-selector .qwen-chat-v2-dropdown-menu-select",
            ".qwen-thinking-selector",
            "[class*='thinking-selector']",
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
        """Inspect Qwen's live web DOM to extract active and available models & thinking levels."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        caps.modes = []
        caps.selected_mode_id = None

        # Detect account type
        try:
            body_text = await page.evaluate("() => document.body.innerText || ''")
            if "Upgrade" in body_text or "Free" in body_text:
                caps.account_type = "free"
            elif "Pro" in body_text or "VIP" in body_text:
                caps.account_type = "pro"
        except Exception:
            pass

        # 1. Model Inspection
        model_btn = await self._find_model_button(page)
        if model_btn is not None:
            try:
                curr_btn_text = (await model_btn.inner_text()).strip()
                logger.info("qwen_inspect_model_button_found", text=curr_btn_text)
                await model_btn.click(timeout=3000)
                await asyncio.sleep(0.8)

                dropdown = page.locator(".ant-dropdown, [class*='dropdown'], [class*='popover']")
                if await dropdown.count() > 0:
                    items = dropdown.locator("[class*='option'], [class*='item'], div")
                    cnt = await items.count()
                    discovered: list[OptionItem] = []
                    seen_ids: set[str] = set()

                    for i in range(cnt):
                        item = items.nth(i)
                        if not await item.is_visible(timeout=100):
                            continue
                        t = (await item.inner_text()).strip()
                        lines = [l.strip() for l in t.split("\n") if l.strip()]
                        if not lines:
                            continue
                        name = lines[0]
                        desc = lines[1] if len(lines) > 1 else ""

                        if "3.8-max" in name.lower() or ("3.8" in name.lower() and "max" in name.lower()):
                            m_id = "qwen-3.8-max"
                            badge = "Max"
                        elif "3.7-plus" in name.lower() or ("3.7" in name.lower() and "plus" in name.lower()):
                            m_id = "qwen-3.7-plus"
                            badge = "Plus"
                        elif "omni" in name.lower() or "flash" in name.lower():
                            m_id = "qwen-3.8-omni-flash"
                            badge = "Omni"
                        else:
                            continue

                        if m_id in seen_ids:
                            continue
                        seen_ids.add(m_id)

                        is_selected = m_id in curr_btn_text.lower().replace(".", "") or (
                            await item.locator(".anticon-check, [data-icon='check'], svg").count() > 0
                        )

                        discovered.append(
                            OptionItem(
                                id=m_id,
                                label=name,
                                description=desc or f"Mô hình {name}",
                                selected=is_selected,
                                badge=badge,
                            )
                        )

                    if discovered:
                        caps.available_models = discovered
                        for d in discovered:
                            if d.selected:
                                caps.selected_model_id = d.id
                                break
                        else:
                            caps.selected_model_id = discovered[0].id

                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
            except Exception as m_err:
                logger.warning("qwen_model_inspect_failed", error=str(m_err))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass

        # 2. Thinking Inspection
        think_btn = await self._find_thinking_button(page)
        if think_btn is not None:
            try:
                curr_t_text = (await think_btn.inner_text()).strip()
                logger.info("qwen_inspect_thinking_button_found", text=curr_t_text)
                await think_btn.click(timeout=3000)
                await asyncio.sleep(0.8)

                t_menu = page.locator(".ant-dropdown, [class*='dropdown']").locator(".qwen-chat-v2-dropdown-menu-item, [role='menuitem'], [class*='item']")
                cnt = await t_menu.count()
                discovered_thinking: list[OptionItem] = []
                seen_t: set[str] = set()

                for i in range(cnt):
                    t_item = t_menu.nth(i)
                    if not await t_item.is_visible(timeout=100):
                        continue
                    t_raw = (await t_item.inner_text()).strip()
                    lower_t = t_raw.lower()

                    if "thinking" in lower_t:
                        t_id = "thinking"
                        t_label = "Thinking (Suy luận sâu)"
                        t_badge = "Think"
                        t_desc = "Kích hoạt mô hình suy luận đa bước chuyên sâu (Chain of Thought)"
                    elif "fast" in lower_t:
                        t_id = "fast"
                        t_label = "Fast (Phản hồi nhanh)"
                        t_badge = "Fast"
                        t_desc = "Tối ưu tốc độ phản hồi nhanh, bỏ qua chuỗi suy luận dài"
                    elif "auto" in lower_t:
                        t_id = "auto"
                        t_label = "Auto (Tự động cân bằng)"
                        t_badge = "Auto"
                        t_desc = "Tự động cân bằng giữa suy luận và tốc độ phản hồi"
                    else:
                        continue

                    if t_id in seen_t:
                        continue
                    seen_t.add(t_id)

                    is_sel = t_id in curr_t_text.lower() or (
                        await t_item.locator(".anticon-check, [data-icon='check'], svg").count() > 0
                    )

                    discovered_thinking.append(
                        OptionItem(
                            id=t_id,
                            label=t_label,
                            description=t_desc,
                            selected=is_sel,
                            badge=t_badge,
                        )
                    )

                if discovered_thinking:
                    caps.thinking_levels = discovered_thinking
                    for dt in discovered_thinking:
                        if dt.selected:
                            caps.selected_thinking_level_id = dt.id
                            break
                    else:
                        caps.selected_thinking_level_id = discovered_thinking[0].id

                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
            except Exception as t_err:
                logger.warning("qwen_thinking_inspect_failed", error=str(t_err))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass

        caps.is_live_dom = True
        logger.info(
            "qwen_dom_inspected_successfully",
            models_count=len(caps.available_models),
            selected_model=caps.selected_model_id,
            thinking_levels_count=len(caps.thinking_levels),
            selected_thinking=caps.selected_thinking_level_id,
        )
        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Apply target model and thinking effort to Qwen's web interface."""
        target_model = (config.model_id or "").lower().strip()
        target_thinking = (config.thinking_level_id or "").lower().strip()
        mode_val = (config.mode_id or "").lower().strip()

        if mode_val in {"deep", "deep_research"}:
            if not target_thinking:
                target_thinking = "thinking"
            if not target_model:
                target_model = "qwen-3.8-max"

        logger.info(
            "qwen_applying_selection",
            target_model=target_model,
            target_thinking=target_thinking,
        )

        try:
            # 1. Switch Model
            if target_model and target_model != "auto" and target_model != "default":
                model_btn = await self._find_model_button(page)
                if model_btn is not None:
                    curr_m_text = (await model_btn.inner_text()).strip().lower()
                    need_switch = True
                    if "max" in target_model and "max" in curr_m_text:
                        need_switch = False
                    elif "plus" in target_model and "plus" in curr_m_text:
                        need_switch = False
                    elif "omni" in target_model and "omni" in curr_m_text:
                        need_switch = False

                    if need_switch:
                        await model_btn.click(timeout=3000)
                        await asyncio.sleep(0.8)

                        pattern = "Max" if "max" in target_model else ("Omni" if "omni" in target_model else "Plus")
                        opt = page.locator(".ant-dropdown, [class*='dropdown']").locator("[class*='option'], [class*='item'], div").filter(has_text=pattern)
                        for i in range(await opt.count()):
                            el = opt.nth(i)
                            if await el.is_visible():
                                await el.click(timeout=3000)
                                logger.info("qwen_model_switched", target=pattern)
                                await asyncio.sleep(1.2)
                                break
                        else:
                            await page.keyboard.press("Escape")

            # 2. Switch Thinking
            if target_thinking:
                think_btn = await self._find_thinking_button(page)
                if think_btn is not None:
                    curr_t_text = (await think_btn.inner_text()).strip().lower()
                    need_think_switch = True
                    if target_thinking in {"auto"} and "auto" in curr_t_text:
                        need_think_switch = False
                    elif target_thinking in {"thinking", "deep", "high"} and "thinking" in curr_t_text:
                        need_think_switch = False
                    elif target_thinking in {"fast", "low"} and "fast" in curr_t_text:
                        need_think_switch = False

                    if need_think_switch:
                        await think_btn.click(timeout=3000)
                        await asyncio.sleep(0.8)

                        t_pattern = "Thinking" if target_thinking in {"thinking", "deep", "high"} else ("Fast" if target_thinking in {"fast", "low"} else "Auto")
                        t_opt = page.locator(".ant-dropdown, [class*='dropdown']").locator(".qwen-chat-v2-dropdown-menu-item, [role='menuitem'], [class*='item'], div").filter(has_text=t_pattern)
                        for i in range(await t_opt.count()):
                            t_el = t_opt.nth(i)
                            if await t_el.is_visible():
                                await t_el.click(timeout=3000)
                                logger.info("qwen_thinking_switched", target=t_pattern)
                                await asyncio.sleep(1.2)
                                break
                        else:
                            await page.keyboard.press("Escape")
        except Exception as exc:
            logger.warning("qwen_apply_selection_failed", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
