from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.browser.session import BrowserSession
from app.core.config import settings


import argparse


def _provider_urls(provider_name: str | None = None) -> list[tuple[str, str]]:
    from app.adapters.selectors_loader import load_selectors, provider_selectors

    selectors = load_selectors()
    urls: list[tuple[str, str]] = []
    providers = [provider_name] if provider_name else list(selectors.get("providers", {}).keys())
    for name in providers:
        try:
            cfg = provider_selectors(selectors, name)
            urls.append((name, cfg["new_chat_url"]))
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] {name}: {exc}")
    return urls


async def main() -> int:
    """Open the automation Chrome profile at chatbot sites so you can log in once.

    The profile persists under BROWSER_PROFILE_DIR. After logging in, press Enter
    in this terminal to close the browser cleanly. Login cookies are stored in the
    profile — this script never extracts or logs them.
    """
    parser = argparse.ArgumentParser(description="Log in to chatbot sites with persistent Chrome profile")
    parser.add_argument("--provider", default=None, help="Specific provider to open (e.g. chatgpt, claude)")
    parser.add_argument("--mode", default=None, choices=["sync", "async"], help="Override WORK_MODE (defaults to .env)")
    args = parser.parse_args()

    mode = args.mode or settings.work_mode
    print(f"Current WORK_MODE: {mode.upper()}")
    print("A headed Chrome window will open at each chatbot site.")
    print("Sign in to any site that shows a login page, then return here.\n")

    urls = _provider_urls(args.provider)
    if not urls:
        print(f"No valid providers found matching: {args.provider}")
        return 1

    from app.browser.session import BrowserSessionManager

    if mode == "sync":
        profile_dir = settings.browser_profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Sync mode] Using shared profile: {profile_dir.resolve()}\n")
        session = BrowserSession.instance()
        try:
            await session.start()
            for name, url in urls:
                page = await session.new_page(url)
                print(f"Opened {name}: {url}")
                try:
                    await asyncio.to_thread(input, f"Log in to {name} if needed, then press Enter to continue... ")
                finally:
                    try:
                        await page.close()
                    except Exception:  # noqa: BLE001
                        pass
        finally:
            await session.close()
    else:
        print("[Async mode] Using dedicated profile per provider under ./data/profiles/<provider>\n")
        for name, url in urls:
            session = BrowserSessionManager.get_session(name)
            print(f"[{name}] Profile dir: {session.profile_dir.resolve()}")
            try:
                await session.start()
                page = await session.new_page(url)
                print(f"Opened {name}: {url}")
                try:
                    await asyncio.to_thread(input, f"Log in to {name} if needed, then press Enter to continue... ")
                finally:
                    try:
                        await page.close()
                    except Exception:  # noqa: BLE001
                        pass
            finally:
                await session.close()

    print("\nLogin state saved to the profile. You can close this terminal.")
    print("Validate selectors next with: python scripts/smoke_test.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
