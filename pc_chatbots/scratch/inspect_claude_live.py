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
    print(f"Opening Claude with profile {profile_dir}...")
    
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
        print("Navigating to https://claude.ai/new ...")
        try:
            await page.goto("https://claude.ai/new", timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"Navigation warning: {e}")
        
        await asyncio.sleep(4)
        print("Current page URL:", page.url)
        print("Page title:", await page.title())
        
        body_text = await page.evaluate("() => document.body.innerText || ''")
        print(f"Body text preview (first 500 chars):\n{body_text[:500]}")
        
        # Check for model selectors & buttons
        print("\n--- Searching for potential model & thinking buttons ---")
        locators_to_check = [
            "button[data-testid='model-selector-dropdown']",
            "button[aria-label*='Model']",
            "button:has-text('Claude')",
            "button:has-text('Sonnet')",
            "button:has-text('Haiku')",
            "button:has-text('Opus')",
            "button[data-testid='extended-thinking-toggle']",
            "button[aria-label*='Thinking']",
            "button[aria-label*='thinking']",
            "button:has-text('Thinking')",
            "button:has-text('Suy nghĩ')",
            "[data-testid*='model']",
            "[data-testid*='thinking']",
            "[class*='model-selector']",
        ]
        
        for sel in locators_to_check:
            loc = page.locator(sel)
            cnt = await loc.count()
            if cnt > 0:
                print(f"Selector '{sel}': found {cnt} elements")
                for i in range(min(cnt, 5)):
                    try:
                        txt = (await loc.nth(i).inner_text()).strip().replace("\n", " | ")
                        aria = await loc.nth(i).get_attribute("aria-label") or ""
                        testid = await loc.nth(i).get_attribute("data-testid") or ""
                        print(f"   [{i}]: text='{txt}' | aria='{aria}' | testid='{testid}'")
                    except Exception as e:
                        print(f"   [{i}]: error reading {e}")
        
        # If model dropdown exists, click it and inspect dropdown options!
        model_btn = None
        for sel in ["button[data-testid='model-selector-dropdown']", "button[aria-label*='Model']", "button:has-text('Sonnet')", "button:has-text('Claude')"]:
            loc = page.locator(sel)
            if await loc.count() > 0 and await loc.first.is_visible():
                model_btn = loc.first
                print(f"\nFound model button with selector '{sel}': '{(await model_btn.inner_text()).strip()}'")
                break
                
        if model_btn:
            print("Clicking model button to inspect options...")
            await model_btn.click()
            await asyncio.sleep(1.5)
            
            # Inspect menu items
            menu_items = page.locator("[role='menuitem'], [data-testid*='model'], [class*='MenuItem'], div[role='option'], div[tabindex='-1']")
            cnt = await menu_items.count()
            print(f"Found {cnt} menu items after opening model dropdown:")
            for i in range(cnt):
                item = menu_items.nth(i)
                if await item.is_visible():
                    txt = (await item.inner_text()).strip().replace("\n", " | ")
                    testid = await item.get_attribute("data-testid") or ""
                    role = await item.get_attribute("role") or ""
                    print(f"   Item [{i}]: role='{role}' testid='{testid}' text='{txt}'")
            
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

        # Inspect extended thinking button / toggle
        think_loc = page.locator("button[data-testid='extended-thinking-toggle'], button:has-text('Thinking'), button[aria-label*='Thinking']")
        if await think_loc.count() > 0:
            for i in range(await think_loc.count()):
                t_btn = think_loc.nth(i)
                if await t_btn.is_visible():
                    print(f"\nThinking button [{i}]: text='{(await t_btn.inner_text()).strip()}' aria='{await t_btn.get_attribute('aria-label')}'")
                    # Check if pressed or aria-checked
                    pressed = await t_btn.get_attribute("aria-pressed")
                    checked = await t_btn.get_attribute("aria-checked")
                    print(f"   pressed={pressed}, checked={checked}")

        screenshot_path = root / "data" / "artifacts" / "claude_inspect_live.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"\nScreenshot saved to {screenshot_path}")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(inspect())
