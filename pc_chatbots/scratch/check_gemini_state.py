import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager


async def main():
    session = BrowserSessionManager.get_session("gemini")
    async with session.exclusive():
        if session._ctx and session._ctx.pages:
            page = session._ctx.pages[0]
            await page.screenshot(path="scratch/gemini_current_state.png")
            print("Screenshot saved to scratch/gemini_current_state.png")
            print("Current URL:", page.url)
            body = await page.inner_text("body")
            print("Body snippet (first 500 chars):")
            print(body[:500])
        else:
            print("No pages open in Gemini session")


if __name__ == "__main__":
    asyncio.run(main())
