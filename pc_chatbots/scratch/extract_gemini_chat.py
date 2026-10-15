import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager
from app.browser.converters import html_to_markdown


async def main():
    session = BrowserSessionManager.get_session("gemini")
    async with session.exclusive():
        page = await session.new_page("https://gemini.google.com/app")
        await asyncio.sleep(3.0)

        # 1. Click on the first chat in the left history list ("Markdown Showcase")
        first_chat = page.locator("a[data-test-id='conversation-list-item'], .conversation-title, nav a:has-text('Markdown Showcase')").first
        if await first_chat.is_visible(timeout=5000):
            print("Opening 'Markdown Showcase' chat...")
            await first_chat.click()
            await asyncio.sleep(3.0)

        # 2. Extract full response content
        # Attempt copy button first
        copy_btn = page.locator("button[aria-label*='Sao chép' i]:not([aria-label*='lệnh' i]), button[aria-label*='Copy' i]").last
        extracted_text = ""
        if await copy_btn.is_visible(timeout=3000):
            try:
                await page.evaluate("navigator.clipboard.writeText('')")
                await copy_btn.click()
                await asyncio.sleep(0.5)
                extracted_text = await page.evaluate("navigator.clipboard.readText()")
                print(f"Copied {len(extracted_text)} chars from clipboard!")
            except Exception as e:
                print(f"Clipboard copy error: {e}")

        # Fallback to HTML extraction
        if not extracted_text:
            ans_loc = page.locator("message-content, model-response message-content, model-response .markdown").last
            if await ans_loc.count() > 0:
                html = await ans_loc.inner_html()
                extracted_text = html_to_markdown(html, provider="gemini")
                print(f"Extracted {len(extracted_text)} chars from HTML!")

        if extracted_text:
            with open("scratch/gemini_showcase_content.md", "w", encoding="utf-8") as f:
                f.write(extracted_text)
            print("Successfully saved to scratch/gemini_showcase_content.md!")
            print("--- Content Preview ---")
            print(extracted_text[:1500])
        else:
            print("Failed to extract content.")


if __name__ == "__main__":
    asyncio.run(main())
