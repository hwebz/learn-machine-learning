import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.async_api import async_playwright

async def test_toggle():
    profile_dir = root / "data" / "profiles" / "deepseek"
    print("Testing DeepSeek DeepThink toggle...")
    
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
        await page.goto("https://chat.deepseek.com/", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        btn = page.locator(".ds-toggle-button:has-text('DeepThink')").first
        print("Initial DeepThink aria-pressed / class:")
        aria = await btn.get_attribute("aria-pressed") or await btn.get_attribute("aria-checked")
        cls = await btn.get_attribute("class") or ""
        print(f"   aria={aria}, class={cls}")
        
        search_btn = page.locator(".ds-toggle-button:has-text('Search')").first
        print("Initial Search aria-pressed / class:")
        s_aria = await search_btn.get_attribute("aria-pressed") or await search_btn.get_attribute("aria-checked")
        s_cls = await search_btn.get_attribute("class") or ""
        print(f"   aria={s_aria}, class={s_cls}")
        
        print("Toggling Search...")
        await search_btn.click()
        await asyncio.sleep(1)
        s_aria_after = await search_btn.get_attribute("aria-pressed") or await search_btn.get_attribute("aria-checked")
        print(f"   Search after click: aria={s_aria_after}")
        
        await search_btn.click()
        await asyncio.sleep(1)
        s_aria_rev = await search_btn.get_attribute("aria-pressed") or await search_btn.get_attribute("aria-checked")
        print(f"   Search reverted: aria={s_aria_rev}")
        
        await context.close()
        print("Toggle test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_toggle())
