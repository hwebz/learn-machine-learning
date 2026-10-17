from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.extraction import clean_markdown_text, html_to_markdown
from app.browser.locators import resolve_locator
from app.core.config import settings

logger = structlog.get_logger(__name__)


class MinimaxUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in agent.minimax.io web UI via Playwright (DOM locators only)."""

    name = "minimax"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Minimax model (dropdown nearby send button) and Deep Research toggle."""
        from app.adapters.capabilities.minimax import MinimaxCapabilitiesStrategy
        from app.adapters.capabilities.models import ProviderSelectionRequest

        strategy = MinimaxCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                        deep_research=parsed.get("deep_research"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("minimax_selection_parse_failed", error=str(exc))

        # Handle legacy or string mode
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        target_model = "m3.1-flash" if mode in {"flash", "fast", "standard"} else "m3"
        config = ProviderSelectionRequest(
            model_id=target_model,
            deep_research=is_deep,
        )
        await strategy.apply_selection(page, config)

    async def _enter_prompt(self, page: Any, input_locator: Any, prompt: str) -> None:
        """Enter prompt into Minimax editor (.tiptap.ProseMirror), preserving deep-research chip if present."""
        try:
            await input_locator.click(timeout=5000)
        except Exception:
            pass

        # If deep-research skill command chip is in the editor, ensure focus is after it
        try:
            has_chip = await page.evaluate("""
            () => {
                const chip = document.querySelector(".node-skillCommand, [data-testid='skill-command-chip']");
                return Boolean(chip);
            }
            """)
            if has_chip:
                await page.keyboard.press("End")
                await asyncio.sleep(0.1)
                await page.keyboard.type(f" {prompt}", delay=10)
                return
        except Exception:
            pass

        # Standard entry fallback
        try:
            await input_locator.fill(prompt, timeout=2000)
            is_disabled = await page.evaluate("""
            () => {
                const btn = document.querySelector("[data-testid='send-button']");
                return btn ? (btn.classList.contains('cursor-not-allowed') || btn.getAttribute('aria-disabled') === 'true') : true;
            }
            """)
            if is_disabled:
                await input_locator.click(timeout=3000)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(prompt, delay=10)
        except Exception:
            await input_locator.click(timeout=3000)
            await page.keyboard.type(prompt, delay=10)

    async def _response_ready(self, page: Any) -> bool | None:
        """Monitor Minimax generation state inside data-testid='chat-main-conversation':

        1. Signal generating (False) while Stop button is visible.
        2. Signal completion readiness (True) once Stop button is gone AND copy button
           at the bottom of the assistant response is shown.
        3. If assistant response is present but copy button is not yet visible, return False.
        4. Otherwise return None for standard checks.
        """
        try:
            # 1. Check if Stop button is visible
            stop_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-testid='stop-button'], "
                "[data-testid='stop-button'], "
                "button[aria-label*='Stop' i], "
                "div[aria-label*='Stop' i]"
            )
            count = await stop_loc.count()
            if count > 0:
                for i in range(count):
                    if await stop_loc.nth(i).is_visible(timeout=200):
                        # Still generating!
                        return False

            # 2. Check if Copy button is visible at the bottom of the assistant response
            copy_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-message-role='assistant'] [data-testid='message-actions'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-role='assistant'] [data-testid='message-actions'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-message-role='assistant'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-role='assistant'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-testid='message-actions'] [aria-label*='Copy' i]"
            )
            count = await copy_loc.count()
            if count > 0:
                for i in range(count):
                    if await copy_loc.nth(i).is_visible(timeout=200):
                        # Stop button is gone and copy button at bottom is shown!
                        return True

            # 3. If an assistant turn exists but copy button is not visible yet, still in progress
            asst_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-message-role='assistant'], "
                "[data-testid='chat-main-conversation'] [data-role='assistant'], "
                "div.mb-4.mavis-assistant-reading-row"
            )
            if await asst_loc.count() > 0:
                return False
        except Exception as exc:  # noqa: BLE001
            logger.debug("minimax_response_ready_check_failed", error=str(exc))

        return None

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        """Extract answer content from Minimax message area inside chat-main-conversation.

        1. In sync mode, copy via the assistant copy button at the bottom of the response.
        2. Fallback to DOM extraction from the assistant container, excluding turn-process-disclosure (thinking).
        """
        allow_clipboard = (settings.work_mode == "sync")
        if allow_clipboard:
            copy_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-message-role='assistant'] [data-testid='message-actions'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-role='assistant'] [data-testid='message-actions'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-message-role='assistant'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-role='assistant'] [aria-label*='Copy' i], "
                "[data-testid='chat-main-conversation'] [data-testid='message-actions'] [aria-label*='Copy' i], "
                "button[aria-label*='Copy' i], "
                "div[aria-label*='Copy' i]"
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
                        logger.info("minimax_answer_copied_from_clipboard", length=len(clipboard_text))
                        return clean_markdown_text(clipboard_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("minimax_clipboard_copy_failed", error=str(exc))

        # Fallback to DOM container inside chat-main-conversation, excluding thinking disclosure
        try:
            asst_loc = page.locator(
                "[data-testid='chat-main-conversation'] [data-message-role='assistant'], "
                "[data-testid='chat-main-conversation'] [data-role='assistant'], "
                "div.mb-4.mavis-assistant-reading-row"
            )
            count = await asst_loc.count()
            if count > 0:
                target = asst_loc.last
                html = await page.evaluate("""
                (el) => {
                    if (!el) return '';
                    const clone = el.cloneNode(true);
                    // Remove buttons, icons, actions
                    clone.querySelectorAll("button, [role='button'], svg, [data-testid='message-actions'], [class*='actions']").forEach(b => b.remove());
                    // Remove thinking/turn-process disclosure so final answer is clean
                    clone.querySelectorAll("[data-testid='turn-process-disclosure'], section.mavis-turn-process-disclosure, [data-testid='activity-group']").forEach(t => t.remove());
                    const md = clone.querySelector("[data-testid='assistant-segment-active'], [data-testid='assistant-active-flow'], .matrix-markdown, [class*='markdown']");
                    return md ? md.innerHTML : clone.innerHTML;
                }
                """, target)
                if html and ("<" in html and ">" in html):
                    markdown = html_to_markdown(html, provider="minimax")
                    if markdown and markdown.strip():
                        return clean_markdown_text(markdown)

                raw_text = await page.evaluate("""
                (el) => {
                    if (!el) return '';
                    const clone = el.cloneNode(true);
                    clone.querySelectorAll("button, [role='button'], svg, [data-testid='message-actions'], [class*='actions']").forEach(b => b.remove());
                    clone.querySelectorAll("[data-testid='turn-process-disclosure'], section.mavis-turn-process-disclosure, [data-testid='activity-group']").forEach(t => t.remove());
                    return clone.innerText || clone.textContent || '';
                }
                """, target)
                if raw_text and raw_text.strip():
                    return clean_markdown_text(raw_text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("minimax_dom_extract_failed", error=str(exc))

        # Fallback to base class
        return await super()._extract_answer(page, prompt)
