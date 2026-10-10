from __future__ import annotations

from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class QwenUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.qwen.ai web UI via Playwright (DOM locators only)."""

    name = "qwen"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Qwen model (Max vs Plus) and thinking dropdown (Thinking vs Auto)."""
        import asyncio

        cfg_modes = self._cfg.get("mode_selectors") or {}
        is_deep = mode in {"deep", "deep_research"}
        try:
            # 1. Top-left model selector (Max for deep, Plus for standard)
            model_btn_chain = cfg_modes.get("model_dropdown")
            if model_btn_chain:
                model_btn, _ = await resolve_locator(page, model_btn_chain)
                if model_btn is not None:
                    curr_m_text = (await model_btn.inner_text()).strip().lower()
                    target_model = "max_model" if is_deep else "plus_model"
                    need_switch = (is_deep and "max" not in curr_m_text) or \
                                  (not is_deep and "plus" not in curr_m_text and "max" in curr_m_text)
                    if need_switch:
                        await model_btn.click(timeout=4000)
                        await asyncio.sleep(0.8)
                        m_item, _ = await resolve_locator(page, cfg_modes.get(target_model, []))
                        if m_item is not None:
                            await m_item.click(timeout=4000)
                            logger.info("qwen_model_selected", target=target_model)
                            await asyncio.sleep(1.0)
                        else:
                            await page.keyboard.press("Escape")

            # 2. Bottom-right thinking dropdown (Thinking for deep, Auto for standard)
            think_btn_chain = cfg_modes.get("thinking_dropdown")
            if think_btn_chain:
                think_btn, _ = await resolve_locator(page, think_btn_chain)
                if think_btn is not None:
                    curr_t_text = (await think_btn.inner_text()).strip().lower()
                    target_think = "thinking_option" if is_deep else "auto_option"
                    need_think_switch = (is_deep and "thinking" not in curr_t_text) or \
                                        (not is_deep and "auto" not in curr_t_text and "thinking" in curr_t_text)
                    if need_think_switch:
                        await think_btn.click(timeout=4000)
                        await asyncio.sleep(0.8)
                        t_item, _ = await resolve_locator(page, cfg_modes.get(target_think, []))
                        if t_item is not None:
                            await t_item.click(timeout=4000)
                            logger.info("qwen_thinking_selected", target=target_think)
                            await asyncio.sleep(1.0)
                        else:
                            await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001 — mode switch is best-effort
            logger.warning("qwen_mode_click_failed", error=str(exc))
