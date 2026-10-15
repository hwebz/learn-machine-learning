import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager


async def main():
    session = BrowserSessionManager.get_session("mistral")

    async with session.exclusive():
        page = await session.new_page("https://chat.mistral.ai/chat")
        await asyncio.sleep(4.0)

        print(f"Page loaded: {page.url}", flush=True)

        # Screenshot initial state
        out_img = Path("scratch/mistral_initial.png")
        await page.screenshot(path=str(out_img))
        print(f"Screenshot saved to {out_img}", flush=True)

        # Inspect all buttons and dropdowns around input
        print("\n--- Buttons on Mistral Page ---", flush=True)
        buttons = await page.locator("button").all()
        for idx, b in enumerate(buttons):
            lbl = (await b.get_attribute("aria-label")) or ""
            tid = (await b.get_attribute("data-testid")) or ""
            txt = (await b.inner_text()).strip()
            cls = (await b.get_attribute("class")) or ""
            vis = await b.is_visible()
            if vis:
                print(f"[{idx}] text={txt!r} label={lbl!r} testid={tid!r} class={cls[:40]!r}")

        # Save HTML for analysis
        html_out = Path("scratch/mistral_initial.html")
        html_out.write_text(await page.content(), encoding="utf-8")
        print(f"HTML saved to {html_out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
