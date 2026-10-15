import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

async def inspect():
    profile_dir = root / "data" / "profiles" / "claude"
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="msedge",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://claude.ai/new", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 1. Open model dropdown
        model_btn = page.locator("button[data-testid='model-selector-dropdown'], button[aria-label*='Model']")
        await model_btn.first.click()
        await asyncio.sleep(1)
        
        # 2. Inspect Effort item
        effort_item = page.locator("[role='menuitem']:has-text('Effort')")
        if await effort_item.count() > 0:
            print("Found Effort item! Hovering or clicking...")
            await effort_item.first.click()
            await asyncio.sleep(1)
            
            # Look for sub-menu or dialog
            sub_items = page.locator("[role='menuitem'], [role='menuitemradio'], [role='option'], div:has-text('Low'), div:has-text('Medium'), div:has-text('High')")
            cnt = await sub_items.count()
            print(f"Items visible after clicking Effort ({cnt}):")
            for i in range(cnt):
                el = sub_items.nth(i)
                if await el.is_visible():
                    t = (await el.inner_text()).strip().replace("\n", " | ")
                    print(f"   Sub [{i}]: role='{await el.get_attribute('role')}' text='{t}'")
                    
        # Also check More models item
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        await model_btn.first.click()
        await asyncio.sleep(1)
        
        more_item = page.locator("[role='menuitem']:has-text('More models')")
        if await more_item.count() > 0:
            print("\nFound More models item! Clicking...")
            await more_item.first.click()
            await asyncio.sleep(1)
            more_sub = page.locator("[role='menuitem'], [role='menuitemradio']")
            for i in range(await more_sub.count()):
                el = more_sub.nth(i)
                if await el.is_visible():
                    t = (await el.inner_text()).strip().replace("\n", " | ")
                    print(f"   More [{i}]: text='{t}'")

        await context.close()

if __name__ == "__main__":
    asyncio.run(inspect())
