"""Open the automation profile at providers that need login, then wait.

Unlike login_profile.py (which waits for Enter on stdin — not available when
run from Claude Code), this opens all requested provider tabs at once and
waits until the user closes the browser window, or a fixed timeout elapses.
Login cookies persist in the profile either way.
"""
from __future__ import annotations

import argparse
import asyncio

from app.adapters.selectors_loader import load_selectors, provider_selectors
from app.browser.session import BrowserSession
from app.core.config import settings


def _provider_urls(provider_name: str | None) -> list[tuple[str, str]]:
    selectors = load_selectors()
    names = [provider_name] if provider_name else list(selectors.get("providers", {}).keys())
    urls: list[tuple[str, str]] = []
    for name in names:
        try:
            cfg = provider_selectors(selectors, name)
            urls.append((name, cfg["new_chat_url"]))
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {name}: {exc}")
    return urls


async def main() -> int:
    parser = argparse.ArgumentParser(description="Open provider tabs for manual login, then wait")
    parser.add_argument("--provider", default=None, help="One provider (e.g. claude) or all by default")
    parser.add_argument("--wait-s", type=int, default=600, help="Max seconds to hold the browser open (default 600).")
    args = parser.parse_args()

    urls = _provider_urls(args.provider)
    if not urls:
        print(f"No valid providers found matching: {args.provider}")
        return 1

    print(f"Profile dir: {settings.browser_profile_dir.resolve()}")
    print(f"Opening {len(urls)} provider tab(s). Log in where needed.")
    print(f"Browser stays open for {args.wait_s}s (or close the window when done).")

    session = BrowserSession.instance()
    try:
        await session.start()
        pages = []
        for name, url in urls:
            page = await session.new_page(url)
            pages.append((name, page))
            print(f"[open] {name}: {url}")
        print("\nLog in now in the browser window. Waiting...")
        await asyncio.sleep(args.wait_s)
        print("Wait elapsed; closing browser. Login state saved to profile.")
    finally:
        await session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
