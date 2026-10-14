from __future__ import annotations

import asyncio
import base64
import re
from typing import Any

import structlog

from app.adapters.browser_base import AnswerExtractionError, BrowserProviderAdapter
from app.browser.chatgpt_response import CAPTURE_RESPONSES, EXTRACT_RESPONSE, RESPONSE_READY
from app.browser.extraction import clean_markdown_text, html_to_markdown
from app.browser.locators import resolve_locator
from app.browser.media import MAX_IMAGE_BYTES, MAX_IMAGES, save_image
from app.core.config import settings

logger = structlog.get_logger(__name__)


class ChatGPTUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in chatgpt.com web UI via Playwright (DOM locators only)."""

    name = "chatgpt"

    async def _prepare_response(self, page: Any) -> None:
        await page.evaluate(CAPTURE_RESPONSES)

    async def _response_ready(self, page: Any) -> bool | None:
        return await page.evaluate(RESPONSE_READY)

    async def _extract_answer(self, page: Any, prompt: str = "") -> str:
        try:
            response = await asyncio.wait_for(
                page.evaluate(EXTRACT_RESPONSE, {"maxBytes": MAX_IMAGE_BYTES, "maxImages": MAX_IMAGES}),
                timeout=MAX_IMAGES * 16,
            )
        except Exception as exc:
            raise AnswerExtractionError(f"Could not retrieve ChatGPT generated images: {exc}") from exc
        if response is None:
            return await super()._extract_answer(page, prompt=prompt)

        answer = html_to_markdown(response.get("html", ""), provider=self.name)
        parts = [answer] if answer.strip() else []
        failures = []
        for image in response.get("images", []):
            try:
                if image.get("error"):
                    raise ValueError(image["error"])
                encoded = image["data"]
                if len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
                    raise ValueError("Generated image exceeds size limit")
                data = base64.b64decode(encoded, validate=True)
                filename = await asyncio.to_thread(save_image, data, image["type"], settings.media_dir)
                alt = re.sub(r"[\r\n\t]+", " ", image.get("alt") or "Generated image")
                alt = alt.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
                parts.append(f"![{alt}](/api/media/{filename})")
            except Exception as exc:
                failures.append(str(exc))
        result = clean_markdown_text("\n\n".join(parts))
        if failures:
            raise AnswerExtractionError("Could not save ChatGPT generated image: " + "; ".join(failures), result)
        return result

    async def _select_mode(self, page: Any, mode: str) -> None:
        """Switch ChatGPT thinking mode (Think button pill), model, or Deep research."""
        from app.adapters.capabilities.models import ProviderSelectionRequest
        from app.adapters.capabilities.chatgpt import ChatGPTCapabilitiesStrategy

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
                    strategy = ChatGPTCapabilitiesStrategy()
                    await strategy.apply_selection(page, config)
                    return
            except Exception:
                pass

        is_deep = mode in {"deep", "deep_research", "research", "pro", "thinking"}
        cfg_modes = self._cfg.get("mode_selectors") or {}

        # 1. Try toggling the "Think" button pill first
        think_chain = cfg_modes.get("think_toggle")
        if think_chain:
            try:
                await page.locator("button:has-text('Think'), button[aria-label*='Think' i]").first.wait_for(state="visible", timeout=3000)
            except Exception:
                pass
            locator, _ = await resolve_locator(page, think_chain)
            if locator is not None:
                try:
                    aria_pressed = await locator.get_attribute("aria-pressed")
                    is_pressed = aria_pressed == "true"
                    if is_deep and not is_pressed:
                        await locator.click(timeout=3000)
                        logger.info("chatgpt_mode_selected", mode=mode, action="think_enabled")
                        return
                    if not is_deep and is_pressed:
                        await locator.click(timeout=3000)
                        logger.info("chatgpt_mode_selected", mode=mode, action="think_disabled")
                        return
                    if (is_deep and is_pressed) or (not is_deep and not is_pressed):
                        logger.info("chatgpt_mode_already_set", mode=mode, is_pressed=is_pressed)
                        return
                except Exception as exc:  # noqa: BLE001
                    logger.warning("chatgpt_think_toggle_failed", error=str(exc))

        # 2. Fallback to research_mode if deep_research is requested
        if is_deep:
            chain = cfg_modes.get("research_mode")
            if not chain:
                return
            locator, _ = await resolve_locator(page, chain)
            if locator is None:
                logger.info("chatgpt_mode_skipped", mode=mode)
                return
            try:
                await locator.click(timeout=3000)
                logger.info("chatgpt_mode_selected", mode=mode)
            except Exception as exc:  # noqa: BLE001
                logger.warning("chatgpt_mode_click_failed", error=str(exc))

    async def _extract_sources(self, page: Any) -> list[Any]:
        """Extract sources for ChatGPT via 'More actions' -> 'View sources' -> 'Sources' modal,

        for the selected response just asked, with fallback to inline citations.
        """
        from app.adapters.browser_base import Source, normalize_sources

        pairs: list[tuple[str, str | None, str | None]] = []

        try:
            # 1. Target the conversation turn for the selected response we've just asked for
            selected_turn = None
            try:
                asst_turns = page.locator(
                    "article:has([data-message-author-role='assistant']), "
                    "article[data-testid*='conversation-turn'], "
                    "[data-message-author-role='assistant']"
                )
                count = await asst_turns.count()
                if count > 0:
                    selected_turn = asst_turns.last
                    await selected_turn.scroll_into_view_if_needed(timeout=2000)
                    await selected_turn.hover(timeout=2000)
                    await page.wait_for_timeout(300)
            except Exception:
                pass

            # 2. Check if the modal with aria-label="Sources" is already open
            modal = page.locator(
                "[aria-label='Sources'], "
                "[aria-label*='Sources' i], "
                "[aria-label*='Nguồn' i]"
            ).first
            modal_open = False
            try:
                if await modal.count() > 0 and await modal.is_visible(timeout=500):
                    modal_open = True
            except Exception:
                modal_open = False

            # 3. If modal not already open, click 'More actions' -> 'View sources'
            if not modal_open:
                more_btn = None
                if selected_turn is not None:
                    turn_more = selected_turn.locator(
                        "[aria-label='More actions'], "
                        "[aria-label*='More action' i], "
                        "[aria-label*='Thao tác khác' i]"
                    ).last
                    if await turn_more.count() > 0:
                        more_btn = turn_more

                if more_btn is None or await more_btn.count() == 0:
                    global_more = page.locator(
                        "[aria-label='More actions'], "
                        "[aria-label*='More action' i], "
                        "[aria-label*='Thao tác khác' i]"
                    ).last
                    if await global_more.count() > 0:
                        more_btn = global_more

                if more_btn is not None and await more_btn.count() > 0:
                    try:
                        await more_btn.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass
                    clicked_more = False
                    try:
                        await more_btn.click(timeout=2500)
                        clicked_more = True
                    except Exception:
                        try:
                            await more_btn.click(force=True, timeout=2000)
                            clicked_more = True
                        except Exception:
                            try:
                                await more_btn.dispatch_event("click")
                                clicked_more = True
                            except Exception:
                                pass

                    if clicked_more:
                        await page.wait_for_timeout(400)

                        # Click 'View sources' in dropdown menu
                        view_sources_selectors = [
                            "[role='menu'] [role='menuitem']:has-text('View sources')",
                            "[role='menuitem']:has-text('View sources')",
                            "button:has-text('View sources')",
                            "[role='menu'] button:has-text('View sources')",
                            "[role='menu'] div:has-text('View sources'):not(:has(div:has-text('View sources')))",
                            "[role='menu'] [role='menuitem']:has-text('Xem nguồn')",
                            "[role='menuitem']:has-text('Xem nguồn')",
                            "button:has-text('Xem nguồn')",
                            "[data-testid*='source']",
                            ":text-is('View sources')",
                            ":text-is('Xem nguồn')",
                        ]
                        clicked_view_sources = False
                        for sel in view_sources_selectors:
                            cand = page.locator(sel).first
                            try:
                                if await cand.count() > 0 and await cand.is_visible(timeout=800):
                                    await cand.click(timeout=2000)
                                    clicked_view_sources = True
                                    break
                            except Exception:
                                continue

                        if not clicked_view_sources:
                            for sel in view_sources_selectors:
                                cand = page.locator(sel).first
                                try:
                                    if await cand.count() > 0:
                                        await cand.click(force=True, timeout=1500)
                                        clicked_view_sources = True
                                        break
                                except Exception:
                                    continue

                        if clicked_view_sources:
                            await page.wait_for_timeout(500)
                        else:
                            await page.keyboard.press("Escape")

            # 4. Extract sources from modal with attribute aria-label="Sources"
            modal = page.locator(
                "[aria-label='Sources'], "
                "[aria-label*='Sources' i], "
                "[aria-label*='Nguồn' i]"
            ).first

            try:
                await modal.wait_for(state="visible", timeout=3000)
            except Exception:
                pass

            if await modal.count() > 0 and await modal.is_visible(timeout=1000):
                try:
                    modal_sources = await modal.evaluate("""(modalEl) => {
                        const results = [];
                        const seen = new Set();
                        const links = modalEl.querySelectorAll("a[href^='http']");
                        for (const a of links) {
                            const href = a.href || a.getAttribute("href") || "";
                            if (!href || href.includes("chatgpt.com") || href.includes("openai.com")) continue;
                            if (seen.has(href)) continue;
                            seen.add(href);

                            let title = (a.getAttribute("title") || a.getAttribute("aria-label") || "").trim();
                            let snippet = "";

                            const titleEl = a.querySelector("h3, h4, h5, [class*='title'], strong, div[class*='font-semibold'], div[class*='font-medium'], div[class*='text-sm']");
                            if (titleEl) {
                                title = (titleEl.innerText || titleEl.textContent || "").trim();
                            }

                            const snipEl = a.querySelector("p, [class*='snippet'], [class*='desc'], [class*='content'], [class*='line-clamp'], [class*='text-xs']");
                            if (snipEl && snipEl !== titleEl) {
                                snippet = (snipEl.innerText || snipEl.textContent || "").trim();
                            }

                            if (!title) {
                                const raw = (a.innerText || a.textContent || "").trim();
                                if (raw) {
                                    const lines = raw.split("\\n").map(l => l.trim()).filter(Boolean);
                                    title = lines[0] || "";
                                    if (!snippet && lines.length > 1) {
                                        snippet = lines.slice(1).join(" ");
                                    }
                                }
                            }

                            if (!title) {
                                try {
                                    title = new URL(href).hostname.replace(/^www\\./, "");
                                } catch (e) {
                                    title = href;
                                }
                            }

                            results.push({ url: href, title: title, snippet: snippet });
                        }
                        return results;
                    }""")
                    if isinstance(modal_sources, list):
                        for s in modal_sources:
                            u = s.get("url")
                            if u:
                                pairs.append((u, s.get("title") or None, s.get("snippet") or None))
                except Exception as exc:
                    logger.debug("chatgpt_modal_eval_failed", error=str(exc))

                # Fallback to locator-based extraction if evaluate returned empty
                if not pairs:
                    links = modal.locator("a[href^='http']")
                    link_count = await links.count()
                    for i in range(link_count):
                        link = links.nth(i)
                        href = await link.get_attribute("href")
                        if href and not ("chatgpt.com" in href or "openai.com" in href):
                            title = ""
                            try:
                                title = (await link.inner_text(timeout=500)).strip()
                            except Exception:
                                pass
                            pairs.append((href, title or None, None))

                # Close the modal cleanly so it does not obstruct the page
                try:
                    close_btn = modal.locator(
                        "button[aria-label*='Close' i], "
                        "button[aria-label*='Đóng' i], "
                        "button[aria-label*='dismiss' i], "
                        "button:has-text('✕'), "
                        "button:has-text('×')"
                    ).first
                    if await close_btn.count() > 0 and await close_btn.is_visible(timeout=500):
                        await close_btn.click(timeout=1000)
                    else:
                        await page.keyboard.press("Escape")
                    await page.wait_for_timeout(200)
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("chatgpt_modal_sources_extract_failed", error=str(exc))

        # 5. Fallback and merge with base extraction
        try:
            base_sources = await super()._extract_sources(page)
            for s in base_sources:
                pairs.append((str(s.url), s.title, s.snippet))
        except Exception:
            pass

        return normalize_sources(pairs)

