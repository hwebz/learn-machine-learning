import asyncio
import sys
from pathlib import Path

# Add pc_chatbots root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright

async def inspect():
    profile_dir = root / "data" / "profiles" / "qwen"
    print(f"Opening Qwen with profile {profile_dir}...")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="msedge",
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        print("Navigating to https://chat.qwenlm.ai/ ...")
        try:
            await page.goto("https://chat.qwenlm.ai/", timeout=25000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"Navigation warning: {e}")
        
        await asyncio.sleep(4)
        print("Current page URL:", page.url)
        print("Page title:", await page.title())
        
        # Check for model selectors
        print("\n--- Searching for potential model buttons ---")
        locators_to_check = [
            "div.wms-trigger",
            "[class*='mode-select']",
            "[class*='model-select']",
            "button:has-text('Qwen')",
            "div:has-text('Qwen')",
            "button:has-text('Max')",
            "button:has-text('Plus')",
            "[class*='header'] button",
            "[class*='model']",
            ".qwen-thinking-selector",
            "[class*='thinking']",
        ]
        
        for sel in locators_to_check:
            loc = page.locator(sel)
            cnt = await loc.count()
            if cnt > 0:
                print(f"Selector '{sel}': found {cnt} elements")
                for i in range(min(cnt, 5)):
                    try:
                        txt = (await loc.nth(i).inner_text()).strip().replace("\n", " | ")
                        print(f"   [{i}]: text='{txt}'")
                    except Exception:
                        pass
        
        # Capture screenshot for visual verification
        screenshot_path = root / "data" / "artifacts" / "qwen_inspect_live.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"\nScreenshot saved to {screenshot_path}")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(inspect())
