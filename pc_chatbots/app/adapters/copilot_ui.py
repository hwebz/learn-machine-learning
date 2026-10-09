from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter

logger = structlog.get_logger(__name__)

# The "Pick an account" screen lists previously used Microsoft accounts as
# ".row.tile" listitems, each with an inner "div.table[role='button']" clickable
# tile; the last one is always "#otherTile" ("Use another account") — skip it.
_ACCOUNT_TILE = "div.row.tile div.table[role='button']:not(#otherTile)"


class CopilotUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in Microsoft 365 Copilot web UI via Playwright (DOM locators only)."""

    name = "copilot"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """No mode switching for Copilot in V1."""
        return

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
