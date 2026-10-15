import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager
from app.adapters.capabilities.gemini import GeminiCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest


async def main():
    session = BrowserSessionManager.get_session("gemini")
    strategy = GeminiCapabilitiesStrategy()

    model_arg = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.8-flash"
    thinking_arg = sys.argv[2] if len(sys.argv) > 2 else "low"

    async with session.exclusive():
        page = await session.new_page("https://gemini.google.com/app")
        await asyncio.sleep(3.0)

        # 1. Apply model & thinking effort
        print(f"Applying selection: {model_arg} + {thinking_arg} Thinking...", flush=True)
        cfg = ProviderSelectionRequest(
            model_id=model_arg,
            thinking_level_id=thinking_arg,
        )
        await strategy.apply_selection(page, cfg)
        await asyncio.sleep(1.0)

        # 2. Find input box
        inp = page.locator("rich-textarea [contenteditable='true'], .ql-editor[contenteditable='true'], [role='textbox']").first
        await inp.wait_for(state="visible", timeout=10000)
        await inp.click()
        await asyncio.sleep(0.5)

        test_prompt = (
            "Generate a comprehensive showcase of all kinds of markdown components supported by Gemini. "
            "Please include:\n"
            "# H1 Main Title\n"
            "## H2 Section\n"
            "### H3 Subsection\n"
            "#### H4 Details\n"
            "- Formatted text: **Bold**, *Italic*, ~~Strikethrough~~, `inline code`\n"
            "- Blockquotes with nested quote\n"
            "- Ordered and Unordered lists with nested bullets\n"
            "- Task checkboxes ([x] done, [ ] todo)\n"
            "- A 4-column rich Markdown Table with alignment\n"
            "- Syntax-highlighted code blocks for Python, TypeScript, and SQL\n"
            "- LaTeX math equations: inline $E = mc^2$ and block display like $$\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$$\n"
            "- GitHub-style alerts/callouts like > [!NOTE] and > [!TIP]\n"
            "Make every section populated with realistic, helpful examples."
        )
        await inp.fill(test_prompt)
        await asyncio.sleep(0.8)

        # 3. Find send button
        send_btn = page.locator("button:has(mat-icon[data-mat-icon-name='arrow_upward']), button[aria-label*='Send' i], button[aria-label*='Gửi' i]").first
        if await send_btn.is_visible(timeout=3000):
            print("Clicking send button...", flush=True)
            await send_btn.click()
        else:
            print("Send button not visible, pressing Enter...", flush=True)
            await inp.press("Enter")

        # Wait and monitor response
        print("Waiting for generation to start and complete...", flush=True)
        for i in range(40):
            await asyncio.sleep(3.0)
            stop_btn = page.locator("button[aria-label*='Ngừng' i], button[aria-label*='Stop' i]")
            is_gen = await stop_btn.count() > 0
            body_text = await page.inner_text("body")
            has_error = "something went wrong" in body_text.lower()
            print(f"[{i*3}s] Generating: {is_gen}, Error: {has_error}", flush=True)
            if not is_gen and i > 3:
                print("Generation complete!", flush=True)
                break

        await page.screenshot(path="scratch/gemini_showcase_result.png")
        print("Saved screenshot to scratch/gemini_showcase_result.png", flush=True)

        # Extract answer container
        from app.adapters.html_utils import html_to_markdown
        ans_loc = page.locator("message-content, model-response message-content, model-response .markdown").last
        if await ans_loc.count() > 0:
            html = await ans_loc.inner_html()
            md = html_to_markdown(html, provider="gemini")
            with open("scratch/gemini_markdown_output.md", "w", encoding="utf-8") as f:
                f.write(md)
            print(f"Successfully extracted response ({len(md)} chars) to scratch/gemini_markdown_output.md", flush=True)
        else:
            print("Answer container locator not found", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
