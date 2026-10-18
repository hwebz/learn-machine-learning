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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._initial_copy_count: int = 0
        self._initial_asst_count: int = 0

    async def _prepare_response(self, page: Any) -> None:
        """Record baseline copy-button and assistant counts before submitting prompt."""
        try:
            self._initial_copy_count = await page.locator(
                "button.copy-response-button, [class*='copy-response-button']"
            ).count()
            self._initial_asst_count = await page.locator(
                "div.chat-assistant, .chat-assistant"
            ).count()
            logger.info(
                "zhipu_baseline_recorded",
                initial_copy_count=self._initial_copy_count,
                initial_asst_count=self._initial_asst_count,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("zhipu_prepare_response_failed", error=str(exc))
            self._initial_copy_count = 0
            self._initial_asst_count = 0

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

        Zhipu response is complete IF AND ONLY IF:
        1. Button with class="copy-response-button" has appeared for the current turn.
        2. Send button is NOT stop icon (no stop button, stop icon svg rect, or stop label).

        While either condition is not met, return False to keep waiting and prevent premature exit.
        Once both conditions are met, return True.
        """
        try:
            # 1. Check for Confirm Preferences dialog
            await self._handle_confirm_preferences(page)

            eval_res = None
            try:
                eval_res = await page.evaluate("""
                (counts) => {
                    const initialCopy = (counts && counts.copyCount) || 0;

                    // 1. Check if Send button is a Stop icon or Stop button is visible
                    let hasStop = false;
                    const stopLocators = [
                        "button:has-text('Stop')",
                        "button:has-text('停止')",
                        "button[aria-label*='Stop' i]",
                        "button[aria-label*='停止']",
                        "button[class*='stop' i]",
                        "button[data-testid*='stop']",
                        "div[aria-label*='Stop' i]",
                        "div[aria-label*='停止']",
                        "[aria-label*='Stop' i]",
                        "[aria-label*='停止']"
                    ];
                    for (const sel of stopLocators) {
                        try {
                            const els = document.querySelectorAll(sel);
                            for (const el of els) {
                                if (el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0) {
                                    hasStop = true;
                                    break;
                                }
                            }
                        } catch(e) {}
                        if (hasStop) break;
                    }

                    if (!hasStop) {
                        const actionButtons = document.querySelectorAll(
                            "button[type='submit'], form button, [class*='input'] button, [class*='chat'] button, footer button, button[aria-label*='Send' i], button[class*='send' i]"
                        );
                        for (const btn of actionButtons) {
                            if (btn.offsetWidth === 0 && btn.offsetHeight === 0 && btn.getClientRects().length === 0) continue;
                            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const title = (btn.getAttribute('title') || '').toLowerCase();
                            const cls = (btn.className || '').toString().toLowerCase();
                            const text = (btn.innerText || btn.textContent || '').trim().toLowerCase();

                            if (aria.includes('stop') || aria.includes('停止') || aria.includes('pause') ||
                                title.includes('stop') || title.includes('停止') ||
                                cls.includes('stop') || text.includes('stop') || text.includes('停止')) {
                                hasStop = true;
                                break;
                            }

                            // CSS square span check (Zhipu stop icon: <span class="block bg-white size-3 dark:bg-black rounded-xs">)
                            const squareSpans = btn.querySelectorAll("span[class*='size-3'], span[class*='size-2.5'], span[class*='size-3.5'], span[class*='rounded-xs']");
                            if (squareSpans.length > 0) {
                                hasStop = true;
                                break;
                            }

                            // SVG rect check (square stop icon)
                            const svgs = btn.querySelectorAll('svg');
                            for (const svg of svgs) {
                                const rects = svg.querySelectorAll('rect');
                                for (const rect of rects) {
                                    const w = parseFloat(rect.getAttribute('width') || '0');
                                    const h = parseFloat(rect.getAttribute('height') || '0');
                                    if (w > 0 && h > 0) {
                                        hasStop = true;
                                        break;
                                    }
                                }
                                const svgCls = (svg.getAttribute('class') || '').toLowerCase();
                                const svgName = (svg.getAttribute('data-icon') || svg.getAttribute('name') || '').toLowerCase();
                                if (svgCls.includes('stop') || svgCls.includes('square') || svgName.includes('stop') || svgName.includes('square')) {
                                    hasStop = true;
                                    break;
                                }
                                if (hasStop) break;
                            }
                            if (hasStop) break;
                        }
                    }

                    // 2. Check active spinning indicators inside .chat-assistant
                    if (!hasStop) {
                        const assts = document.querySelectorAll("div.chat-assistant, .chat-assistant");
                        if (assts.length > 0) {
                            const lastAsst = assts[assts.length - 1];
                            const activeSpin = lastAsst.querySelector("svg.animate-spin, [class*='loading'], [class*='typing'], [class*='cursor'], .cursor");
                            if (activeSpin && (activeSpin.offsetWidth > 0 || activeSpin.offsetHeight > 0 || activeSpin.getClientRects().length > 0)) {
                                hasStop = true;
                            }
                        }
                    }

                    // 3. Check if button with class="copy-response-button" has appeared
                    let hasCopy = false;
                    const assts = document.querySelectorAll("div.chat-assistant, .chat-assistant");
                    if (assts.length > 0) {
                        const lastAsst = assts[assts.length - 1];
                        const copyBtn = lastAsst.querySelector("button.copy-response-button, [class*='copy-response-button']");
                        if (copyBtn && (copyBtn.offsetWidth > 0 || copyBtn.offsetHeight > 0 || copyBtn.getClientRects().length > 0)) {
                            hasCopy = true;
                        }
                    }

                    if (!hasCopy) {
                        const allCopy = document.querySelectorAll("button.copy-response-button, [class*='copy-response-button']");
                        let visibleCount = 0;
                        for (const b of allCopy) {
                            if (b.offsetWidth > 0 || b.offsetHeight > 0 || b.getClientRects().length > 0) {
                                visibleCount++;
                            }
                        }
                        if (visibleCount > initialCopy) {
                            hasCopy = true;
                        }
                    }

                    return { hasStop, hasCopy };
                }
                """, {"copyCount": self._initial_copy_count, "asstCount": self._initial_asst_count})
            except Exception:
                eval_res = None

            has_stop_icon = False
            copy_button_appeared = False

            if isinstance(eval_res, dict):
                has_stop_icon = bool(eval_res.get("hasStop"))
                copy_button_appeared = bool(eval_res.get("hasCopy"))
            elif isinstance(eval_res, bool):
                has_stop_icon = eval_res

            # Playwright locator fallback check for stop button
            if not has_stop_icon:
                try:
                    stop_loc = page.locator(
                        "button:has-text('Stop'), "
                        "button:has-text('停止'), "
                        "button[aria-label*='Stop' i], "
                        "button[aria-label*='停止'], "
                        "div[aria-label*='Stop' i], "
                        "div[aria-label*='停止'], "
                        "[aria-label*='Stop' i], "
                        "[aria-label*='停止'], "
                        "button[class*='stop' i], "
                        "button[data-testid*='stop']"
                    )
                    count = await stop_loc.count()
                    if count > 0:
                        for i in range(count):
                            if await stop_loc.nth(i).is_visible(timeout=100):
                                has_stop_icon = True
                                break
                except Exception:
                    pass

            # Playwright locator fallback check for copy button
            if not copy_button_appeared:
                try:
                    copy_loc = page.locator(
                        "div.chat-assistant button.copy-response-button, "
                        ".chat-assistant button.copy-response-button, "
                        "button.copy-response-button"
                    )
                    count = await copy_loc.count()
                    if count > self._initial_copy_count:
                        for i in range(count):
                            if await copy_loc.nth(i).is_visible(timeout=100):
                                copy_button_appeared = True
                                break
                except Exception:
                    pass

            # Condition 1: Button with class="copy-response-button" appeared
            # Condition 2: Send button is NOT stop icon
            if copy_button_appeared and not has_stop_icon:
                logger.info("zhipu_generation_completed")
                return True

            logger.debug(
                "zhipu_still_generating",
                copy_button_appeared=copy_button_appeared,
                has_stop_icon=has_stop_icon,
            )
            return False

        except Exception as exc:  # noqa: BLE001
            logger.debug("zhipu_response_ready_check_failed", error=str(exc))
            return False

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        """Extract answer content targeting .chat-assistant.

        1. In sync mode, try the assistant's Copy button (clean markdown).
        2. Fallback to DOM extraction from .chat-assistant, excluding thought processes.
        3. If any file is generated with view class="DocxViewer", extract its full HTML and append at the end.
        """
        base_answer = ""
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
                        base_answer = clean_markdown_text(clipboard_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("zhipu_clipboard_copy_failed", error=str(exc))

        # Fallback: extract directly from the last .chat-assistant excluding thought containers
        if not base_answer:
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
                            base_answer = clean_markdown_text(markdown)

                    if not base_answer:
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
                            base_answer = clean_markdown_text(raw_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("zhipu_dom_extract_failed", error=str(exc))

        if not base_answer:
            base_answer = await super()._extract_answer(page, prompt)

        # Check for generated file with view class="DocxViewer"
        try:
            docx_html = await page.evaluate("""
            () => {
                const selectors = [
                    ".DocxViewer",
                    "[class*='DocxViewer']",
                    "[class*='docx-viewer']",
                    "[data-component*='DocxViewer']",
                    "[data-testid*='DocxViewer']",
                    "[data-testid*='docx-viewer']"
                ];
                let viewer = null;
                const assts = document.querySelectorAll("div.chat-assistant, .chat-assistant");
                if (assts.length > 0) {
                    const lastAsst = assts[assts.length - 1];
                    for (const sel of selectors) {
                        const found = lastAsst.querySelector(sel);
                        if (found) {
                            viewer = found;
                            break;
                        }
                    }
                }
                if (!viewer) {
                    for (const sel of selectors) {
                        const all = document.querySelectorAll(sel);
                        if (all.length > 0) {
                            viewer = all[all.length - 1];
                            break;
                        }
                    }
                }
                if (!viewer) return '';

                const clone = viewer.cloneNode(true);
                clone.querySelectorAll("a[href]").forEach(a => {
                    try { a.href = a.href; } catch(e) {}
                });
                clone.querySelectorAll("img[src]").forEach(img => {
                    try { img.src = img.src; } catch(e) {}
                });
                clone.querySelectorAll("source[src]").forEach(s => {
                    try { s.src = s.src; } catch(e) {}
                });
                clone.querySelectorAll("link[href]").forEach(l => {
                    try { l.href = l.href; } catch(e) {}
                });

                let styleTags = '';
                try {
                    const styles = Array.from(document.querySelectorAll("style"));
                    for (const st of styles) {
                        const txt = st.textContent || '';
                        if (txt.includes("DocxViewer") || txt.includes("docx-viewer")) {
                            styleTags += `<style>${txt}</style>\\n`;
                        }
                    }
                } catch(e) {}

                return (styleTags + clone.outerHTML).trim();
            }
            """)
            if (
                docx_html
                and isinstance(docx_html, str)
                and ("DocxViewer" in docx_html or "docx-viewer" in docx_html)
            ):
                logger.info("zhipu_docx_viewer_extracted", html_length=len(docx_html))
                if docx_html not in base_answer:
                    if base_answer.strip():
                        base_answer = f"{base_answer}\n\n{docx_html}"
                    else:
                        base_answer = docx_html
        except Exception as exc:  # noqa: BLE001
            logger.debug("zhipu_docx_viewer_extract_failed", error=str(exc))

        return base_answer
