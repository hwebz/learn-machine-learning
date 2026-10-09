"""Probe the live login screen to find the remembered-account tile structure."""
from __future__ import annotations

import asyncio

from app.adapters.selectors_loader import provider_selectors
from app.browser.session import BrowserSession


async def main() -> int:
    session = BrowserSession.instance()
    try:
        await session.start()
        cfg = provider_selectors(__import__("app.adapters.selectors_loader", fromlist=["load_selectors"]).load_selectors(), "copilot")
        page = await session.new_page(cfg["new_chat_url"])
        print("URL:", page.url)
        await asyncio.sleep(3)
        print("URL after settle:", page.url)
        html = await page.locator("body").inner_html(timeout=5000)
        print("BODY HTML (first 6000 chars):")
        print(html[:6000])
        # Look for clickable account tiles
        for sel in ["[data-test-id]", "[role='option']", "[role='button']", "div.table", "#tiles", ".tile"]:
            try:
                count = await page.locator(sel).count()
                print(f"\nselector {sel!r}: count={count}")
                if 0 < count <= 5:
                    for i in range(count):
                        el = page.locator(sel).nth(i)
                        outer = await el.evaluate("el => el.outerHTML.substring(0, 300)")
                        print(f"  [{i}] {outer}")
            except Exception as exc:
                print(f"  error: {exc}")
        await page.close()
    finally:
        await session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
