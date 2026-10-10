from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)

from app.browser.locators import resolve_locator

# The "Pick an account" screen lists previously used Microsoft accounts as
# ".row.tile" listitems, each with an inner "div.table[role='button']" clickable
# tile; the last one is always "#otherTile" ("Use another account") — skip it.
_ACCOUNT_TILE = "div.row.tile div.table[role='button']:not(#otherTile)"


class CopilotUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in Microsoft 365 Copilot web UI via Playwright (DOM locators only)."""

    name = "copilot"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Copilot mode between Auto and Think deeper."""
        is_deep = mode in {"deep", "deep_research"}
        cfg_modes = self._cfg.get("mode_selectors") or {}
        dropdown_chain = cfg_modes.get("mode_dropdown")
        if not dropdown_chain:
            return
        locator, _ = await resolve_locator(page, dropdown_chain)
        if locator is None:
            logger.info("copilot_mode_dropdown_not_found")
            return
        try:
            curr_text = (await locator.inner_text()).strip().lower()
            if is_deep and "think deeper" in curr_text:
                logger.info("copilot_mode_already_deep")
                return
            if not is_deep and "auto" in curr_text:
                logger.info("copilot_mode_already_auto")
                return

            target_key = "deep_mode" if is_deep else "standard_mode"
            await locator.click(timeout=4000)
            await asyncio.sleep(0.8)
            target_chain = cfg_modes.get(target_key)
            if target_chain:
                item_loc, _ = await resolve_locator(page, target_chain)
                if item_loc is not None:
                    await item_loc.click(timeout=4000)
                    logger.info("copilot_mode_selected", mode=mode, target=target_key)
                    await asyncio.sleep(1.0)
                else:
                    await page.keyboard.press("Escape")
        except Exception as exc:  # noqa: BLE001
            logger.warning("copilot_mode_switch_failed", error=str(exc))

    async def attempt_login_recovery(self, page: Any) -> bool:
        """Copilot's OAuth cookie expires after a while and the site bounces to
        login.microsoftonline.com's "Pick an account" screen. Click the first
        remembered account tile to go straight back into chat (no password)."""
        try:
            tile = page.locator(_ACCOUNT_TILE).first
            await tile.wait_for(state="visible", timeout=10000)
            logger.info("login_recovery_clicking_account")
            await tile.click(timeout=15000)  # OAuth redirect can take 10+ seconds
        except Exception as exc:  # noqa: BLE001 — no account tile (full login wall)
            logger.info("login_recovery_no_account_tile")
            return False

        # Wait until we land back on the Copilot chat screen.
        try:
            await page.wait_for_url("**/m365.cloud.microsoft/**", timeout=60000)
            await asyncio.sleep(3.0)  # let the chat SPA hydrate
            return True
        except Exception as exc:  # noqa: BLE001 — navigation never completed
            logger.info("login_recovery_navigation_failed")
            return False
