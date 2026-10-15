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
    print(f"Opening DeepSeek with profile {profile_dir}...")
    
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
        print("Navigating to https://chat.deepseek.com/ ...")
        try:
            await page.goto("https://chat.deepseek.com/", timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"Navigation warning: {e}")
        
        await asyncio.sleep(4)
        print("Current page URL:", page.url)
        print("Page title:", await page.title())
        
        body_text = await page.evaluate("() => document.body.innerText || ''")
        print(f"Body text preview (first 400 chars):\n{body_text[:400]}")
        
        # Check buttons and toggles
        print("\n--- Searching for potential toggles and model selectors ---")
        locators_to_check = [
            ".ds-toggle-button",
            "button:has-text('DeepThink')",
            "div:has-text('DeepThink')",
            "button:has-text('Search')",
            "div:has-text('Search')",
            "[class*='toggle']",
            "[class*='model']",
            "button[aria-label*='DeepThink']",
            "button[aria-label*='Search']",
            "textarea",
            "#chat-input",
        ]
        
        for sel in locators_to_check:
            loc = page.locator(sel)
            cnt = await loc.count()
            if cnt > 0:
                print(f"Selector '{sel}': found {cnt} elements")
                for i in range(min(cnt, 5)):
                    try:
                        el = loc.nth(i)
                        txt = (await el.inner_text()).strip().replace("\n", " | ")
                        cls = await el.get_attribute("class") or ""
                        aria = await el.get_attribute("aria-pressed") or await el.get_attribute("aria-checked") or ""
                        visible = await el.is_visible()
                        print(f"   [{i}]: visible={visible} text='{txt}' class='{cls[:50]}' aria='{aria}'")
                    except Exception as e:
                        print(f"   [{i}]: error reading {e}")
        
        # Check active DeepThink state
        dt_btn = page.locator("div.ds-toggle-button:has-text('DeepThink'), .ds-toggle-button:has-text('DeepThink'), button:has-text('DeepThink')")
        if await dt_btn.count() > 0:
            for i in range(await dt_btn.count()):
                el = dt_btn.nth(i)
                if await el.is_visible():
                    cls = await el.get_attribute("class") or ""
                    print(f"\nVisible DeepThink button found: class='{cls}'")
                    is_active = "active" in cls.lower() or "selected" in cls.lower() or "checked" in cls.lower()
                    print(f"DeepThink is_active: {is_active}")

        screenshot_path = root / "data" / "artifacts" / "deepseek_inspect_live.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"\nScreenshot saved to {screenshot_path}")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(inspect())
