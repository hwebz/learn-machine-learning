from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.adapters.base import Source
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

    async def _extract_sources(self, page: Any) -> list[Source]:
        """Click the Sources button if present to open the sources flyout/pane and collect all citations."""
        try:
            btn = page.locator("button[data-testid='sources-button-testid'], button[aria-label='Sources'], [data-testid='sources-button-testid']").first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(timeout=1500)
                await asyncio.sleep(0.5)
        except Exception:  # noqa: BLE001
            pass

        sources = await super()._extract_sources(page)

        # Also extract inline paragraph citations from fai-BebopCitation buttons
        try:
            inline_citations = await page.evaluate("""() => {
                const results = [];
                const buttons = document.querySelectorAll("button[class*='fai-BebopCitation'], [class*='fai-BebopCitation'], [data-grouped-citations]");
                for (const b of buttons) {
                    const raw = b.getAttribute("data-grouped-citations");
                    const aria = b.getAttribute("aria-label") || "";
                    let title = "";
                    if (aria) {
                        let clean = aria.trim();
                        if (clean.toLowerCase().startsWith("citation:")) clean = clean.slice(9).trim();
                        if (clean.includes(" — ")) title = clean.split(" — ")[1].trim();
                        else if (clean.includes(" - ")) title = clean.split(" - ")[1].trim();
                        else title = clean;
                    }
                    if (raw) {
                        try {
                            const parsed = JSON.parse(raw);
                            if (Array.isArray(parsed)) {
                                for (const item of parsed) {
                                    if (item && item.url) {
                                        results.push({ url: item.url, title: item.name || title || item.url });
                                    }
                                }
                            }
                        } catch (e) {}
                    }
                }
                return results;
            }""")
            if isinstance(inline_citations, list) and inline_citations:
                known_urls = {str(s.url) for s in sources}
                for c in inline_citations:
                    u = c.get("url")
                    if u and u not in known_urls:
                        known_urls.add(u)
                        sources.append(Source(url=u, title=c.get("title") or u))
        except Exception:  # noqa: BLE001
            pass

        return sources

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Copilot mode (Auto, Quick Response, Think Deeper, GPT-5.6 Sol options)."""
        from app.adapters.capabilities.models import ProviderSelectionRequest
        from app.adapters.capabilities.copilot import CopilotCapabilitiesStrategy

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                        thinking_level_id=parsed.get("thinking_level_id"),
                        mode_id=parsed.get("mode_id"),
                    )
                    strategy = CopilotCapabilitiesStrategy()
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("copilot_selection_parse_failed", error=str(exc))

        # Direct string mode fallback (e.g. "think_deeper", "deep", "quick", "auto")
        target_mode = "think_deeper" if mode in {"deep", "deep_research", "think_deeper", "thinking"} else mode
        strategy = CopilotCapabilitiesStrategy()
        config = ProviderSelectionRequest(mode_id=target_mode)
        await strategy.apply_selection(page, config)

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
