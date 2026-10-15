import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright

async def find_visible_max():
    profile_dir = root / "data" / "profiles" / "qwen"
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="msedge",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://chat.qwen.ai/", timeout=25000, wait_until="domcontentloaded")
        await asyncio.sleep(4)
        
        model_btn = page.locator("div.wms-trigger, [class*='mode-select'] div.wms-trigger").first
        await model_btn.click()
        await asyncio.sleep(1.0)
        
        # Test clicking using text selector with visible=True or filter
        loc = page.locator("div, span, button").filter(has_text="Qwen3.8-Max")
        cnt = await loc.count()
        print(f"Total matching elements: {cnt}")
        for i in range(cnt):
            elem = loc.nth(i)
            vis = await elem.is_visible()
            tag = await elem.evaluate("el => el.tagName + '.' + el.className")
            print(f"[{i}] visible={vis}, tag={tag}")
            if vis:
                # Try clicking the visible one!
                print(f"Clicking visible element {i}...")
                await elem.click(timeout=3000)
                await asyncio.sleep(1.5)
                break
                
        new_text = (await model_btn.inner_text()).strip()
        print("Model button after click:", new_text)
        await context.close()

if __name__ == "__main__":
    asyncio.run(find_visible_max())
