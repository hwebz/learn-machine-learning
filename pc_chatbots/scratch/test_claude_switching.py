import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

async def test_switch():
    profile_dir = root / "data" / "profiles" / "claude"
    print("Testing Claude model and effort switching...")
    
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
        
        # Test 1: Switch to Sonnet 5.5
        model_btn = page.locator("button[data-testid='model-selector-dropdown'], button[aria-label*='Model']")
        curr_text = (await model_btn.first.inner_text()).strip()
        print(f"Current button text: '{curr_text}'")
        
        await model_btn.first.click()
        await asyncio.sleep(0.8)
        
        sonnet_opt = page.locator("[role='menuitemradio']:has-text('Sonnet')")
        if await sonnet_opt.count() > 0:
            print("Clicking Sonnet 5.5...")
            await sonnet_opt.first.click()
            await asyncio.sleep(1.2)
            
        new_text = (await model_btn.first.inner_text()).strip()
        print(f"After switching to Sonnet, button text: '{new_text}'")
        
        # Test 2: Switch Effort to High
        await model_btn.first.click()
        await asyncio.sleep(0.8)
        
        effort_item = page.locator("[role='menuitem']:has-text('Effort')")
        if await effort_item.count() > 0:
            print("Clicking Effort submenu...")
            await effort_item.first.click()
            await asyncio.sleep(0.8)
            
            high_opt = page.locator("[role='menuitemradio']:has-text('High')")
            if await high_opt.count() > 0:
                print("Clicking High effort...")
                await high_opt.first.click()
                await asyncio.sleep(1.2)
                
        after_effort_text = (await model_btn.first.inner_text()).strip()
        print(f"After switching effort to High, button text: '{after_effort_text}'")
        
        # Test 3: Switch back to Haiku and Medium
        await model_btn.first.click()
        await asyncio.sleep(0.8)
        haiku_opt = page.locator("[role='menuitemradio']:has-text('Haiku')")
        if await haiku_opt.count() > 0:
            await haiku_opt.first.click()
            await asyncio.sleep(1.0)
            
        await model_btn.first.click()
        await asyncio.sleep(0.8)
        effort_item = page.locator("[role='menuitem']:has-text('Effort')")
        if await effort_item.count() > 0:
            await effort_item.first.click()
            await asyncio.sleep(0.8)
            med_opt = page.locator("[role='menuitemradio']:has-text('Medium')")
            if await med_opt.count() > 0:
                await med_opt.first.click()
                await asyncio.sleep(1.0)
                
        final_text = (await model_btn.first.inner_text()).strip()
        print(f"Final button text: '{final_text}'")
        
        await context.close()
        print("Switch test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_switch())
