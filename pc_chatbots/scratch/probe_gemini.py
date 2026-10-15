import asyncio
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from app.browser.session import BrowserSessionManager
from app.adapters.selectors_loader import load_selectors, provider_selectors

async def main():
    print("=== PROBING GEMINI DROPDOWN ===")
    session = BrowserSessionManager.get_session("gemini")
    selectors = load_selectors()
    cfg = provider_selectors(selectors, "gemini")
    target_url = cfg.get("new_chat_url", "https://gemini.google.com/app")
    
    async with session.exclusive():
        page = await session.new_page(target_url)
        await asyncio.sleep(3.5)
        
        # Locate the model/mode dropdown (shows "Flash-Lite" or has arrow)
        selector_candidates = [
            "button:has-text('Flash-Lite')",
            "button:has-text('Flash')",
            "button:has-text('Pro')",
            "button:has(mat-icon[data-mat-icon-name='keyboard_arrow_down'])",
            ".input-area-switch",
            "bard-mode-switcher button",
            "button[aria-haspopup='menu']",
        ]
        
        clicked = False
        for sel in selector_candidates:
            loc = page.locator(sel)
            cnt = await loc.count()
            for idx in range(cnt):
                btn = loc.nth(idx)
                if await btn.is_visible(timeout=500):
                    txt = (await btn.inner_text()).strip().replace("\n", " ")
                    aria = (await btn.get_attribute("aria-label")) or ""
                    print(f"Found visible button with [{sel} #{idx}]: text='{txt}', aria='{aria}'")
                    if not clicked and ("flash" in txt.lower() or "pro" in txt.lower() or "lite" in txt.lower() or "chế độ" in aria.lower() or "mode" in aria.lower()):
                        print(f"--> Clicking button: '{txt}'")
                        await btn.click()
                        clicked = True
                        break
            if clicked:
                break
                
        if clicked:
            await asyncio.sleep(1.5)
            await page.screenshot(path="scratch/gemini_menu.png")
            print("Saved screenshot to scratch/gemini_menu.png")
            
            # Inspect menu items
            items = page.locator("[role='menuitem'], .mat-mdc-menu-item, mat-list-item, [role='option'], .cdk-overlay-container button")
            cnt = await items.count()
            print(f"\nFound {cnt} menu items/buttons in overlay:")
            for i in range(cnt):
                it = items.nth(i)
                try:
                    if await it.is_visible(timeout=100):
                        t = (await it.inner_text()).strip().replace("\n", " | ")
                        a = (await it.get_attribute("aria-label")) or ""
                        r = (await it.get_attribute("role")) or ""
                        print(f"  Item #{i}: text='{t}' | aria='{a}' | role='{r}'")
                except:
                    pass
        else:
            print("Could not find dropdown button to click!")
            
        await page.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
