from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, ClassVar

import structlog

from pathlib import Path

from app.core.config import get_provider_profile_dir, settings

logger = structlog.get_logger(__name__)

# Playwright is imported lazily so that importing this module never requires
# the playwright runtime (tests, health checks, fake/api modes). Only the UI
# adapters actually drive a browser, so they call BrowserSession.start() which
# performs the import.


class BrowserSession:
    """Persistent Chromium context backed by a dedicated profile dir.

    Supports:
      - Dedicated profile directory per session (isolated cookies/storage).
      - Reusable Chromium context with anti-background-throttling flags.
      - Per-session lock to prevent concurrent tab collisions within the same profile.
      - Singleton backward-compatible access via `BrowserSession.instance()`.
    """

    _instance: ClassVar[BrowserSession | None] = None

    def __init__(self, profile_dir: Path | None = None) -> None:
        self.profile_dir = profile_dir or settings.browser_profile_dir
        self._lock = asyncio.Lock()
        self._pw: Any = None
        self._ctx: Any = None

    # ------------------------------------------------------------------ lifecycle

    @classmethod
    def instance(cls) -> BrowserSession:
        if cls._instance is None:
            cls._instance = cls(profile_dir=settings.browser_profile_dir)
        return cls._instance

    async def start(self, headless: bool | None = None) -> None:
        """Idempotently launch the persistent context if not already running."""
        if self._ctx is not None:
            return
        async with self._lock:
            if self._ctx is not None:
                return
            from playwright.async_api import async_playwright

            self.profile_dir.mkdir(parents=True, exist_ok=True)
            use_headless = settings.browser_headless if headless is None else headless
            logger.info(
                "browser_session_starting",
                profile=str(self.profile_dir),
                channel=settings.browser_channel,
                headless=use_headless,
            )
            pw = await async_playwright().start()
            max_attempts = 3
            ctx = None
            last_err: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    ctx = await pw.chromium.launch_persistent_context(
                        user_data_dir=str(self.profile_dir),
                        channel=settings.browser_channel,
                        headless=use_headless,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-background-timer-throttling",
                            "--disable-backgrounding-occluded-windows",
                            "--disable-renderer-backgrounding",
                        ],
                        permissions=["clipboard-read", "clipboard-write"],
                        viewport={"width": 1280, "height": 900},
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    logger.warning(
                        "browser_launch_retry",
                        profile=str(self.profile_dir),
                        attempt=attempt,
                        max_attempts=max_attempts,
                        error=str(exc),
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(1.5)

            if ctx is None:
                await pw.stop()
                raise last_err or RuntimeError(f"Failed to launch browser persistent context for {self.profile_dir}")

            ctx.on("close", lambda: setattr(self, "_ctx", None))
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
        """Open a tab at ``url`` against the persistent context."""
        await self.start()
        try:
            assert self._ctx is not None
            _ = self._ctx.pages
        except Exception:
            logger.warning("browser_context_dead_restarting", profile=str(self.profile_dir))
            await self.close()
            await self.start()

        assert self._ctx is not None

        page = None
        try:
            for existing in self._ctx.pages:
                if existing.url in ("about:blank", "") and not existing.is_closed():
                    page = existing
                    logger.info("page_reused_blank_tab", profile=str(self.profile_dir))
                    break
        except Exception:  # noqa: BLE001
            page = None

        if page is None:
            page = await self._ctx.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:  # noqa: BLE001
            logger.warning("page_goto_slow", url=url, error=str(exc))
        await asyncio.sleep(1.0)
        return page

    @asynccontextmanager
    async def exclusive(self) -> AsyncIterator[None]:
        """Hold the session lock for the duration of one provider ask()."""
        await self.start()
        async with self._lock:
            yield


class BrowserSessionManager:
    """Manages browser sessions across providers and execution modes."""

    _sessions: ClassVar[dict[str, BrowserSession]] = {}
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    def get_session(cls, provider: str = "main") -> BrowserSession:
        """Return the appropriate BrowserSession based on WORK_MODE and provider."""
        if settings.work_mode == "sync":
            return BrowserSession.instance()

        key = provider.lower()
        session = cls._sessions.get(key)
        if session is None:
            profile = get_provider_profile_dir(key, mode="async")
            session = BrowserSession(profile_dir=profile)
            cls._sessions[key] = session
        return session

    @classmethod
    async def close_session(cls, provider: str = "main") -> None:
        """Close and remove a specific session from the pool."""
        if settings.work_mode == "sync":
            return
        key = provider.lower()
        async with cls._lock:
            session = cls._sessions.pop(key, None)
        if session is not None:
            await session.close()

    @classmethod
    async def close_all(cls) -> None:
        """Close all pooled sessions and the singleton session."""
        async with cls._lock:
            for session in list(cls._sessions.values()):
                await session.close()
            cls._sessions.clear()
            if BrowserSession._instance is not None:
                await BrowserSession._instance.close()


async def close_browser_session() -> None:
    """Convenience hook used by the app lifespan shutdown."""
    await BrowserSessionManager.close_all()
