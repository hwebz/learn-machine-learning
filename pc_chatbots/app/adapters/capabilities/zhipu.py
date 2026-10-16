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


class ZhipuCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Zhipu AI (GLM / chat.z.ai) DOM option discovery and capabilities.

    Features:
    1. Model selection: Single dropdown in the top-left corner of the chat interface.
    2. Otherwise, no more options (no thinking levels, no mode dropdown, no deep research/thinking toggles).
    """

    @property
    def provider_name(self) -> str:
        return "zhipu"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Zhipu AI (chat.z.ai)."""
        fallback_models = [
            OptionItem(
                id="glm-5.3-flash",
                label="GLM-5.3-Flash",
                description="Lightweight flagship model, premium quality, instant response (Mô hình cờ đầu gọn nhẹ, phản hồi tức thì)",
                selected=True,
                disabled=False,
                badge="Flash",
            ),
            OptionItem(
                id="glm-5.3",
                label="GLM-5.3",
                description="Flagship model, excels at coding and long-horizon tasks (Mô hình cờ đầu, xuất sắc về lập trình & tác vụ phức tạp)",
                selected=False,
                disabled=False,
                badge="Flagship",
            ),
            OptionItem(
                id="glm-5.2",
                label="GLM-5.2",
                description="Previous flagship model (Mô hình cờ đầu thế hệ trước)",
                selected=False,
                disabled=False,
                badge="5.2",
            ),
            OptionItem(
                id="glm-4-plus",
                label="GLM-4-Plus",
                description="Mô hình hiệu năng cao toàn diện cho tác vụ phức tạp",
                selected=False,
                disabled=False,
                badge="Plus",
            ),
            OptionItem(
                id="glm-4-air",
                label="GLM-4-Air",
                description="Cân bằng tốc độ xử lý nhanh và độ chính xác cao",
                selected=False,
                disabled=False,
                badge="Air",
            ),
        ]

        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=50,
            supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".docx", ".xlsx", ".py", ".md"],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và chuyển thành văn bản thời gian thực qua backend.",
        )

        return ProviderLiveCapabilities(
            provider="zhipu",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=fallback_models,
            selected_model_id="glm-5.3-flash",
            thinking_levels=[],
            selected_thinking_level_id=None,
            modes=[],
            selected_mode_id=None,
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
            deep_thinking=False,
            web_search=False,
            deep_research=False,
        )

    async def _find_dropdown_button(self, page: Any, timeout_s: float = 6.0) -> Any | None:
        """Locate the model selector dropdown button on the top-left corner of chat.z.ai."""
        import time

        candidates = [
            "#model-selector-x-preview-l-button",
            "button[id*='model-selector']",
            "div[id*='model-selector']",
            "button[aria-label*='Select a model' i]",
            "button[aria-label*='Select model' i]",
            "button[aria-label*='model' i]",
            "button[data-testid*='model' i]",
            "header button:has-text('GLM')",
            "header button:has-text('Flash')",
            "header button:has-text('Pro')",
            "header button:has-text('Air')",
            "nav button:has-text('GLM')",
            "button:has-text('GLM')",
            "button:has-text('Flash')",
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
                            # Verify if it's placed in the top-left region of the page
                            try:
                                box = await b.bounding_box()
                                if box and box["x"] < 450 and box["y"] < 180:
                                    return b
                            except Exception:
                                pass
                            return b
                except Exception:
                    continue
            await asyncio.sleep(0.3)
        return None

    def _normalize_model_id(self, raw_label: str) -> str:
        """Create a clean lowercase identifier from the model title."""
        s = raw_label.strip().lower()
        if ("5.3" in s and "flash" in s) or "5-3-flash" in s:
            return "glm-5.3-flash"
        if "5.3" in s or "5-3" in s:
            return "glm-5.3"
        if "5.2" in s or "5-2" in s:
            return "glm-5.2"
        if "plus" in s:
            return "glm-4-plus"
        if "air" in s:
            return "glm-4-air"
        if "flash" in s:
            return "glm-5.3-flash"
        if "glm-5" in s or "glm 5" in s:
            return "glm-5.3"
        if "zero" in s:
            return "glm-zero"
        clean = re.sub(r"[^a-z0-9.]+", "-", s).strip("-")
        return clean or "glm-5.3-flash"

    def _derive_badge(self, model_id: str, label: str, has_new_badge: bool = False) -> str:
        """Derive a short badge text for display."""
        if has_new_badge or "flash" in model_id:
            return "Flash"
        if "5.3" in model_id:
            return "Flagship"
        if "5.2" in model_id:
            return "5.2"
        if "plus" in model_id:
            return "Plus"
        if "air" in model_id:
            return "Air"
        if "zero" in model_id:
            return "Zero"
        return "GLM"

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect chat.z.ai DOM to collect available models from the top-left dropdown."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        btn = await self._find_dropdown_button(page, timeout_s=4.0)
        if btn is None:
            logger.info("zhipu_dom_dropdown_button_not_found_using_defaults")
            caps.is_live_dom = False
            return caps

        try:
            btn_text = (await btn.inner_text()).strip()
            logger.info("zhipu_dom_model_btn_found", text=btn_text)

            # Determine currently selected model from trigger text
            current_selected_id = self._normalize_model_id(btn_text)
            caps.selected_model_id = current_selected_id

            # Click dropdown button to reveal model list
            await btn.click(timeout=3000)
            await asyncio.sleep(0.8)

            # Extract dropdown items
            menu_data = await page.evaluate("""() => {
                const candidates = Array.from(document.querySelectorAll(
                    "[role='menuitem'], [role='option'], li, div[class*='item'], div[class*='menu'], button"
                ));
                const visible = candidates.filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 120 && r.height > 25 && r.y > 30;
                });
                return visible.map(el => {
                    const text = (el.innerText || '').trim();
                    const lines = text.split('\\n').map(s => s.trim()).filter(Boolean);
                    const title = lines[0] || text;
                    const desc = lines.slice(1).filter(l => l !== 'NEW' && l !== 'Active' && l !== 'PRO').join(' ');
                    const hasNewBadge = lines.includes('NEW');
                    const ariaSelected = el.getAttribute('aria-selected') === 'true' || el.getAttribute('aria-checked') === 'true';
                    const isSelected = ariaSelected || el.classList.contains('active') || el.classList.contains('selected');
                    const isDisabled = el.getAttribute('aria-disabled') === 'true' || el.classList.contains('disabled');
                    return {
                        title,
                        description: desc,
                        hasNewBadge,
                        isSelected,
                        isDisabled
                    };
                }).filter(item => item.title && (
                    item.title.includes('GLM-5.3') ||
                    item.title.includes('GLM-5.2') ||
                    item.title.includes('GLM-5') ||
                    item.title.includes('GLM-4') ||
                    item.title.includes('GLM') ||
                    item.title.includes('Flash')
                ) && !item.title.includes('ZCode') && !item.title.includes('Visit China'));
            }""")

            if menu_data and len(menu_data) > 0:
                discovered_models: list[OptionItem] = []
                for item in menu_data:
                    m_id = self._normalize_model_id(item["title"])
                    # Avoid duplicates
                    if any(existing.id == m_id for existing in discovered_models):
                        continue
                    is_cur_selected = item["isSelected"] or (m_id == current_selected_id)
                    badge = self._derive_badge(m_id, item["title"], item.get("hasNewBadge", False))
                    discovered_models.append(
                        OptionItem(
                            id=m_id,
                            label=item["title"],
                            description=item["description"] or f"Mô hình {item['title']}",
                            selected=is_cur_selected,
                            disabled=item["isDisabled"],
                            badge=badge,
                        )
                    )

                if discovered_models:
                    caps.available_models = discovered_models
                    # Pick selected model
                    selected_m = next((m for m in discovered_models if m.selected), discovered_models[0])
                    caps.selected_model_id = selected_m.id
                    caps.is_live_dom = True
                    logger.info("zhipu_dom_models_discovered", count=len(discovered_models), selected=caps.selected_model_id)

            # Safely close dropdown popup
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("zhipu_inspect_dom_failed", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

        # Strict adherence: no more options
        caps.thinking_levels = []
        caps.selected_thinking_level_id = None
        caps.modes = []
        caps.selected_mode_id = None
        caps.deep_thinking = False
        caps.deep_research = False
        caps.web_search = False

        return caps

    async def apply_selection(self, page: Any, config: Any) -> None:
        """Apply selected model in the top-left dropdown on chat.z.ai."""
        if not isinstance(config, ProviderSelectionRequest):
            if isinstance(config, dict):
                config = ProviderSelectionRequest.model_validate(config)
            else:
                config = ProviderSelectionRequest()

        target_model = (config.model_id or "").strip().lower()
        if not target_model:
            return

        btn = await self._find_dropdown_button(page, timeout_s=5.0)
        if btn is None:
            logger.warning("zhipu_model_dropdown_button_not_found")
            return

        try:
            curr_text = (await btn.inner_text()).strip().lower()
            curr_id = self._normalize_model_id(curr_text)
            if curr_id == target_model:
                logger.info("zhipu_model_already_active", target=target_model, current=curr_text)
                return

            logger.info("zhipu_switching_model", target=target_model, current=curr_text)
            await btn.click(timeout=3000)
            await asyncio.sleep(0.6)

            # Specific locator strategy based on target model
            clicked = False
            if "flash" in target_model:
                loc = page.locator("button:has-text('GLM-5.3-Flash'), [role='menuitem']:has-text('GLM-5.3-Flash'), div:has-text('GLM-5.3-Flash')").last
                if await loc.count() > 0 and await loc.is_visible(timeout=800):
                    await loc.click(timeout=3000)
                    clicked = True
            elif "5.3" in target_model:
                # Match GLM-5.3 but NOT Flash
                loc = page.locator("button:has-text('GLM-5.3'):not(:has-text('Flash'))").first
                if await loc.count() > 0 and await loc.is_visible(timeout=800):
                    await loc.click(timeout=3000)
                    clicked = True
            elif "5.2" in target_model:
                loc = page.locator("button:has-text('GLM-5.2'), [role='menuitem']:has-text('GLM-5.2')").first
                if await loc.count() > 0 and await loc.is_visible(timeout=800):
                    await loc.click(timeout=3000)
                    clicked = True
            elif "plus" in target_model:
                loc = page.locator("button:has-text('Plus'), [role='menuitem']:has-text('Plus')").first
                if await loc.count() > 0 and await loc.is_visible(timeout=800):
                    await loc.click(timeout=3000)
                    clicked = True
            elif "air" in target_model:
                loc = page.locator("button:has-text('Air'), [role='menuitem']:has-text('Air')").first
                if await loc.count() > 0 and await loc.is_visible(timeout=800):
                    await loc.click(timeout=3000)
                    clicked = True

            # General fallback if not clicked yet
            if not clicked:
                for kw in [target_model, target_model.replace("glm-", "GLM-")]:
                    item_loc = page.locator(f"button:has-text('{kw}'), [role='menuitem']:has-text('{kw}')").first
                    if await item_loc.count() > 0 and await item_loc.is_visible(timeout=500):
                        await item_loc.click(timeout=3000)
                        clicked = True
                        break

            if clicked:
                logger.info("zhipu_model_selected_successfully", target=target_model)
                await asyncio.sleep(0.5)
            else:
                logger.warning("zhipu_target_model_item_not_found", target=target_model)
                await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001
            logger.warning("zhipu_apply_selection_failed", error=str(exc))
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
