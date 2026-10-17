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


class MinimaxCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Strategy for MiniMax (agent.minimax.io) DOM discovery and capabilities control.

    Features:
    1. AI models in dropdown nearby send button (model-selector-trigger).
    2. Deep Research toggle: by clicks on '+' button -> Skills -> deep-research.
    """

    @property
    def provider_name(self) -> str:
        return "minimax"

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Baseline options for MiniMax (agent.minimax.io)."""
        return ProviderLiveCapabilities(
            provider="minimax",
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=[
                OptionItem(
                    id="m3",
                    label="M3",
                    description="Mô hình cờ đầu toàn diện của MiniMax, xử lý tác vụ phức tạp",
                    selected=True,
                    disabled=False,
                    badge="M3",
                ),
                OptionItem(
                    id="m3.1-flash",
                    label="M3.1-Flash-Preview",
                    description="Mô hình tốc độ cao, phản hồi tức thì cho tác vụ nhanh",
                    selected=False,
                    disabled=False,
                    badge="Flash",
                ),
                OptionItem(
                    id="m2.7",
                    label="M2.7",
                    description="Mô hình tiêu chuẩn ổn định",
                    selected=False,
                    disabled=False,
                    badge="2.7",
                ),
                OptionItem(
                    id="m2.7-highspeed",
                    label="M2.7 HighSpeed",
                    description="Phiên bản tốc độ cao",
                    selected=False,
                    disabled=False,
                    badge="HighSpeed",
                ),
            ],
            selected_model_id="m3",
            thinking_levels=[],
            selected_thinking_level_id=None,
            modes=[],
            selected_mode_id=None,
            account_type="free",
            supported_data_types=SupportedDataTypes(
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
                ],
            ),
            voice_chat=VoiceChatSupport(
                supported=True,
                mode="backend_stt",
                details="Hỗ trợ ghi âm microphone và chuyển thành văn bản thời gian thực qua backend.",
            ),
            deep_thinking=False,
            web_search=False,
            deep_research=False,
            research_mode=None,
            last_error=None,
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect live DOM on agent.minimax.io:
        1. Discover models from dropdown nearby send button (model-selector-trigger).
        2. Detect if deep-research skill is active.
        """
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        caps.is_live_dom = True

        try:
            # 1. Model trigger nearby send button
            trigger = page.locator("[data-testid='model-selector-trigger'], .mavis-model-selector-trigger")
            if await trigger.count() > 0:
                current_text = (await trigger.first.inner_text(timeout=2000)).strip()
                logger.info("minimax_dom_current_model", text=current_text)

                # Open dropdown to read models
                await trigger.first.click(timeout=3000)
                try:
                    await page.wait_for_selector(".mavis-menu-item, [role='menuitem']", timeout=3000)
                except Exception:
                    await asyncio.sleep(0.8)

                models_data = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll(".mavis-menu-item, [role='menuitem']");
                    const res = [];
                    for (const it of items) {
                        const rect = it.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            const raw = (it.innerText || '').split('\\n')[0].trim();
                            if (raw && !res.some(r => r.label === raw)) {
                                res.push({ label: raw });
                            }
                        }
                    }
                    return res;
                }
                """)
                # Close dropdown
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

                if models_data:
                    discovered_models: list[OptionItem] = []
                    for m in models_data:
                        label = m["label"]
                        lower = label.lower()
                        if "flash" in lower:
                            m_id = "m3.1-flash"
                            badge = "Flash"
                            desc = "Mô hình tốc độ cao, phản hồi tức thì"
                        elif "m3" in lower:
                            m_id = "m3"
                            badge = "M3"
                            desc = "Mô hình cờ đầu toàn diện của MiniMax"
                        elif "highspeed" in lower:
                            m_id = "m2.7-highspeed"
                            badge = "HighSpeed"
                            desc = "Phiên bản tốc độ cao"
                        elif "m2.7" in lower or "2.7" in lower:
                            m_id = "m2.7"
                            badge = "2.7"
                            desc = "Mô hình tiêu chuẩn ổn định"
                        else:
                            m_id = lower.replace(" ", "-")
                            badge = label
                            desc = f"Mô hình {label}"

                        is_active = (
                            current_text.lower() == label.lower()
                            or (m_id == "m3" and current_text.lower() == "m3")
                            or (m_id == "m3.1-flash" and "flash" in current_text.lower())
                        )
                        discovered_models.append(
                            OptionItem(
                                id=m_id,
                                label=label,
                                description=desc,
                                selected=is_active,
                                badge=badge,
                            )
                        )

                    if discovered_models:
                        caps.available_models = discovered_models
                        active = [m for m in discovered_models if m.selected]
                        caps.selected_model_id = active[0].id if active else discovered_models[0].id

            # 2. Check if deep-research skill is currently in the editor
            has_chip = await page.evaluate("""
            () => {
                const chip = document.querySelector(".node-skillCommand, [data-testid='skill-command-chip']");
                return Boolean(chip);
            }
            """)
            caps.deep_research = bool(has_chip)

        except Exception as exc:  # noqa: BLE001
            logger.warning("minimax_inspect_dom_failed", error=str(exc))
            caps.last_error = str(exc)

        return caps

    async def apply_selection(self, page: Any, request: ProviderSelectionRequest) -> None:
        """Apply requested model and Deep Research toggle on live page."""
        # 1. Model switching via dropdown nearby send button
        target_model = (request.model_id or "").strip().lower()
        if target_model:
            trigger = page.locator("[data-testid='model-selector-trigger'], .mavis-model-selector-trigger")
            if await trigger.count() > 0:
                current_text = (await trigger.first.inner_text(timeout=2000)).strip().lower()
                need_switch = True
                if "flash" in target_model and "flash" in current_text:
                    need_switch = False
                elif target_model in {"m3", "pro", "flagship"} and current_text == "m3":
                    need_switch = False
                elif "highspeed" in target_model and "highspeed" in current_text:
                    need_switch = False
                elif "2.7" in target_model and "2.7" in current_text and "highspeed" not in current_text:
                    need_switch = False

                if need_switch:
                    logger.info("minimax_switching_model", target=target_model, current=current_text)
                    try:
                        open_dropdown = page.locator(".ant-dropdown:not(.ant-dropdown-hidden)")
                        if await open_dropdown.count() > 0:
                            await page.keyboard.press("Escape")
                            await asyncio.sleep(0.5)
                    except Exception:
                        pass

                    await trigger.first.click(timeout=3000)
                    try:
                        await page.wait_for_selector(".mavis-menu-item, [role='menuitem']", timeout=3000)
                    except Exception:
                        await asyncio.sleep(0.8)

                    if "flash" in target_model:
                        loc = page.locator(".mavis-menu-item:has-text('Flash'), [role='menuitem']:has-text('Flash')")
                    elif target_model in {"m3", "pro", "flagship"}:
                        loc = page.locator(".mavis-menu-item:has-text('M3'):not(:has-text('Flash')), [role='menuitem']:has-text('M3'):not(:has-text('Flash'))")
                    elif "highspeed" in target_model:
                        loc = page.locator(".mavis-menu-item:has-text('HighSpeed'), [role='menuitem']:has-text('HighSpeed')")
                    elif "2.7" in target_model:
                        loc = page.locator(".mavis-menu-item:has-text('M2.7'):not(:has-text('HighSpeed')), [role='menuitem']:has-text('M2.7'):not(:has-text('HighSpeed'))")
                    else:
                        loc = page.locator(f".mavis-menu-item:has-text('{target_model}'), [role='menuitem']:has-text('{target_model}')")

                    if await loc.count() > 0:
                        await loc.first.click(timeout=3000)
                        logger.info("minimax_model_selected", target=target_model)
                        await asyncio.sleep(0.5)
                    else:
                        await page.keyboard.press("Escape")
                        logger.warning("minimax_target_model_item_not_found", target=target_model)

        # 2. Deep Research toggle:
        # User rule: clicks on '+' button -> Skills -> deep-research to enable it (on), otherwise off by default
        wants_deep = bool(request.deep_research)
        try:
            has_chip = await page.evaluate("""
            () => {
                const chip = document.querySelector(".node-skillCommand, [data-testid='skill-command-chip']");
                return Boolean(chip);
            }
            """)
        except Exception:
            has_chip = False

        if wants_deep and not has_chip:
            logger.info("minimax_enabling_deep_research")
            attach_btn = page.locator("[data-testid='attach-button'], div[aria-label='Add attachment']")
            if await attach_btn.count() > 0:
                await attach_btn.first.click(timeout=3000)
                await asyncio.sleep(0.8)

                skills_item = page.locator(".ant-dropdown:not(.ant-dropdown-hidden) .mavis-menu-item:has-text('Skills')")
                if await skills_item.count() > 0:
                    await skills_item.first.click(timeout=3000)
                    await asyncio.sleep(0.8)

                    deep_btn = page.locator("button.mavis-menu-item:has-text('deep-research'), button:has-text('deep-research')")
                    if await deep_btn.count() > 0:
                        await deep_btn.first.click(timeout=3000)
                        logger.info("minimax_deep_research_enabled")
                        await asyncio.sleep(0.5)
                    else:
                        await page.keyboard.press("Escape")
                        logger.warning("minimax_deep_research_btn_not_found")
                else:
                    await page.keyboard.press("Escape")
                    logger.warning("minimax_skills_item_not_found")
        elif not wants_deep and has_chip:
            logger.info("minimax_disabling_deep_research")
            remove_btn = page.locator("button.rich-text-skill-remove, button[aria-label*='Remove deep-research']")
            if await remove_btn.count() > 0:
                await remove_btn.first.click(timeout=2000)
                logger.info("minimax_deep_research_disabled")
                await asyncio.sleep(0.5)
