import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

async def inspect():
    profile_dir = root / "data" / "profiles" / "deepseek"
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="msedge",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://chat.deepseek.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        buttons = await page.locator(".ds-toggle-button").all()
        print(f"Total .ds-toggle-button elements: {len(buttons)}")
        for idx, btn in enumerate(buttons):
            text = (await btn.inner_text()).strip()
            aria = await btn.get_attribute("aria-pressed") or await btn.get_attribute("aria-checked")
            cls = await btn.get_attribute("class") or ""
            print(f"Button {idx}: text='{text}', aria={aria}, class='{cls}'")
            
        # Also check any other toggle buttons or icons around textarea
        area_btns = await page.locator("button, [role='button']").all()
        for b in area_btns:
            t = (await b.inner_text()).strip()
            if any(k in t.lower() for k in ["deepthink", "search", "tìm", "web"]):
                aria = await b.get_attribute("aria-pressed") or await b.get_attribute("aria-checked")
                cls = await b.get_attribute("class") or ""
                print(f"Candidate button text='{t}', aria={aria}, class='{cls}'")
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(inspect())
