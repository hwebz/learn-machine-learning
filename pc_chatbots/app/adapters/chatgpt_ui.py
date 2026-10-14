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
                        tool_id=parsed.get("tool_id"),
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

        with automatic fallback to base locator and inline citation extraction.
        """
        from app.adapters.browser_base import Source, normalize_sources

        pairs: list[tuple[str, str | None]] = []

        try:
            # 1. Look for 'More actions' button on the assistant response turn
            more_btn = page.locator(
                "article [data-message-author-role='assistant'] button[aria-label*='More action' i], "
                "[data-message-author-role='assistant'] button[aria-label*='More action' i], "
                "button[aria-label='More actions'], "
                "button[aria-label*='Thao tác khác' i]"
            ).last

            if await more_btn.count() > 0 and await more_btn.is_visible(timeout=1000):
                await more_btn.click(timeout=1500)
                await page.wait_for_timeout(300)

                # 2. Look for 'View sources' menu item
                view_sources_item = page.locator(
                    "[role='menuitem']:has-text('View sources'), "
                    "[role='menuitem']:has-text('Xem nguồn'), "
                    "button:has-text('View sources'), "
                    "button:has-text('Xem nguồn'), "
                    ":has-text('View sources')"
                ).first

                if await view_sources_item.count() > 0 and await view_sources_item.is_visible(timeout=1500):
                    await view_sources_item.click(timeout=1500)
                    await page.wait_for_timeout(400)

                    # 3. Look for modal with aria-label="Sources" (or aria-label="Nguồn" / role="dialog")
                    modal = page.locator(
                        "[aria-label='Sources'], "
                        "[aria-label='Nguồn'], "
                        "[role='dialog'][aria-label*='Sources' i], "
                        "[role='dialog'][aria-label*='Nguồn' i], "
                        "[role='dialog']:has-text('Sources')"
                    ).first

                    if await modal.count() > 0 and await modal.is_visible(timeout=2000):
                        # Extract all links inside the sources modal
                        links = modal.locator("a[href^='http']")
                        link_count = await links.count()
                        for i in range(link_count):
                            link = links.nth(i)
                            href = await link.get_attribute("href")
                            if href:
                                title = ""
                                try:
                                    title = (await link.inner_text(timeout=500)).strip()
                                except Exception:
                                    pass
                                pairs.append((href, title or None))

                        # Close the modal
                        try:
                            close_btn = modal.locator(
                                "button[aria-label*='Close' i], "
                                "button[aria-label*='Đóng' i], "
                                "button[aria-label*='dismiss' i]"
                            ).first
                            if await close_btn.count() > 0 and await close_btn.is_visible(timeout=500):
                                await close_btn.click(timeout=1000)
                            else:
                                await page.keyboard.press("Escape")
                            await page.wait_for_timeout(200)
                        except Exception:
                            pass
                else:
                    await page.keyboard.press("Escape")
        except Exception as exc:
            logger.debug("chatgpt_modal_sources_extract_failed", error=str(exc))

        # 4. Fallback and merge with base extraction
        try:
            base_sources = await super()._extract_sources(page)
            for s in base_sources:
                pairs.append((str(s.url), s.title))
        except Exception:
            pass

        return normalize_sources(pairs)

