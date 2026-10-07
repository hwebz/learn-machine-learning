from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.browser.session import BrowserSession
from app.core.config import settings


def _provider_urls() -> list[tuple[str, str]]:
    from app.adapters.selectors_loader import load_selectors, provider_selectors

    selectors = load_selectors()
    urls: list[tuple[str, str]] = []
    for name in ("perplexity", "gemini"):
        try:
            cfg = provider_selectors(selectors, name)
            urls.append((name, cfg["new_chat_url"]))
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {name}: {exc}")
    return urls


async def main() -> int:
    """Open the automation Chrome profile at both chatbot sites so you can log in once.

    The profile persists under BROWSER_PROFILE_DIR. After logging in, press Enter
    in this terminal to close the browser cleanly. Login cookies are stored in the
    profile — this script never extracts or logs them.
    """
    profile_dir: Path = settings.browser_profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)
    print(f"Profile dir: {profile_dir.resolve()}")
    print("A headed Chrome window will open at each chatbot site.")
    print("Sign in to any site that shows a login page, then return here.\n")

    session = BrowserSession.instance()
    try:
        await session.start()
        for name, url in _provider_urls():
            page = await session.new_page(url)
            print(f"Opened {name}: {url}")
            try:
                await asyncio.to_thread(input, "Log in if needed, then press Enter to open the next site... ")
            finally:
                try:
                    await page.close()
                except Exception:  # noqa: BLE001
                    pass
        print("\nLogin state saved to the profile. You can close this terminal.")
        print("Validate selectors next with: python scripts/smoke_test.py")
    finally:
        await session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
