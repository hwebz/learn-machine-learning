import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager


async def test():
    s = BrowserSessionManager.get_session("gemini")
    async with s.exclusive():
        p = await s.new_page("https://gemini.google.com/app")
        await asyncio.sleep(4.0)
        items = p.locator("a[href*='/app/'], .conversation, [data-test-id*='conversation']")
        cnt = await items.count()
        print(f"Found {cnt} matching items:")
        for i in range(cnt):
            it = items.nth(i)
            txt = (await it.inner_text()).strip().replace("\n", " | ")
            href = await it.get_attribute("href")
            print(f"[{i}] {txt} -> {href}")


if __name__ == "__main__":
    asyncio.run(test())
