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


class KimiCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for Moonshot Kimi (kimi.ai) DOM option discovery and capabilities.

    Features:
    1. Models in dropdown nearby Send button:
       - Instant (Fast chat, quick replies) - default
       - K3 (Chat & Agent, flagship all-rounder)
       - K2.8 (Preview · Well-rounded and efficient)
    2. Thinking effort options inside that dropdown:
       - Standard (Tiêu chuẩn)
       - High (Cao / Chuyên sâu) - default
    3. Deep Research available at the list of buttons below the textbox area:
       - Toggle on/off
    """

    @property
    def provider_name(self) -> str:
        return "kimi"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for Kimi AI."""
        fallback_models = [
            OptionItem(
                id="instant",
                label="Instant",
                description="Fast chat, quick replies (Phản hồi nhanh)",
                selected=True,
                disabled=False,
                badge="Instant",
            ),
            OptionItem(
                id="k3",
                label="K3",
                description="Chat & Agent, flagship all-rounder (Toàn diện, suy luận mạnh)",
                selected=False,
                disabled=False,
                badge="K3",
            ),
            OptionItem(
                id="k2.8",
                label="K2.8",
                description="Preview · Well-rounded and efficient for everyday tasks",
                selected=False,
                disabled=False,
                badge="Preview",
            ),
        ]

        fallback_thinking_levels = [
            OptionItem(
                id="standard",
                label="Standard",
                description="Suy luận tiêu chuẩn, phản hồi cân bằng",
                selected=False,
                disabled=False,
                badge="Standard",
            ),
            OptionItem(
                id="high",
                label="High",
                description="Suy luận chuyên sâu cao nhất",
                selected=True,
                disabled=False,
                badge="High",
            ),
        ]

        data_types = SupportedDataTypes(
            text=True,
            image=True,
            file=True,
            audio=False,
            video=False,
            max_file_size_mb=100,
            supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json", ".docx", ".xlsx", ".pptx", ".md", ".py"],
        )

        voice = VoiceChatSupport(
            supported=True,
            mode="backend_stt",
            details="Hỗ trợ ghi âm microphone và nhận diện văn bản qua backend.",
        )

        return ProviderLiveCapabilities(
            provider="kimi",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=fallback_models,
            selected_model_id="instant",
            thinking_levels=fallback_thinking_levels,
            selected_thinking_level_id="high",
            modes=[],
            selected_mode_id=None,
            deep_thinking=True,
            web_search=True,
            deep_research=False,
            research_mode="normal",
            account_type="free",
            supported_data_types=data_types,
            voice_chat=voice,
        )

    async def _find_model_trigger(self, page: Any) -> Any | None:
        """Find the model dropdown trigger nearby the Send button."""
        candidates = [
            page.locator(".current-model, [data-testid='model-select-trigger']").first,
            page.locator("div, button").filter(has_text=re.compile(r"(Instant|K3|K2\.8)")).filter(has_text=re.compile(r"(High|Standard)")).last,
        ]
        for loc in candidates:
            try:
                if await loc.count() > 0 and await loc.is_visible(timeout=1000):
                    return loc
            except Exception:
                continue
        return None

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect the live kimi.ai DOM to collect models, thinking effort, and deep research status."""
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)

        # 1. Check Deep Research state via URL or input badge
        is_dr = "deep-research" in page.url.lower()
        if not is_dr:
            try:
                dr_badge = page.locator(".publisher-shortcut__link:has-text('Deep Research'), span:has-text('Deep Research')").first
                if await dr_badge.count() > 0 and await dr_badge.is_visible(timeout=500):
                    # Check if it is inside the composer/input
                    inside_composer = await page.locator(".editor, .chat-input, .chat-box").filter(has_text="Deep Research").count()
                    if inside_composer > 0:
                        is_dr = True
            except Exception:
                pass
        caps.deep_research = is_dr

        # 2. Inspect Model Trigger & Dropdown
        trigger = await self._find_model_trigger(page)
        if trigger is not None:
            try:
                cur_text = (await trigger.inner_text()).strip()
                if "k3" in cur_text.lower():
                    caps.selected_model_id = "k3"
                elif "k2.8" in cur_text.lower() or "k2" in cur_text.lower():
                    caps.selected_model_id = "k2.8"
                elif "instant" in cur_text.lower():
                    caps.selected_model_id = "instant"

                if "standard" in cur_text.lower():
                    caps.selected_thinking_level_id = "standard"
                elif "high" in cur_text.lower():
                    caps.selected_thinking_level_id = "high"

                # Click trigger to inspect DOM options
                await trigger.click(timeout=2000)
                await asyncio.sleep(0.6)

                # Collect model items
                model_items = await page.evaluate("""() => {
                    const els = Array.from(document.querySelectorAll("[role='menuitem'], div, button"));
                    return els
                        .filter(el => {
                            const t = (el.innerText || '').trim();
                            return (t.includes('Chat & Agent') || t.includes('flagship') || t.includes('Preview · Well-rounded') || t.includes('Fast chat')) && el.getBoundingClientRect().width > 0;
                        })
                        .map(el => el.innerText.trim());
                }""")

                if model_items:
                    caps.is_live_dom = True

                # Inspect Thinking Effort submenu
                think_row = page.locator(":is(div, span, button):text-matches('Thinking effort', 'i')").last
                if await think_row.count() > 0 and await think_row.is_visible(timeout=1000):
                    await think_row.hover()
                    await asyncio.sleep(0.3)
                    await think_row.click()
                    await asyncio.sleep(0.5)

                    effort_options = await page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll("button.effort-option, button"));
                        return btns
                            .filter(b => {
                                const t = (b.innerText || '').trim();
                                return (t === 'Standard' || t === 'High') && b.getBoundingClientRect().width > 0;
                            })
                            .map(b => b.innerText.trim());
                    }""")
                    if "Standard" in effort_options and "High" in effort_options:
                        caps.thinking_levels = [
                            OptionItem(
                                id="standard",
                                label="Standard",
                                description="Suy luận tiêu chuẩn, phản hồi cân bằng",
                                selected=(caps.selected_thinking_level_id == "standard"),
                                disabled=False,
                                badge="Standard",
                            ),
                            OptionItem(
                                id="high",
                                label="High",
                                description="Suy luận chuyên sâu cao nhất",
                                selected=(caps.selected_thinking_level_id == "high"),
                                disabled=False,
                                badge="High",
                            ),
                        ]

                await page.keyboard.press("Escape")
                await asyncio.sleep(0.2)
                await page.keyboard.press("Escape")
            except Exception as exc:
                logger.warning("kimi_inspect_dom_failed", error=str(exc))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass

        # If deep research is active:
        # 1. Disable Instant model and default to k3
        # 2. Lock reasoning effort to Auto and disable changing reasoning
        if caps.deep_research:
            for m in caps.available_models:
                if m.id == "instant":
                    m.disabled = True
                    m.badge = "Không hỗ trợ DR"
            if caps.selected_model_id == "instant":
                caps.selected_model_id = "k3"
            caps.selected_thinking_level_id = "auto"
            caps.thinking_levels = [
                OptionItem(
                    id="auto",
                    label="Auto (Tự động)",
                    description="Deep Research tự động điều chỉnh mức độ suy luận (Khóa bởi Deep Research)",
                    selected=True,
                    disabled=True,
                    badge="Auto",
                )
            ]

        # Update selected flags in lists
        for m in caps.available_models:
            m.selected = (m.id == caps.selected_model_id)
        for t in caps.thinking_levels:
            t.selected = (t.id == caps.selected_thinking_level_id)

        caps.modes = []
        caps.selected_mode_id = None
        caps.web_search = True
        return caps

    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Apply selected model, thinking level, web search, deep research, and research mode on kimi.ai."""
        logger.info("kimi_apply_selection_started", config=config.model_dump())

        # 1. Apply Deep Research toggle if specified
        target_dr = config.deep_research
        if target_dr is not None:
            curr_dr = "deep-research" in page.url.lower()
            if target_dr and not curr_dr:
                logger.info("kimi_activating_deep_research")
                dr_link = page.locator("a[href*='deep-research'], .publisher-shortcut__link:has-text('Deep Research')").first
                if await dr_link.count() > 0 and await dr_link.is_visible(timeout=2000):
                    await dr_link.click(timeout=3000)
                    await asyncio.sleep(1.5)
                else:
                    await page.goto("https://www.kimi.ai/deep-research", wait_until="domcontentloaded")
                    await asyncio.sleep(1.5)
            elif not target_dr and curr_dr:
                logger.info("kimi_deactivating_deep_research")
                new_chat = page.locator("a[href='/'], a[aria-label='New chat'], [data-testid='sidebar-new-chat']").first
                if await new_chat.count() > 0 and await new_chat.is_visible(timeout=2000):
                    await new_chat.click(timeout=3000)
                    await asyncio.sleep(1.5)
                else:
                    await page.goto("https://www.kimi.ai/", wait_until="domcontentloaded")
                    await asyncio.sleep(1.5)

        effective_dr = target_dr if target_dr is not None else ("deep-research" in page.url.lower())

        # 2. Apply Research Mode (Advanced vs Normal) when Deep Research is active
        if effective_dr and config.research_mode:
            target_rm = config.research_mode.lower()
            mode_label = "Advanced" if target_rm == "advanced" else "Normal"
            logger.info("kimi_applying_research_mode", mode=mode_label)
            try:
                # First check if the mode button is directly visible
                mode_btn = page.locator(f"button:has-text('{mode_label}'), [role='button']:has-text('{mode_label}')").first
                if await mode_btn.count() > 0 and await mode_btn.is_visible(timeout=1000):
                    await mode_btn.click(timeout=2000)
                    await asyncio.sleep(0.5)
                else:
                    # Open '+' menu nearby textbox area
                    plus_btn = page.locator("button:has-text('+'), [data-testid*='plus'], [data-testid*='attachment'], [aria-label*='Add'], [aria-label*='plus']").first
                    if await plus_btn.count() > 0 and await plus_btn.is_visible(timeout=1000):
                        await plus_btn.click(timeout=1500)
                        await asyncio.sleep(0.5)
                        opt_btn = page.locator(f":is(button, div, span):has-text('{mode_label}')").first
                        if await opt_btn.count() > 0 and await opt_btn.is_visible(timeout=1500):
                            await opt_btn.click(timeout=2000)
                            await asyncio.sleep(0.5)
                        else:
                            await page.keyboard.press("Escape")
            except Exception as exc:
                logger.warning("kimi_research_mode_toggle_failed", error=str(exc))
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass

        # 3. Apply Web Search Toggle if specified
        if config.web_search is not None:
            logger.info("kimi_applying_web_search", web_search=config.web_search)
            try:
                # Look for web search toggle button or in '+' menu
                search_btn = page.locator("button:has-text('Web search'), button:has-text('Search'), [data-testid*='search']").first
                if await search_btn.count() > 0 and await search_btn.is_visible(timeout=1000):
                    is_active = "active" in (await search_btn.get_attribute("class") or "").lower() or (await search_btn.get_attribute("aria-pressed") or "") == "true"
                    if is_active != config.web_search:
                        await search_btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
            except Exception as exc:
                logger.warning("kimi_web_search_toggle_failed", error=str(exc))

        # 4. Apply Model Selection (Deep Research does not allow Instant)
        target_model = (config.model_id or "").lower()
        if effective_dr and (not target_model or target_model in {"instant", "default"}):
            logger.info("kimi_deep_research_disallows_instant_fallback_to_k3")
            target_model = "k3"

        if target_model:
            trigger = await self._find_model_trigger(page)
            if trigger is not None:
                cur_text = (await trigger.inner_text()).strip().lower()
                need_switch_model = False
                if target_model in {"k3", "k-3"} and "k3" not in cur_text:
                    need_switch_model = True
                elif target_model in {"k2.8", "k2", "k2-8"} and "k2" not in cur_text:
                    need_switch_model = True
                elif target_model in {"instant", "default"} and "instant" not in cur_text:
                    need_switch_model = True

                if need_switch_model:
                    try:
                        await trigger.click(timeout=2000)
                        await asyncio.sleep(0.5)

                        if target_model in {"k3", "k-3"}:
                            btn = page.locator("div, button, [role='menuitem']").filter(has_text="K3").filter(has_text="Chat & Agent").last
                            if await btn.count() == 0:
                                btn = page.locator("text='K3'").first
                        elif target_model in {"k2.8", "k2", "k2-8"}:
                            btn = page.locator("div, button, [role='menuitem']").filter(has_text="K2.8").last
                            if await btn.count() == 0:
                                btn = page.locator("text='K2.8'").first
                        else:
                            btn = page.locator("div, button, [role='menuitem']").filter(has_text="Instant").filter(has_text="Fast chat").last
                            if await btn.count() == 0:
                                btn = page.locator("text='Instant'").first

                        if await btn.count() > 0 and await btn.is_visible(timeout=2000):
                            await btn.click(timeout=2000)
                            logger.info("kimi_model_selected", target=target_model)
                            await asyncio.sleep(0.8)
                        else:
                            await page.keyboard.press("Escape")
                    except Exception as exc:
                        logger.warning("kimi_model_switch_failed", error=str(exc))
                        try:
                            await page.keyboard.press("Escape")
                        except Exception:
                            pass

        # 5. Apply Thinking Effort Selection (Deep Research does NOT allow changing reasoning; locks to Auto)
        if not effective_dr:
            target_effort = (config.thinking_level_id or "").lower()
            if target_effort in {"standard", "high", "low"}:
                effort_label = "Standard" if target_effort in {"standard", "low"} else "High"
                trigger = await self._find_model_trigger(page)
                if trigger is not None:
                    cur_text = (await trigger.inner_text()).strip()
                    if effort_label.lower() not in cur_text.lower():
                        try:
                            await trigger.click(timeout=2000)
                            await asyncio.sleep(0.5)

                            think_row = page.locator(":is(div, span, button):text-matches('Thinking effort', 'i')").last
                            if await think_row.count() > 0 and await think_row.is_visible(timeout=2000):
                                await think_row.hover()
                                await asyncio.sleep(0.3)
                                await think_row.click()
                                await asyncio.sleep(0.5)

                                opt_btn = page.locator(f"button.effort-option:has-text('{effort_label}'), button:has-text('{effort_label}')").first
                                if await opt_btn.count() > 0 and await opt_btn.is_visible(timeout=2000):
                                    await opt_btn.click(timeout=2000)
                                    logger.info("kimi_thinking_effort_selected", effort=effort_label)
                                    await asyncio.sleep(0.8)
                                else:
                                    await page.keyboard.press("Escape")
                            else:
                                await page.keyboard.press("Escape")
                        except Exception as exc:
                            logger.warning("kimi_thinking_effort_switch_failed", error=str(exc))
                            try:
                                await page.keyboard.press("Escape")
                            except Exception:
                                pass
        else:
            logger.info("kimi_deep_research_active_skipping_thinking_effort_change")

        logger.info("kimi_apply_selection_completed")
