from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, ClassVar

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Playwright is imported lazily so that importing this module never requires
# the playwright runtime (tests, health checks, fake/api modes). Only the UI
# adapters actually drive a browser, so they call BrowserSession.start() which
# performs the import.


class BrowserSession:
    """Singleton persistent Chromium context backed by the dedicated profile dir.

    Guarantees (per PLAN.md §6):
      - One browser session at a time: a single ``asyncio.Lock`` serializes asks.
      - Persistent profile reused across runs (login persists).
      - Dedicated automation profile only — never the user's daily profile.
      - Headed in V1 (``headless=False``), ``channel="chrome"``.

    Usage::

        async with BrowserSession.exclusive() as page_factory:
            page = await BrowserSession.new_page("https://...")
            ...
    """

    _instance: ClassVar[BrowserSession | None] = None

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._pw: Any = None
        self._ctx: Any = None

    # ------------------------------------------------------------------ lifecycle

    @classmethod
    def instance(cls) -> BrowserSession:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Idempotently launch the persistent context if not already running.

        Safe to call from inside ``exclusive()`` (which already holds the lock):
        the lock is only taken when the context needs to be created, and the
        early-return path does not block on it.
        """
        if self._ctx is not None:
            return  # already started — no lock needed (re-entrant safe)
        async with self._lock:
            # Re-check inside the lock: another task may have started it.
            if self._ctx is not None:
                return
            from playwright.async_api import async_playwright

            profile_dir = settings.browser_profile_dir
            profile_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                "browser_session_starting",
                profile=str(profile_dir),
                channel=settings.browser_channel,
                headless=settings.browser_headless,
            )
            pw = await async_playwright().start()
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                channel=settings.browser_channel,
                headless=settings.browser_headless,
                args=["--disable-blink-features=AutomationControlled"],
                permissions=["clipboard-read", "clipboard-write"],
                viewport={"width": 1280, "height": 900},
            )
            self._pw = pw
            self._ctx = ctx

    async def close(self) -> None:
        """Close the context and stop Playwright. Safe to call when not started."""
        async with self._lock:
            ctx, pw = self._ctx, self._pw
            self._ctx = None
            self._pw = None
        if ctx is not None:
            try:
                await ctx.close()
            except Exception:
                logger.exception("browser_context_close_failed")
        if pw is not None:
            try:
                await pw.stop()
            except Exception:
                logger.exception("browser_playwright_stop_failed")

    # ------------------------------------------------------------------ pages

    async def new_page(self, url: str) -> Any:
        """Open a new tab at ``url`` against the persistent context.

        Waits for ``domcontentloaded`` (30s cap) then a short settle delay so
        SPAs (Perplexity, Gemini) can hydrate before the caller probes the DOM.
        Never hangs: navigation timeouts are logged, not raised.
        """
        import asyncio

        await self.start()
        assert self._ctx is not None  # narrowed for type checkers
        page = await self._ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:  # noqa: BLE001 — don't hang on slow SPA navigation
            logger.warning("page_goto_slow", url=url, error=str(exc))
        # SPAs with persistent sockets never reach networkidle, so a short
        # settle delay is more reliable than wait_for_load_state here.
        await asyncio.sleep(2.0)
        return page

    @asynccontextmanager
    async def exclusive(self) -> AsyncIterator[None]:
        """Hold the global lock for the duration of one provider ask().

        Ensures only one browser interaction runs at a time. The persistent
        context is started (if needed) before acquiring the lock.
        """
        await self.start()
        async with self._lock:
            yield


async def close_browser_session() -> None:
    """Convenience hook used by the app lifespan shutdown."""
    await BrowserSession.instance().close()
