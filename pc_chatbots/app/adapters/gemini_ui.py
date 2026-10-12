from __future__ import annotations

from typing import Any

import structlog

from app.adapters.base import Source
from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class GeminiUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in gemini.google.com web UI via Playwright (DOM locators only)."""

    name = "gemini"

    async def _extract_sources(self, page: Any) -> list[Source]:
        """Ensure thought toggles or attribution containers are open before extraction."""
        try:
            toggles = page.locator(
                ".thoughts-container button[aria-expanded='false'], "
                ".thoughts-wrapper button[aria-expanded='false'], "
                "button.thoughts-header[aria-expanded='false'], "
                "button.thoughts-toggle[aria-expanded='false'], "
                "button[aria-label*='suy nghĩ' i][aria-expanded='false'], "
                "button[aria-label*='thought' i][aria-expanded='false']"
            )
            count = await toggles.count()
            for idx in range(count):
                toggle = toggles.nth(idx)
                if await toggle.is_visible(timeout=500):
                    await toggle.click(timeout=1000)
        except Exception:  # noqa: BLE001
            pass
        return await super()._extract_sources(page)

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Configure Gemini model (Pro vs Flash) and thinking effort (Cao vs Thấp)."""
        import asyncio
        import time

        cfg_modes = self._cfg.get("mode_selectors") or {}
        dropdown_chain = cfg_modes.get("mode_dropdown")
        if not dropdown_chain:
            return

        # Poll until the mode dropdown button is attached to the DOM (SPA hydration)
        btn: Any | None = None
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            loc, _ = await resolve_locator(page, dropdown_chain)
            if loc is not None:
                btn = loc
                break
            await asyncio.sleep(0.5)

        if btn is None:
            logger.info("gemini_mode_dropdown_not_found")
            return

        is_deep = mode in {"deep", "deep_research"}
        try:
            async def _get_curr_text() -> str:
                curr_inner = await btn.inner_text() or ""
                curr_aria = await btn.get_attribute("aria-label") or ""
                return f"{curr_inner} {curr_aria}".strip().lower()

            async def _ensure_menu_open() -> None:
                expanded = (await btn.get_attribute("aria-expanded")) == "true"
                if not expanded:
                    await btn.click(timeout=4000)
                    await asyncio.sleep(0.4)

            # Helper to wait for a menu item to appear after clicking dropdown
            async def _wait_menu_item(chain: Any, timeout_s: float = 3.0) -> Any | None:
                item_deadline = time.monotonic() + timeout_s
                while time.monotonic() < item_deadline:
                    item_loc, _ = await resolve_locator(page, chain)
                    if item_loc is not None and await item_loc.count() > 0:
                        return item_loc.first
                    await asyncio.sleep(0.2)
                return None

            # 1. Select Pro / Flash if needed
            curr_text = await _get_curr_text()
            target_model = "pro_model" if is_deep else "flash_model"
            need_model_switch = (
                (is_deep and "pro" not in curr_text)
                or (not is_deep and "pro" in curr_text and "flash" not in curr_text)
            )
            if need_model_switch:
                await _ensure_menu_open()
                m_loc = await _wait_menu_item(cfg_modes.get(target_model, []))
                if m_loc is not None:
                    await m_loc.click(timeout=4000)
                    logger.info("gemini_model_selected", target=target_model)
                    await asyncio.sleep(1.0)
                else:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)

            # 2. Select Thinking effort: Cao (High) for deep mode, Thấp (Low) for standard mode
            curr_text = await _get_curr_text()
            if is_deep:
                need_thinking_switch = ("cao" not in curr_text and "high" not in curr_text)
                target_thinking = "thinking_high"
            else:
                need_thinking_switch = (
                    "cao" in curr_text
                    or "high" in curr_text
                    or ("thấp" not in curr_text and "thap" not in curr_text and "low" not in curr_text)
                )
                target_thinking = "thinking_low"

            if need_thinking_switch:
                await _ensure_menu_open()
                t_loc = await _wait_menu_item(cfg_modes.get(target_thinking, []))
                if t_loc is not None:
                    await t_loc.click(timeout=4000)
                    logger.info("gemini_thinking_selected", target=target_thinking)
                    await asyncio.sleep(1.0)
                else:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
        except Exception as exc:  # noqa: BLE001 — mode switch is best-effort
            logger.warning("gemini_mode_click_failed", error=str(exc))
