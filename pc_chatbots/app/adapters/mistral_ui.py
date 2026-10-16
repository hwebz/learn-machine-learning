from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.adapters.browser_base import BrowserProviderAdapter
from app.adapters.capabilities.mistral import MistralCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest
from app.browser.extraction import clean_markdown_text, html_to_markdown
from app.core.config import settings

logger = structlog.get_logger(__name__)

MISTRAL_ASST_WRAPPER = (
    "div[data-message-author-role='assistant'], "
    "div[class*='group/message'], "
    "div[class*='group group/message']"
)


class MistralUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chat.mistral.ai (Le Chat) web UI via Playwright (DOM locators only).

    Supported:
    1. No model selection available (available_models = []).
    2. Reasoning mode: Dropdown button nearby Send button with Fast and Think options.
    3. Deep Research toggle: Enabled by typing '@deep-research', selecting the first skill from
       the autocomplete popup, and continuing to enter the prompt.
    4. Status tracking:
       - Based on Stop/Send button to identify whether response is still generating.
       - Thinking and research steps scanned directly from DOM (title, description, status).
       - Auto-expand 'Content truncated' -> clicks 'Expand' button at the footer to reveal full report.
       - Extract full response once action buttons (Like, Dislike, Re-generate, Copy) appear.
    """

    name = "mistral"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._deep_research_active = False

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Switch Mistral reasoning mode (Fast vs Think) and configure Deep Research status."""
        strategy = MistralCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        thinking_level_id=parsed.get("thinking_level_id"),
                        deep_research=parsed.get("deep_research"),
                        deep_thinking=parsed.get("deep_thinking"),
                    )
                    self._deep_research_active = bool(config.deep_research)
                    logger.info("mistral_config_applied", thinking_level=config.thinking_level_id, deep_research=self._deep_research_active)
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("mistral_selection_parse_failed", error=str(exc))

        # Fallback string mode
        is_deep = mode in {"deep", "deep_research", "research", "pro"}
        self._deep_research_active = is_deep
        target_thinking = "think" if (is_deep or mode in {"think", "thinking"}) else "fast"
        config = ProviderSelectionRequest(
            thinking_level_id=target_thinking,
            deep_research=is_deep,
        )
        logger.info("mistral_fallback_mode_applied", target_thinking=target_thinking, deep_research=self._deep_research_active)
        await strategy.apply_selection(page, config)

    async def _enter_prompt(self, page: Any, input_locator: Any, prompt: str) -> None:
        """Enter prompt into Mistral Le Chat ProseMirror editor.

        If Deep Research toggle is active:
        1. Types '@deep-research' into the input
        2. Selects the first skill from the autocomplete popup
        3. Enters the user's prompt after the skill tag
        """
        try:
            await input_locator.click(timeout=5000)
        except Exception:  # noqa: BLE001
            pass

        if self._deep_research_active:
            logger.info("mistral_entering_prompt_with_deep_research", prompt_prefix=prompt[:30])
            # Step 1: Type @deep-research to trigger skill autocomplete
            await input_locator.type("@deep-research", delay=40)
            await asyncio.sleep(1.2)

            # Step 2: Select the first skill from the autocomplete popup
            first_skill = page.locator("[role='listbox'] [role='option'], [role='option'], button[role='option'], div:has-text('deep-research')").first
            if await first_skill.count() > 0 and await first_skill.is_visible(timeout=1500):
                await page.keyboard.press("Enter")
            else:
                await page.keyboard.press("Enter")
            await asyncio.sleep(0.8)

            # Step 3: Continue to enter the prompt with a leading space
            await input_locator.type(f" {prompt}", delay=15)
        else:
            logger.info("mistral_entering_standard_prompt", prompt_prefix=prompt[:30])
            try:
                await input_locator.fill(prompt, timeout=5000)
            except Exception:  # noqa: BLE001
                await input_locator.type(prompt, delay=15)

    async def _handle_truncated_content(self, page: Any) -> bool:
        """Detect if Mistral generated report is collapsed/truncated and click 'Expand' or 'Open Canvas' to open the side panel."""
        try:
            side_sel = "#chat-side-panel, [data-panel-id='chat-side-panel'], [data-panel][data-panel-id='chat-side-panel']"
            side_loc = page.locator(side_sel)
            if await side_loc.count() > 0 and await side_loc.first.is_visible(timeout=200):
                return True

            expand_candidates = [
                f"{MISTRAL_ASST_WRAPPER} button:has-text('Expand')",
                f"{MISTRAL_ASST_WRAPPER} button[aria-label*='Expand' i]",
                f"{MISTRAL_ASST_WRAPPER} button[aria-label='Open Canvas']",
                f"{MISTRAL_ASST_WRAPPER} button[aria-label*='Canvas' i]",
                f"{MISTRAL_ASST_WRAPPER} button[class*='bg-card']",
                "button:has-text('Expand')",
                "button[aria-label*='Expand' i]",
                "button[aria-label='Open Canvas']",
                "button[aria-label*='Canvas' i]",
                "button:has-text('View full')",
                "button:has-text('Show more')",
                "div:has-text('Content truncated') ~ button",
                "div:has-text('Content truncated') button",
            ]
            for sel in expand_candidates:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible(timeout=300):
                    logger.info("mistral_clicking_expand_button", selector=sel)
                    await btn.click(timeout=2000)
                    await page.wait_for_timeout(600)
                    if await side_loc.count() > 0 and await side_loc.first.is_visible(timeout=1000):
                        return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("mistral_handle_truncated_failed", error=str(exc))
        return False

    async def _extract_deep_research_report(self, page: Any) -> str:
        """Extract the full detailed Deep Research report from Mistral's side panel (chat-side-panel).

        Identifies the component via attributes:
          1. data-panel
          2. data-panel-id="chat-side-panel"
          3. id="chat-side-panel"
        """
        side_panel_sel = "#chat-side-panel, [data-panel-id='chat-side-panel'], [data-panel][data-panel-id='chat-side-panel']"
        try:
            side_loc = page.locator(side_panel_sel)
            panel_visible = (await side_loc.count() > 0) and (await side_loc.first.is_visible(timeout=300))

            # 1. If not yet open, click Expand / Open Canvas trigger to open the side panel
            if not panel_visible:
                opened = await self._handle_truncated_content(page)
                if opened:
                    panel_visible = True
                else:
                    side_loc = page.locator(side_panel_sel)
                    panel_visible = (await side_loc.count() > 0) and (await side_loc.first.is_visible(timeout=600))

            if not panel_visible:
                return ""

            # 2. Method A: In sync mode, copy directly via side panel Copy button
            allow_clipboard = (settings.work_mode == "sync")
            if allow_clipboard:
                try:
                    copy_btn = side_loc.locator(
                        "button[aria-label='Copy content to clipboard'], button[aria-label*='Copy' i]"
                    ).first
                    if await copy_btn.count() > 0 and await copy_btn.is_visible(timeout=1000):
                        try:
                            await page.evaluate("navigator.clipboard.writeText('')")
                        except Exception:
                            pass
                        await copy_btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        clipboard_text = await page.evaluate("navigator.clipboard.readText()")
                        if clipboard_text and len(clipboard_text.strip()) > 50:
                            logger.info("mistral_report_copied_from_side_panel_clipboard", length=len(clipboard_text))
                            return clean_markdown_text(clipboard_text)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("mistral_side_panel_clipboard_failed", error=str(exc))

            # 3. Method B: Extract HTML from editor inside side panel and convert to markdown
            editor_selectors = [
                ".tiptap.ProseMirror",
                ".canva-editor",
                ".markdown-editor",
                ".markdown-container-style",
                "div[class*='ProseMirror']",
                "[contenteditable='true']",
                ".markdown-body",
                "article",
            ]
            for ed_sel in editor_selectors:
                ed_loc = side_loc.locator(ed_sel).first
                if await ed_loc.count() > 0 and await ed_loc.is_visible(timeout=500):
                    html = await ed_loc.inner_html(timeout=5000)
                    if html and len(html.strip()) > 30:
                        markdown = html_to_markdown(html, provider=self.name)
                        if markdown and len(markdown.strip()) > 30:
                            logger.info("mistral_report_extracted_from_side_panel_dom", selector=ed_sel, length=len(markdown))
                            return clean_markdown_text(markdown)

            # Fallback inner_text of side panel content area
            body_text = await side_loc.first.inner_text(timeout=3000)
            if body_text and len(body_text.strip()) > 50:
                return clean_markdown_text(body_text)

        except Exception as exc:  # noqa: BLE001
            logger.warning("mistral_extract_deep_research_report_failed", error=str(exc))
        return ""

    async def _extract_thinking_steps(self, page: Any) -> list[dict[str, Any]]:
        """Extract all thinking & research steps (title, description, external links, sources)
        from inside the assistant message wrapper:
          1. data-message-author-role="assistant"
          2. class*="group group/message"
        """
        try:
            asst_loc = page.locator(MISTRAL_ASST_WRAPPER)
            if await asst_loc.count() > 0:
                last_asst = asst_loc.last
                steps_data = await last_asst.evaluate("""
                (wrapper) => {
                    const steps = [];
                    const seen = new Set();

                    // 1. Check reasoning parts
                    const reasoningEls = wrapper.querySelectorAll("div[data-message-part-type='reasoning']");
                    for (const rEl of reasoningEls) {
                        const stepItem = rEl.closest("div[id^='collapsible-content-']") || rEl.closest(".flex.flex-col") || rEl.parentElement;
                        let title = "";
                        const triggerId = stepItem ? stepItem.getAttribute("aria-labelledby") : null;
                        let triggerBtn = triggerId ? wrapper.querySelector(`#${triggerId}`) : null;
                        if (!triggerBtn && stepItem && stepItem.parentElement) {
                            triggerBtn = stepItem.parentElement.querySelector("button[id^='collapsible-trigger-']");
                        }
                        if (triggerBtn) {
                            title = (triggerBtn.innerText || triggerBtn.textContent || "").trim();
                        }
                        if (!title) {
                            const summaryEl = wrapper.querySelector("div[data-testid='harness-steps-summary']");
                            if (summaryEl) title = (summaryEl.innerText || summaryEl.textContent || "").trim();
                        }
                        if (!title) title = "Quá trình suy luận";

                        const paras = Array.from(rEl.querySelectorAll("p, li")).map(p => (p.innerText || p.textContent || "").trim()).filter(Boolean);
                        const desc = paras.join("\\n\\n") || (rEl.innerText || rEl.textContent || "").trim();

                        const links = [];
                        for (const a of rEl.querySelectorAll("a[href^='http']")) {
                            const href = a.getAttribute("href");
                            const text = (a.innerText || a.textContent || "").trim();
                            if (href && !links.some(l => l.url === href)) {
                                links.push({ url: href, title: text || href });
                            }
                        }

                        const key = title + "::" + desc;
                        if (!seen.has(key)) {
                            seen.add(key);
                            steps.push({ title, description: desc, links });
                        }
                    }

                    // 2. Check collapsible content containers if no data-message-part-type='reasoning'
                    if (steps.length === 0) {
                        const collapsibles = wrapper.querySelectorAll("div[id^='collapsible-content-']");
                        for (const c of collapsibles) {
                            const trigId = c.getAttribute("aria-labelledby");
                            const trig = trigId ? wrapper.querySelector(`#${trigId}`) : null;
                            const title = trig ? (trig.innerText || trig.textContent || "").trim() : "Quá trình suy luận";
                            const paras = Array.from(c.querySelectorAll("p, li")).map(p => (p.innerText || p.textContent || "").trim()).filter(Boolean);
                            const desc = paras.join("\\n\\n") || (c.innerText || c.textContent || "").trim();
                            const links = [];
                            for (const a of c.querySelectorAll("a[href^='http']")) {
                                const href = a.getAttribute("href");
                                const text = (a.innerText || a.textContent || "").trim();
                                if (href && !links.some(l => l.url === href)) {
                                    links.push({ url: href, title: text || href });
                                }
                            }
                            const key = title + "::" + desc;
                            if (desc && !seen.has(key)) {
                                seen.add(key);
                                steps.push({ title, description: desc, links });
                            }
                        }
                    }

                    // 3. Check harness steps summary if still empty
                    if (steps.length === 0) {
                        const summaryEl = wrapper.querySelector("div[data-testid='harness-steps-summary']");
                        if (summaryEl) {
                            const sTitle = (summaryEl.innerText || summaryEl.textContent || "").trim();
                            if (sTitle) {
                                steps.push({ title: sTitle, description: "", links: [] });
                            }
                        }
                    }

                    return steps;
                }
                """)
                if isinstance(steps_data, list) and len(steps_data) > 0:
                    return steps_data
        except Exception as exc:  # noqa: BLE001
            logger.debug("mistral_extract_thinking_steps_failed", error=str(exc))

        # Fallback to DOM scan data
        try:
            from app.browser.waits import DOM_SCAN_THINKING_AND_CITATIONS
            raw_scan = await page.evaluate(DOM_SCAN_THINKING_AND_CITATIONS, self.name)
            if isinstance(raw_scan, dict) and raw_scan.get("thinking_steps"):
                scanned = raw_scan["thinking_steps"]
                cits = raw_scan.get("citations", [])
                links = [{"url": str(c.get("url")), "title": c.get("title") or str(c.get("url"))} for c in cits if c.get("url")]
                fallback_steps = []
                for s in scanned:
                    fallback_steps.append({
                        "title": s.get("title", ""),
                        "description": s.get("description", ""),
                        "links": links if s == scanned[-1] else [],
                    })
                return fallback_steps
        except Exception:
            pass

        return []

    def _format_thinking_steps(self, steps: list[dict[str, Any]]) -> str:
        """Format thinking and research steps (title, description, external links, sources)."""
        if not steps:
            return ""

        lines = [
            "<details open>",
            "<summary><b>💭 Quá trình suy luận & Nghiên cứu (Thinking & Research Steps)</b></summary>\n",
        ]
        for idx, step in enumerate(steps, 1):
            title = (step.get("title") or f"Bước {idx}").strip()
            desc = (step.get("description") or "").strip()
            links = step.get("links") or []

            lines.append(f"**{idx}. {title}**\n")
            if desc:
                lines.append(f"{desc}\n")
            if links:
                lines.append("*Nguồn tham khảo (Sources):*")
                for link in links:
                    url = link.get("url") or ""
                    ltitle = link.get("title") or url
                    lines.append(f"- [{ltitle}]({url})")
                lines.append("")
            if idx < len(steps):
                lines.append("---\n")
        lines.append("</details>")
        return "\n".join(lines).strip()

    async def _extract_main_chat_answer(self, page: Any, prompt: str = "") -> str:
        """Extract the final conclusion response from the assistant message wrapper
        (excluding thinking steps, collapsible sections, and footer buttons)."""
        import re

        # Method A: DOM extraction of assistant text without reasoning accordions or action buttons
        try:
            asst_loc = page.locator(MISTRAL_ASST_WRAPPER)
            if await asst_loc.count() > 0:
                last_asst = asst_loc.last
                html = await last_asst.evaluate("""
                (el) => {
                    const clone = el.cloneNode(true);
                    // 1. Remove reasoning / thinking accordions
                    clone.querySelectorAll(
                        "div[data-message-part-type='reasoning'], div[id^='collapsible-content-'], button[id^='collapsible-trigger-'], div[data-testid='harness-steps-summary']"
                    ).forEach(n => n.remove());

                    // 2. Remove footer action buttons (Copy, like, dislike, etc.) and toolbars
                    clone.querySelectorAll("button, nav, header, [role='toolbar']").forEach(n => n.remove());

                    // 3. Remove deep research summary card widget with expand button from final conclusion
                    clone.querySelectorAll("div[class*='bg-card'], div[class*='border-card']").forEach(n => {
                        const txt = n.innerText || "";
                        if (txt.includes("Content truncated") || txt.includes("Canvas") || txt.includes("Expand")) {
                            n.remove();
                        }
                    });

                    return clone.innerHTML;
                }
                """)
                if html and len(html.strip()) > 10:
                    markdown = html_to_markdown(html, provider=self.name)
                    cleaned = clean_markdown_text(markdown)
                    cleaned = re.sub(r"^Thought for [^\n]+\n*", "", cleaned, flags=re.IGNORECASE).strip()
                    cleaned = re.sub(r"Content truncated\s*(?:Expand)?", "", cleaned, flags=re.IGNORECASE).strip()
                    if cleaned and cleaned.lower() != prompt.strip().lower():
                        return cleaned
        except Exception as exc:  # noqa: BLE001
            logger.debug("mistral_main_chat_clean_dom_failed", error=str(exc))

        # Method B: In sync mode, copy directly via assistant message Copy button
        allow_clipboard = (settings.work_mode == "sync")
        if allow_clipboard:
            try:
                asst_loc = page.locator(MISTRAL_ASST_WRAPPER)
                if await asst_loc.count() > 0:
                    last_asst = asst_loc.last
                    copy_btn = last_asst.locator("button[aria-label='Copy to clipboard'], button[aria-label*='Copy' i]").first
                    if await copy_btn.count() > 0 and await copy_btn.is_visible(timeout=1000):
                        try:
                            await page.evaluate("navigator.clipboard.writeText('')")
                        except Exception:
                            pass
                        await copy_btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        clipboard_text = await page.evaluate("navigator.clipboard.readText()")
                        if (
                            clipboard_text
                            and len(clipboard_text.strip()) > 10
                            and clipboard_text.strip().lower() != prompt.strip().lower()
                        ):
                            cleaned = re.sub(r"^Thought for [^\n]+\n*", "", clipboard_text.strip(), flags=re.IGNORECASE).strip()
                            cleaned = re.sub(r"Content truncated\s*(?:Expand)?", "", cleaned, flags=re.IGNORECASE).strip()
                            if cleaned:
                                return clean_markdown_text(cleaned)
            except Exception as exc:  # noqa: BLE001
                logger.debug("mistral_main_chat_clipboard_failed", error=str(exc))

        # Method C: Fallback to container DOM
        try:
            asst_loc = page.locator(MISTRAL_ASST_WRAPPER)
            if await asst_loc.count() > 0:
                last_asst = asst_loc.last
                containers = last_asst.locator(".markdown-container-style, div[class*='prose'], .markdown-body")
                cnt = await containers.count()
                if cnt > 0:
                    target = containers.last
                    html = await target.inner_html(timeout=5000)
                    markdown = html_to_markdown(html, provider=self.name)
                    if markdown and markdown.strip():
                        return clean_markdown_text(markdown)
                    raw_text = await target.inner_text(timeout=5000)
                    if raw_text and raw_text.strip():
                        return clean_markdown_text(raw_text)

                html = await last_asst.inner_html(timeout=5000)
                markdown = html_to_markdown(html, provider=self.name)
                if markdown and markdown.strip():
                    return clean_markdown_text(markdown)
                return clean_markdown_text(await last_asst.inner_text(timeout=5000))
        except Exception as exc:  # noqa: BLE001
            logger.warning("mistral_main_chat_dom_failed", error=str(exc))
        return ""

    async def _response_ready(self, page: Any) -> bool | None:
        """Determine conversation status based on Stop/Send button and end-of-response action buttons:
        1. If Stop button is visible -> STILL GENERATING (return False).
        2. If Send button is missing AND input is not editable -> STILL INITIALIZING / GENERATING (return False).
        3. If 'Content truncated' notice is visible -> click Expand button at footer to open side panel.
        4. If side panel (#chat-side-panel) is open and Stop button is gone -> COMPLETED (return True).
        5. If latest assistant message shows action buttons (Like, Dislike, Re-generate, Copy) -> COMPLETED (return True).
        6. Otherwise return False while waiting for completion indicators.
        """
        try:
            # 1. Check if Stop button is currently visible (definitely still generating)
            stop_loc = page.locator(
                "button[aria-label='Stop generation'], "
                "button[aria-label*='Stop' i], "
                "button[aria-label*='Ngừng' i], "
                "button[aria-label*='Arrêter' i]"
            )
            if await stop_loc.count() > 0:
                for i in range(await stop_loc.count()):
                    try:
                        if await stop_loc.nth(i).is_visible(timeout=150):
                            return False
                    except Exception:
                        pass

            # 2. Check if Send button is restored OR input is editable
            send_loc = page.locator(
                "button[aria-label*='Send' i], "
                "button[aria-label*='Gửi' i], "
                "button[aria-label*='Envoyer' i], "
                "button[type='submit']"
            )
            send_ready = False
            if await send_loc.count() > 0:
                for i in range(await send_loc.count()):
                    try:
                        if await send_loc.nth(i).is_visible(timeout=150):
                            send_ready = True
                            break
                    except Exception:
                        pass

            if not send_ready:
                input_loc = page.locator("div.ProseMirror[contenteditable='true'], [contenteditable='true'], textarea")
                if await input_loc.count() > 0:
                    try:
                        inp_first = input_loc.first
                        if hasattr(inp_first, "is_editable") and await inp_first.is_editable(timeout=150):
                            send_ready = True
                    except Exception:
                        pass

            if not send_ready:
                return False

            # 3. Check if content truncated and expand if needed
            await self._handle_truncated_content(page)

            # 4. Check if Deep Research side panel is visible and ready
            side_sel = "#chat-side-panel, [data-panel-id='chat-side-panel'], [data-panel][data-panel-id='chat-side-panel']"
            side_loc = page.locator(side_sel)
            if await side_loc.count() > 0:
                try:
                    s_first = side_loc.first
                    if hasattr(s_first, "is_visible") and await s_first.is_visible(timeout=150):
                        return True
                except Exception:
                    pass

            # 5. Check action buttons on the latest assistant message
            asst_loc = page.locator(MISTRAL_ASST_WRAPPER)
            if await asst_loc.count() == 0:
                return False
            last_asst = asst_loc.last

            copy_btn = last_asst.locator("button[aria-label='Copy to clipboard'], button[aria-label*='Copy' i]")
            like_btn = last_asst.locator("button[aria-label='Like'], button[aria-label*='Like' i]")
            dislike_btn = last_asst.locator("button[aria-label='Dislike'], button[aria-label*='Dislike' i]")
            rewrite_btn = last_asst.locator("button[aria-label='Rewrite'], button[aria-label*='Regenerat' i]")

            has_copy = await copy_btn.count() > 0 and await copy_btn.first.is_visible(timeout=150)
            has_like = await like_btn.count() > 0 and await like_btn.first.is_visible(timeout=150)
            has_dislike = await dislike_btn.count() > 0 and await dislike_btn.first.is_visible(timeout=150)
            has_rewrite = await rewrite_btn.count() > 0 and await rewrite_btn.first.is_visible(timeout=150)

            # Once Like, Dislike, Re-generate, Copy buttons shown at the end of the response
            if has_copy or has_like or has_dislike or has_rewrite:
                return True

            return False
        except Exception as exc:  # noqa: BLE001
            logger.debug("mistral_response_ready_check_failed", error=str(exc))
            return None

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        """Extract full response following Mistral's order:
        1. All thinking steps (title, description, external links, sources, ...)
        2. Deep research report (from chat-side-panel)
        3. Final conclusion (from main assistant message)
        """
        # 1. Extract all thinking steps
        thinking_steps = await self._extract_thinking_steps(page)
        thinking_markdown = self._format_thinking_steps(thinking_steps)

        # 2. Extract Deep Research report from chat-side-panel (clicking Expand if needed)
        report_markdown = await self._extract_deep_research_report(page)

        # 3. Extract the final conclusion response from the main chat message
        conclusion_markdown = await self._extract_main_chat_answer(page, prompt=prompt)

        # Combine into Mistral's order:
        # 1. All thinking steps
        # 2. Deep research report
        # 3. Final conclusion
        parts: list[str] = []
        if thinking_markdown and thinking_markdown.strip():
            parts.append(thinking_markdown.strip())

        clean_rep = report_markdown.strip() if report_markdown else ""
        clean_conc = conclusion_markdown.strip() if conclusion_markdown else ""

        if clean_rep:
            parts.append(clean_rep)

        if clean_conc:
            if clean_rep and clean_conc != clean_rep:
                # Add conclusion below the report with a clean title
                if clean_conc.lower() not in clean_rep.lower() or len(clean_conc) > 120:
                    parts.append(f"### 📝 Kết luận / Phản hồi\n\n{clean_conc}")
                else:
                    parts.append(clean_conc)
            elif not clean_rep:
                parts.append(clean_conc)

        if parts:
            full_ans = "\n\n---\n\n".join(parts)
            logger.info(
                "mistral_ordered_response_extracted",
                has_thinking=bool(thinking_markdown),
                has_report=bool(clean_rep),
                has_conclusion=bool(clean_conc),
                total_len=len(full_ans),
            )
            return full_ans

        return await super()._extract_answer(page, prompt)
