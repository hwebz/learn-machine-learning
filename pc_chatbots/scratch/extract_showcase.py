import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager
from app.browser.converters import html_to_markdown


async def test():
    s = BrowserSessionManager.get_session("gemini")
    async with s.exclusive():
        p = await s.new_page("https://gemini.google.com/app/2a5e1277fda20e89")
        await asyncio.sleep(4.0)

        # Take full screenshot
        await p.screenshot(path="scratch/gemini_showcase_full_page.png")
        print("Saved scratch/gemini_showcase_full_page.png")

        # Find answer containers
        containers = p.locator("message-content, model-response")
        cnt = await containers.count()
        print(f"Found {cnt} response containers")

        last_container = containers.last
        html = await last_container.inner_html()
        md = html_to_markdown(html, provider="gemini")

        # Also get inner_text as baseline
        text = await last_container.inner_text()

        with open("scratch/gemini_extracted_markdown.md", "w", encoding="utf-8") as f:
            f.write(md if len(md) > 200 else text)

        print(f"Wrote {len(md if len(md) > 200 else text)} chars to scratch/gemini_extracted_markdown.md")
        print("--- Markdown Preview ---")
        lines = (md if len(md) > 200 else text).splitlines()
        for l in lines[:40]:
            print(l)


if __name__ == "__main__":
    asyncio.run(test())
