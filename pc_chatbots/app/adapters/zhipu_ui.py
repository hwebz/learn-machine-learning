from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.extraction import clean_markdown_text, html_to_markdown
from app.core.config import settings

logger = structlog.get_logger(__name__)


class ZhipuUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.z.ai (Zhipu/GLM) web UI via Playwright (DOM locators only)."""

    name = "zhipu"

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch Zhipu model via capabilities strategy (top-left dropdown)."""
        from app.adapters.capabilities.models import ProviderSelectionRequest
        from app.adapters.capabilities.zhipu import ZhipuCapabilitiesStrategy

        strategy = ZhipuCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("zhipu_selection_parse_failed", error=str(exc))

        # Handle direct model IDs or legacy mode strings
        target_model = "glm-5.3-flash"
        if mode:
            lower = mode.strip().lower()
            if "5.3" in lower and "flash" in lower:
                target_model = "glm-5.3-flash"
            elif "5.3" in lower:
                target_model = "glm-5.3"
            elif "5.2" in lower:
                target_model = "glm-5.2"
            elif lower in {"deep", "pro", "research", "deep_research", "flagship"}:
                target_model = "glm-5.3"
            elif lower in {"flash", "standard", "fast"}:
                target_model = "glm-5.3-flash"
            elif "plus" in lower:
                target_model = "glm-4-plus"
            elif "air" in lower:
                target_model = "glm-4-air"
            elif "zero" in lower:
                target_model = "glm-zero"
            elif lower.startswith("glm-"):
                target_model = lower

        config = ProviderSelectionRequest(model_id=target_model)
        await strategy.apply_selection(page, config)

    async def _handle_confirm_preferences(self, page: Any, max_wait_s: float = 75.0) -> bool:
        """Handle Zhipu AI 'Confirm Preferences' modal/dialog.

        Rules:
        - Leave all questions/choices default.
        - Wait for 'Continue' button to become enabled or for dialog to auto-dismiss/continue.
        - Click 'Continue' once available.
        """
        try:
            is_dialog_open = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll("[role='dialog'], [aria-modal='true'], form, .modal, [class*='modal'], [class*='dialog'], div");
                for (const el of elements) {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        const txt = (el.innerText || el.textContent || "").toLowerCase();
                        if (txt.includes("confirm preferences") || txt.includes("confirm preference") || txt.includes("确认偏好") || txt.includes("偏好确认")) {
                            return true;
                        }
                    }
                }
                return false;
            }
            """)
        except Exception:
            is_dialog_open = False

        if not is_dialog_open:
            return False

        logger.info("zhipu_confirm_preferences_detected", max_wait_s=max_wait_s)
        start_t = time.monotonic()

        while (time.monotonic() - start_t) < max_wait_s:
            # Check if dialog auto-dismissed / auto-continued
            try:
                still_open = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll("[role='dialog'], [aria-modal='true'], form, .modal, [class*='modal'], [class*='dialog'], div");
                    for (const el of elements) {
                        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                            const txt = (el.innerText || el.textContent || "").toLowerCase();
                            if (txt.includes("confirm preferences") || txt.includes("confirm preference") || txt.includes("确认偏好") || txt.includes("偏好确认")) {
                                return true;
                            }
                        }
                    }
                    return false;
                }
                """)
                if not still_open:
                    logger.info("zhipu_confirm_preferences_auto_continued_or_closed")
                    return True
            except Exception:
                pass

            # Check if Continue button is enabled
            try:
                continue_loc = page.locator(
                    "button:has-text('Continue'), "
                    "button:has-text('继续'), "
                    "button[aria-label*='Continue' i], "
                    "[role='button']:has-text('Continue')"
                )
                count = await continue_loc.count()
                if count > 0:
                    btn = continue_loc.first
                    if await btn.is_visible(timeout=500):
                        is_disabled = await page.evaluate("""
                        (btn) => {
                            if (!btn) return true;
                            if (btn.disabled || btn.getAttribute('disabled') !== null) return true;
                            if (btn.getAttribute('aria-disabled') === 'true') return true;
                            const cls = (btn.className || '').toLowerCase();
                            if (cls.includes('disabled')) return true;
                            return false;
                        }
                        """, btn)
                        if not is_disabled:
                            logger.info("zhipu_confirm_preferences_clicking_continue")
                            await btn.click(timeout=3000)
                            await asyncio.sleep(1.0)
                            return True
            except Exception as click_err:
                logger.debug("zhipu_continue_check_failed", error=str(click_err))

            await asyncio.sleep(1.5)

        # Timeout reached fallback
        logger.warning("zhipu_confirm_preferences_wait_timeout")
        try:
            continue_loc = page.locator(
                "button:has-text('Continue'), button:has-text('继续'), button[aria-label*='Continue' i]"
            )
            if await continue_loc.count() > 0 and await continue_loc.first.is_visible(timeout=500):
                await continue_loc.first.click(force=True, timeout=2000)
        except Exception:
            pass
        return True

    async def _response_ready(self, page: Any) -> bool | None:
        """Monitor Zhipu generation state:

        1. Detect and resolve 'Confirm Preferences' popup.
        2. Signal generating (False) while Stop button is present.
        3. Signal completion readiness when Stop button is gone and Copy icon is available.
        """
        try:
            # 1. Check for Confirm Preferences dialog
            await self._handle_confirm_preferences(page)

            # 2. Check if Stop button is visible
            stop_loc = page.locator(
                "button:has-text('Stop'), "
                "button:has-text('停止'), "
                "button[aria-label*='Stop' i], "
                "button[aria-label*='停止'], "
                "button[class*='stop' i], "
                "button[data-testid*='stop']"
            )
            count = await stop_loc.count()
            if count > 0:
                for i in range(count):
                    if await stop_loc.nth(i).is_visible(timeout=200):
                        # Still generating!
                        return False

            # 3. Check if Copy button is visible in .chat-assistant
            copy_loc = page.locator(
                "div.chat-assistant button.copy-response-button, "
                "div.chat-assistant button[class*='copy' i], "
                "div.chat-assistant [aria-label*='Copy' i], "
                ".chat-assistant button[class*='copy' i], "
                ".chat-assistant [aria-label*='Copy' i]"
            )
            if await copy_loc.count() > 0:
                for i in range(await copy_loc.count()):
                    if await copy_loc.nth(i).is_visible(timeout=200):
                        # Generation finished and copy button rendered
                        return None
        except Exception as exc:  # noqa: BLE001
            logger.debug("zhipu_response_ready_check_failed", error=str(exc))

        return None

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        """Extract answer content targeting .chat-assistant.

        1. In sync mode, try the assistant's Copy button (clean markdown).
        2. Fallback to DOM extraction from .chat-assistant, excluding thought processes.
        """
        allow_clipboard = (settings.work_mode == "sync")
        if allow_clipboard:
            copy_loc = page.locator(
                "div.chat-assistant button.copy-response-button, "
                "div.chat-assistant button[class*='copy' i], "
                "div.chat-assistant [aria-label*='Copy' i], "
                ".chat-assistant button[class*='copy' i], "
                ".chat-assistant [aria-label*='Copy' i], "
                "button.copy-response-button"
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
                        logger.info("zhipu_answer_copied_from_clipboard", length=len(clipboard_text))
                        return clean_markdown_text(clipboard_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("zhipu_clipboard_copy_failed", error=str(exc))

        # Fallback: extract directly from the last .chat-assistant excluding thought containers
        try:
            asst_loc = page.locator("div.chat-assistant, .chat-assistant")
            count = await asst_loc.count()
            if count > 0:
                target = asst_loc.last
                html = await page.evaluate("""
                (el) => {
                    if (!el) return '';
                    const clone = el.cloneNode(true);
                    // Remove buttons and icons
                    clone.querySelectorAll("button, [role='button'], svg, [class*='action'], .copy-response-button").forEach(b => b.remove());
                    // Remove thinking/reasoning blocks so final answer text is clean
                    clone.querySelectorAll("details, [class*='thought'], [class*='reasoning'], [class*='thinking']").forEach(t => t.remove());
                    const md = clone.querySelector(".markdown, .markdown-body, [class*='markdown']");
                    return md ? md.innerHTML : clone.innerHTML;
                }
                """, target)
                if html and ("<" in html and ">" in html):
                    markdown = html_to_markdown(html, provider="zhipu")
                    if markdown and markdown.strip():
                        return clean_markdown_text(markdown)

                raw_text = await page.evaluate("""
                (el) => {
                    if (!el) return '';
                    const clone = el.cloneNode(true);
                    clone.querySelectorAll("button, [role='button'], svg, [class*='action'], .copy-response-button").forEach(b => b.remove());
                    clone.querySelectorAll("details, [class*='thought'], [class*='reasoning'], [class*='thinking']").forEach(t => t.remove());
                    return clone.innerText || clone.textContent || '';
                }
                """, target)
                if raw_text and raw_text.strip():
                    return clean_markdown_text(raw_text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("zhipu_dom_extract_failed", error=str(exc))

        return await super()._extract_answer(page, prompt)
