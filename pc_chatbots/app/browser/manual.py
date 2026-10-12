from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, ClassVar

import structlog
from playwright.async_api import async_playwright

from app.adapters.selectors_loader import load_selectors, provider_selectors
from app.browser.session import BrowserSessionManager
from app.core.config import get_provider_profile_dir, settings

logger = structlog.get_logger(__name__)

DEFAULT_PROVIDER_URLS: dict[str, str] = {
    "perplexity": "https://www.perplexity.ai/",
    "gemini": "https://gemini.google.com/app",
    "chatgpt": "https://chatgpt.com/",
    "claude": "https://claude.ai/new",
    "deepseek": "https://chat.deepseek.com/",
    "copilot": "https://copilot.microsoft.com/",
    "qwen": "https://chat.qwenlm.ai/",
    "grok": "https://x.com/i/grok",
    "mistral": "https://chat.mistral.ai/chat",
}


class ManualBrowserManager:
    """Manages headed browser windows launched manually for user sign-in or CAPTCHA resolution."""

    _active_contexts: ClassVar[dict[str, Any]] = {}
    _active_playwrights: ClassVar[dict[str, Any]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    def get_provider_url(cls, provider: str) -> str:
        prov = provider.lower().strip()
        try:
            selectors = load_selectors()
            cfg = provider_selectors(selectors, prov)
            url = cfg.get("new_chat_url")
            if url:
                return url
        except Exception:
            pass
        return DEFAULT_PROVIDER_URLS.get(prov, f"https://www.{prov}.com/")

    @classmethod
    def is_open(cls, provider: str) -> bool:
        prov = provider.lower().strip()
        return prov in cls._active_contexts

    @classmethod
    async def open_browser(cls, provider: str, url: str | None = None) -> dict[str, Any]:
        """Launch a headed browser window with the provider profile for manual login."""
        prov = provider.lower().strip()
        async with cls._lock:
            # 1. Close any automated pipeline session for this provider first to release profile lock
            try:
                await BrowserSessionManager.close_session(prov)
            except Exception as exc:
                logger.warning("close_automated_session_before_manual_error", provider=prov, error=str(exc))

            # 2. Check if already open
            target_url = url or cls.get_provider_url(prov)
            existing_ctx = cls._active_contexts.get(prov)
            if existing_ctx is not None:
                try:
                    pages = existing_ctx.pages
                    if pages:
                        page = pages[0]
                        await page.bring_to_front()
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                    else:
                        page = await existing_ctx.new_page()
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                    return {
                        "status": "already_open",
                        "provider": prov,
                        "url": target_url,
                        "message": f"Browser already open for {prov}. Focused window.",
                    }
                except Exception:
                    # Stale context, close and re-launch
                    await cls._close_unlocked(prov)

            profile_dir = get_provider_profile_dir(prov)
            profile_dir.mkdir(parents=True, exist_ok=True)

            logger.info("manual_browser_opening", provider=prov, profile=str(profile_dir), url=target_url)

            pw = await async_playwright().start()

            launch_kwargs: dict[str, Any] = {
                "user_data_dir": str(profile_dir),
                "headless": False,  # Always headed so user can sign in interactively
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ],
                "permissions": ["clipboard-read", "clipboard-write"],
                "viewport": {"width": 1280, "height": 900},
            }
            if settings.browser_executable and Path(settings.browser_executable).is_file():
                launch_kwargs["executable_path"] = settings.browser_executable
            elif settings.browser_channel and settings.browser_channel != "chromium":
                launch_kwargs["channel"] = settings.browser_channel

            try:
                ctx = await pw.chromium.launch_persistent_context(**launch_kwargs)
            except Exception as exc:
                try:
                    await pw.stop()
                except Exception:
                    pass
                logger.error("manual_browser_launch_failed", provider=prov, error=str(exc))
                raise RuntimeError(
                    f"Failed to launch browser for {prov}: {exc}. "
                    "Make sure no other browser process is using this profile."
                ) from exc

            def _on_close() -> None:
                logger.info("manual_browser_closed_by_user", provider=prov)
                cls._active_contexts.pop(prov, None)
                pw_inst = cls._active_playwrights.pop(prov, None)
                if pw_inst is not None:
                    try:
                        asyncio.create_task(pw_inst.stop())
                    except Exception:
                        pass

            ctx.on("close", lambda: _on_close())
            cls._active_contexts[prov] = ctx
            cls._active_playwrights[prov] = pw

            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                logger.warning("manual_browser_goto_slow", provider=prov, url=target_url, error=str(exc))

            return {
                "status": "opened",
                "provider": prov,
                "url": target_url,
                "profile_dir": str(profile_dir),
                "message": f"Browser opened for {prov}. Sign in, then return and continue.",
            }

    @classmethod
    async def _close_unlocked(cls, provider: str) -> None:
        prov = provider.lower().strip()
        ctx = cls._active_contexts.pop(prov, None)
        pw = cls._active_playwrights.pop(prov, None)
        if ctx is not None:
            try:
                await ctx.close()
            except Exception as exc:
                logger.debug("manual_browser_ctx_close_error", provider=prov, error=str(exc))
        if pw is not None:
            try:
                await pw.stop()
            except Exception as exc:
                logger.debug("manual_browser_pw_stop_error", provider=prov, error=str(exc))

    @classmethod
    async def close_browser(cls, provider: str) -> dict[str, Any]:
        """Close the manual browser window for a provider so profile is unlocked."""
        prov = provider.lower().strip()
        async with cls._lock:
            await cls._close_unlocked(prov)
            return {"status": "closed", "provider": prov}

    @classmethod
    async def close_all(cls) -> None:
        """Close all manual browser windows."""
        async with cls._lock:
            for prov in list(cls._active_contexts.keys()):
                await cls._close_unlocked(prov)
