from __future__ import annotations

from typing import Any

import structlog

from app.adapters.base import Source
from app.adapters.browser_base import BrowserProviderAdapter
from app.browser.locators import resolve_locator

logger = structlog.get_logger(__name__)


class GeminiUIAdapter(BrowserProviderAdapter):
    """Drive the signed-in gemini.google.com web UI via Playwright (DOM locators only)."""

    name = "gemini"

    async def _extract_sources(self, page: Any) -> list[Source]:
        """Ensure thought toggles or attribution containers are open before extraction."""
        try:
            toggles = page.locator(
                ".thoughts-container button[aria-expanded='false'], "
                ".thoughts-wrapper button[aria-expanded='false'], "
                "button.thoughts-header[aria-expanded='false'], "
                "button.thoughts-toggle[aria-expanded='false'], "
                "button[aria-label*='suy nghĩ' i][aria-expanded='false'], "
                "button[aria-label*='thought' i][aria-expanded='false']"
            )
            count = await toggles.count()
            for idx in range(count):
                toggle = toggles.nth(idx)
                if await toggle.is_visible(timeout=500):
                    await toggle.click(timeout=1000)
        except Exception:  # noqa: BLE001
            pass
        return await super()._extract_sources(page)

    async def _select_mode(self, page: Any, mode: str, *, timeout_s: float = 8.0) -> None:
        """Configure Gemini model (3.8 Flash, 3.1 Pro, 4 Argon, 3.5 Flash-Lite) and thinking effort (Cao, Trung bình, Thấp)."""
        from app.adapters.capabilities.gemini import GeminiCapabilitiesStrategy
        from app.adapters.capabilities.models import ProviderSelectionRequest

        strategy = GeminiCapabilitiesStrategy()

        if mode and mode.startswith("{") and mode.endswith("}"):
            try:
                import json
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    config = ProviderSelectionRequest(
                        model_id=parsed.get("model_id"),
                        thinking_level_id=parsed.get("thinking_level_id"),
                        mode_id=parsed.get("mode_id"),
                        deep_research=parsed.get("deep_research"),
                    )
                    await strategy.apply_selection(page, config)
                    return
            except Exception as exc:  # noqa: BLE001
                logger.warning("gemini_selection_parse_failed", error=str(exc))

        # Fallback string mode
        is_deep = mode in {"deep", "deep_research", "research", "pro", "thinking"}
        config = ProviderSelectionRequest(
            model_id="gemini-3.1-pro" if is_deep else "gemini-3.8-flash",
            thinking_level_id="high" if is_deep else "medium",
            mode_id=mode,
            deep_research=True if is_deep else None,
        )
        await strategy.apply_selection(page, config)

    async def delete_conversation(self, conversation_url: str) -> bool:
        """Delete conversation on gemini.google.com by clicking the 3-dots top right menu,
        selecting 'Xóa', confirming if prompted, and waiting for the 'Đã xóa...' toast.
        """
        import asyncio
        import time

        if not conversation_url or not conversation_url.startswith(("http://", "https://")):
            return False

        logger.info("gemini_delete_conversation_start", url=conversation_url)
        try:
            async with self._session.exclusive():
                page = await self._session.new_page(conversation_url)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(2.0)  # Wait for Angular hydration

                try:
                    # 1. Check if already deleted or redirected to /app without conversation ID
                    cur_url = page.url
                    if cur_url.rstrip("/") == "https://gemini.google.com/app":
                        logger.info("gemini_conversation_already_at_root", url=conversation_url)
                        return True

                    # 2. Find and click the 3-dot menu button in top right corner
                    menu_candidates = [
                        "button:has(mat-icon[data-mat-icon-name='more_vert'])",
                        "button:has(mat-icon:has-text('more_vert'))",
                        "mat-icon[data-mat-icon-name='more_vert']",
                        "mat-icon:has-text('more_vert')",
                        "button[aria-label*='Thao tác' i]",
                        "button[aria-label*='Tùy chọn' i]",
                        "button[aria-label*='More' i]",
                        "button[aria-label*='more' i]",
                        "button[aria-label*='thêm' i]",
                        "header button[aria-haspopup='true']",
                        "header button[aria-haspopup='menu']",
                        "header button[aria-label*='menu' i]",
                        ".top-bar button[aria-haspopup='menu']",
                        "button.mat-mdc-menu-trigger",
                        "button[data-test-id*='more' i]",
                        "button[data-test-id*='action' i]",
                    ]

                    menu_btn = None
                    for sel in menu_candidates:
                        loc = page.locator(sel)
                        cnt = await loc.count()
                        for i in range(cnt):
                            btn = loc.nth(i)
                            if await btn.is_visible(timeout=500):
                                try:
                                    box = await btn.bounding_box()
                                    if box and box["y"] < 250:
                                        menu_btn = btn
                                        break
                                except Exception:
                                    menu_btn = btn
                                    break
                        if menu_btn is not None:
                            break

                    if menu_btn is None:
                        # Fallback: check any visible button with more options
                        loc = page.locator("button:has(mat-icon)")
                        cnt = await loc.count()
                        for i in range(cnt):
                            btn = loc.nth(i)
                            if await btn.is_visible(timeout=300):
                                aria = (await btn.get_attribute("aria-label", timeout=300) or "").lower()
                                if any(k in aria for k in ["tùy chọn", "thao tác", "more", "menu", "thêm"]):
                                    menu_btn = btn
                                    break

                    if menu_btn is not None:
                        logger.info("gemini_clicking_3dot_menu", url=conversation_url)
                        await menu_btn.click(timeout=3000)
                        await asyncio.sleep(0.8)
                    else:
                        logger.warning("gemini_3dot_menu_not_found", url=conversation_url)

                    # 3. Locate and click 'Xóa' / 'Xoá' option in the menu
                    delete_candidates = [
                        "[role='menuitem']:has-text('Xóa')",
                        "[role='menuitem']:has-text('Xoá')",
                        ".mat-mdc-menu-item:has-text('Xóa')",
                        ".mat-mdc-menu-item:has-text('Xoá')",
                        "button:has-text('Xóa')",
                        "button:has-text('Xoá')",
                        "div[role='menuitem']:has-text('Xóa')",
                        "div[role='menuitem']:has-text('Xoá')",
                        "span:has-text('Xóa')",
                        "span:has-text('Xoá')",
                        "[role='menuitem']:has(mat-icon[data-mat-icon-name*='delete'])",
                        "button:has(mat-icon[data-mat-icon-name*='delete'])",
                        "[role='menuitem']:has-text('Delete')",
                        ".mat-mdc-menu-item:has-text('Delete')",
                        "button:has-text('Delete')",
                        "span:has-text('Delete')",
                    ]

                    del_clicked = False
                    menu_deadline = time.monotonic() + 3.0
                    while time.monotonic() < menu_deadline:
                        for sel in delete_candidates:
                            loc = page.locator(sel)
                            if await loc.count() > 0 and await loc.first.is_visible(timeout=300):
                                logger.info("gemini_clicking_delete_option", selector=sel)
                                await loc.first.click(timeout=3000)
                                del_clicked = True
                                break
                        if del_clicked:
                            break
                        await asyncio.sleep(0.2)

                    if not del_clicked:
                        logger.warning("gemini_delete_option_not_found", url=conversation_url)

                    # 4. Handle confirmation modal: "Bạn muốn xoá cuộc trò chuyện?" / "Delete chat?"
                    logger.info("gemini_waiting_for_confirm_modal", url=conversation_url)
                    confirm_clicked = False
                    modal_deadline = time.monotonic() + 6.0
                    confirm_candidates = [
                        # Direct button inside dialog or modal
                        "[role='dialog'] button:has-text('Xóa')",
                        "[role='dialog'] button:has-text('Xoá')",
                        "[role='dialog'] button:has-text('Delete')",
                        "mat-dialog-container button:has-text('Xóa')",
                        "mat-dialog-container button:has-text('Xoá')",
                        "mat-dialog-container button:has-text('Delete')",
                        ".mat-mdc-dialog-container button:has-text('Xóa')",
                        ".mat-mdc-dialog-container button:has-text('Xoá')",
                        ".mat-mdc-dialog-container button:has-text('Delete')",
                        "mat-dialog-actions button:has-text('Xóa')",
                        "mat-dialog-actions button:has-text('Xoá')",
                        "mat-dialog-actions button:has-text('Delete')",
                        ".mat-mdc-dialog-actions button:has-text('Xóa')",
                        ".mat-mdc-dialog-actions button:has-text('Xoá')",
                        ".mat-mdc-dialog-actions button:has-text('Delete')",
                        # General modal container buttons
                        ".cdk-overlay-pane[role='dialog'] button:has-text('Xóa')",
                        ".cdk-overlay-pane[role='dialog'] button:has-text('Xoá')",
                        # Confirmation button by data-test-id
                        "button[data-test-id*='confirm' i]",
                        "button[data-test-id*='delete' i]",
                        # Last button in dialog actions (standard confirm button position)
                        "mat-dialog-actions button:last-child",
                        ".mat-mdc-dialog-actions button:last-child",
                        # Fallback: any visible button containing Xóa or Xoá
                        "button:has-text('Xóa')",
                        "button:has-text('Xoá')",
                    ]

                    while time.monotonic() < modal_deadline:
                        for sel in confirm_candidates:
                            loc = page.locator(sel)
                            try:
                                cnt = await loc.count()
                                if cnt > 0:
                                    for idx in range(cnt):
                                        btn = loc.nth(idx)
                                        if await btn.is_visible(timeout=300):
                                            # Validate button text is not cancel/hủy
                                            txt = (await btn.inner_text(timeout=200) or "").strip().lower()
                                            if any(c in txt for c in ["hủy", "huỷ", "cancel"]):
                                                continue
                                            logger.info("gemini_confirming_delete_modal_clicked", selector=sel, text=txt)
                                            await btn.click(timeout=3000)
                                            confirm_clicked = True
                                            break
                            except Exception:
                                pass
                            if confirm_clicked:
                                break
                        if confirm_clicked:
                            break
                        await asyncio.sleep(0.3)

                    if not confirm_clicked:
                        logger.warning("gemini_confirm_modal_not_clicked", url=conversation_url)

                    # 5. Wait for toast message starting with "Đã xóa..." or "Đã xoá..."
                    logger.info("gemini_waiting_for_delete_toast", url=conversation_url)
                    toast_detected = False
                    deadline = time.monotonic() + 15.0
                    while time.monotonic() < deadline:
                        # Check snackbar container elements
                        snackbars = page.locator(
                            "mat-snack-bar-container, "
                            ".mat-mdc-snack-bar-container, "
                            "snack-bar-container, "
                            "[role='status'], "
                            "[role='alert'], "
                            ".cdk-overlay-container"
                        )
                        cnt = await snackbars.count()
                        for idx in range(cnt):
                            sb = snackbars.nth(idx)
                            if await sb.is_visible(timeout=200):
                                txt = (await sb.inner_text(timeout=200)).strip()
                                lower_txt = txt.lower()
                                if any(k in lower_txt for k in ["đã xóa", "đã xoá", "deleted"]):
                                    logger.info("gemini_delete_toast_seen", text=txt, url=conversation_url)
                                    toast_detected = True
                                    break
                        if toast_detected:
                            break

                        # Regex text check on page
                        txt_loc = page.locator("text=/^Đã xo[áa]/i, text=/Đã xo[áa]/i, text=/^Deleted/i, text=/Chat deleted/i")
                        if await txt_loc.count() > 0:
                            for idx in range(await txt_loc.count()):
                                item = txt_loc.nth(idx)
                                if await item.is_visible(timeout=200):
                                    txt = (await item.inner_text(timeout=200)).strip()
                                    logger.info("gemini_delete_toast_seen_via_text", text=txt, url=conversation_url)
                                    toast_detected = True
                                    break
                        if toast_detected:
                            break

                        await asyncio.sleep(0.3)

                    await asyncio.sleep(0.5)  # Let server finalize delete

                    if toast_detected:
                        logger.info("gemini_conversation_deleted_successfully", url=conversation_url)
                        return True

                    # Fallback check: Did URL navigate away from the conversation ID?
                    if page.url.rstrip("/") == "https://gemini.google.com/app" or conversation_url not in page.url:
                        logger.info("gemini_conversation_url_changed_success", url=conversation_url)
                        return True

                    return False
                finally:
                    # 6. Close the browser / page for Gemini
                    try:
                        if self._session._ctx is not None and len(self._session._ctx.pages) <= 1:
                            await page.goto("about:blank")
                        else:
                            await page.close()
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("gemini_delete_conversation_error", url=conversation_url, error=str(exc))
            return False
