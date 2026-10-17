from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.adapters.capabilities.meta import MetaCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest
from app.browser.extraction import clean_markdown_text, html_to_markdown
from app.core.config import settings

logger = structlog.get_logger(__name__)


class MetaUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in meta.ai web UI via Playwright (DOM locators only)."""

    name = "meta"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Meta AI composer mode (Thinking vs Instant)."""
        strategy = MetaCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        deep_thinking=parsed.get("deep_thinking"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("meta_selection_parse_failed", error=str(exc))

        is_thinking = mode in {"deep", "deep_research", "thinking", "think", "pro"}
        config = ProviderSelectionRequest(deep_thinking=is_thinking)
        await strategy.apply_selection(page, config)

    async def _response_ready(self, page: Any) -> bool | None:
        """Monitor Meta AI generation state inside data-testid='chat-main-conversation':

        1. Signal generating (False) while Stop button is visible.
        2. Signal completion readiness (True) once Stop button is gone AND copy button
           at the bottom of the response is shown.
        3. If assistant response/thinking status is present but copy button is not yet visible, return False.
        4. Otherwise return None for standard checks.
        """
        try:
            # 1. Check if Stop button is visible
            stop_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-testid='stop-button'], "
                "[data-testid='chat-main-conversation'] button[aria-label*='Stop' i], "
                "[data-testid='chat-main-conversation'] div[aria-label*='Stop' i], "
                "button[aria-label*='Stop' i], "
                "[data-testid='stop-button']"
            )
            count = await stop_loc.count()
            if count > 0:
                for i in range(count):
                    if await stop_loc.nth(i).is_visible(timeout=200):
                        # Still generating!
                        return False

            # 2. Check if Copy button is visible at the bottom of the response
            copy_loc = page.locator(
                "[data-testid='chat-main-conversation'] button[aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] button[aria-label*='Sao chép' i], "
                "button[aria-label*='Copy' i]"
            )
            count = await copy_loc.count()
            if count > 0:
                for i in range(count):
                    if await copy_loc.nth(i).is_visible(timeout=200):
                        # Stop button is gone and copy button is shown!
                        return True

            # 3. If thinking status or conversation content exists but copy button not yet visible, still in progress
            thinking_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-testid='thinking-status'], "
                "[data-testid='thinking-status']"
            )
            if await thinking_loc.count() > 0:
                for i in range(await thinking_loc.count()):
                    if await thinking_loc.nth(i).is_visible(timeout=200):
                        return False
        except Exception as exc:  # noqa: BLE001
            logger.debug("meta_response_ready_check_failed", error=str(exc))

        return None

    async def _extract_html_asset_codes(self, page: Any) -> list[str]:
        """Detect blocks with data-asset-type='HTML' or data-language='html', click

        'View source code' (aria-label='View source code'), and extract code from .ecto-code-source-panel.
        """
        extracted_codes: list[str] = []
        try:
            # Find HTML asset containers
            asset_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-asset-type='HTML'], "
                "[data-testid='chat-main-conversation'] [data-language='html'], "
                "[data-asset-type='HTML'], "
                "[data-language='html']"
            )
            count = await asset_loc.count()
            for i in range(count):
                asset_el = asset_loc.nth(i)
                try:
                    # Look for "View source code" button
                    view_btn = asset_el.locator(
                        "button[aria-label='View source code'], "
                        "[aria-label*='View source code' i], "
                        "button:has-text('View source code'), "
                        "[aria-label*='source code' i]"
                    )
                    if await view_btn.count() > 0:
                        btn = view_btn.first
                        if await btn.is_visible(timeout=500):
                            await btn.click(timeout=2000)
                            await asyncio.sleep(0.4)

                    # Extract text from .ecto-code-source-panel
                    panel_loc = page.locator(".ecto-code-source-panel, [class*='ecto-code-source-panel']")
                    if await panel_loc.count() > 0:
                        panel = panel_loc.first
                        if await panel.is_visible(timeout=500):
                            code_text = await page.evaluate(
                                """
                                (el) => {
                                    if (!el) return '';
                                    const codeEl = el.querySelector('code, pre') || el;
                                    return codeEl.innerText || codeEl.textContent || '';
                                }
                                """,
                                panel,
                            )
                            cleaned = (code_text or "").strip()
                            if cleaned and cleaned not in extracted_codes:
                                extracted_codes.append(cleaned)
                                logger.info("meta_html_asset_code_extracted", length=len(cleaned))
                except Exception as inner_exc:  # noqa: BLE001
                    logger.debug("meta_asset_block_extract_failed", index=i, error=str(inner_exc))
        except Exception as exc:  # noqa: BLE001
            logger.debug("meta_extract_html_asset_codes_failed", error=str(exc))

        return extracted_codes

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        """Extract answer content from Meta AI inside chat-main-conversation.

        1. Inspect HTML asset preview blocks (data-asset-type='HTML') and extract source code
           from .ecto-code-source-panel.
        2. In sync mode, copy via the assistant copy button at the bottom of the response.
        3. Fallback to DOM extraction from [data-testid='chat-main-conversation'].
        4. Embed any extracted HTML source code into markdown if not already present.
        """
        # Step 1: Extract HTML asset code blocks if present
        html_codes = await self._extract_html_asset_codes(page)

        # Step 2: Try clipboard copy button at the bottom of response
        allow_clipboard = (settings.work_mode == "sync")
        if allow_clipboard:
            copy_loc = page.locator(
                "[data-testid='chat-main-conversation'] button[aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] button[aria-label*='Sao chép' i], "
                "button[aria-label*='Copy' i]"
            )
            try:
                count = await copy_loc.count()
                if count > 0:
                    try:
                        await page.evaluate("navigator.clipboard.writeText('')")
                    except Exception:
                        pass
                    target_btn = copy_loc.last if count > 1 else copy_loc.first
                    await target_btn.click(timeout=2000)
                    await asyncio.sleep(0.5)
                    clipboard_text = await page.evaluate("navigator.clipboard.readText()")
                    if (
                        clipboard_text
                        and len(clipboard_text.strip()) > 10
                        and clipboard_text.strip().lower() != prompt.strip().lower()
                    ):
                        logger.info("meta_answer_copied_from_clipboard", length=len(clipboard_text))
                        full_answer = clean_markdown_text(clipboard_text)

                        # Embed any extracted HTML asset code if not already present in clipboard text
                        for code in html_codes:
                            if code not in full_answer and len(code) > 20:
                                full_answer += f"\n\n```html\n{code}\n```"

                        return full_answer
            except Exception as exc:  # noqa: BLE001
                logger.debug("meta_clipboard_copy_failed", error=str(exc))

        # Step 3: Fallback to DOM extraction inside [data-testid="chat-main-conversation"]
        try:
            main_loc = page.locator("[data-testid='chat-main-conversation']")
            if await main_loc.count() > 0:
                target = main_loc.first
                html = await page.evaluate(
                    """
                    (el) => {
                        if (!el) return '';
                        const clone = el.cloneNode(true);
                        // Remove interactive controls and thinking status headers
                        clone.querySelectorAll("button, [role='button'], svg, [data-testid='thinking-status'], [class*='actions']").forEach(b => b.remove());
                        return clone.innerHTML;
                    }
                    """,
                    target,
                )
                if html and ("<" in html and ">" in html):
                    markdown = html_to_markdown(html, provider="meta")
                    if markdown and markdown.strip():
                        full_answer = clean_markdown_text(markdown)
                        for code in html_codes:
                            if code not in full_answer and len(code) > 20:
                                full_answer += f"\n\n```html\n{code}\n```"
                        return full_answer

                raw_text = await page.evaluate(
                    """
                    (el) => {
                        if (!el) return '';
                        const clone = el.cloneNode(true);
                        clone.querySelectorAll("button, [role='button'], svg, [data-testid='thinking-status'], [class*='actions']").forEach(b => b.remove());
                        return clone.innerText || clone.textContent || '';
                    }
                    """,
                    target,
                )
                if raw_text and raw_text.strip():
                    full_answer = clean_markdown_text(raw_text)
                    for code in html_codes:
                        if code not in full_answer and len(code) > 20:
                            full_answer += f"\n\n```html\n{code}\n```"
                    return full_answer
        except Exception as exc:  # noqa: BLE001
            logger.debug("meta_dom_extract_failed", error=str(exc))

        # Fallback to base class
        base_answer = await super()._extract_answer(page, prompt)
        for code in html_codes:
            if code not in base_answer and len(code) > 20:
                base_answer += f"\n\n```html\n{code}\n```"
        return base_answer
