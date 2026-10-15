import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright

async def check_expanded():
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
        
        model_btn = page.locator("div.wms-trigger, [class*='mode-select'] div.wms-trigger")
        if await model_btn.count() > 0:
            await model_btn.first.click()
            await asyncio.sleep(1.0)
            
            expand_btn = page.locator("div:has-text('Expand more models'), [class*='expand']")
            if await expand_btn.count() > 0:
                await expand_btn.first.hover()
                await asyncio.sleep(0.5)
                await expand_btn.first.click()
                await asyncio.sleep(1.0)
                await page.screenshot(path=str(root / "data" / "artifacts" / "qwen_expanded_models.png"))
                
        await context.close()

if __name__ == "__main__":
    asyncio.run(check_expanded())
