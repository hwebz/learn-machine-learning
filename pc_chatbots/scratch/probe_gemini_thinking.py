import asyncio
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from app.browser.session import BrowserSessionManager
from app.adapters.selectors_loader import load_selectors, provider_selectors

async def main():
    print("=== PROBING GEMINI THINKING SUBMENU ===")
    session = BrowserSessionManager.get_session("gemini")
    selectors = load_selectors()
    cfg = provider_selectors(selectors, "gemini")
    target_url = cfg.get("new_chat_url", "https://gemini.google.com/app")
    
    async with session.exclusive():
        page = await session.new_page(target_url)
        await asyncio.sleep(3.5)
        
        # Click the dropdown button
        btn = page.locator("button:has-text('Flash-Lite'), button:has-text('Flash'), button:has-text('Pro')").first
        await btn.click()
        await asyncio.sleep(1.0)
        
        # Find "Cấp độ tư duy" or "Thinking" item
        thinking_menu = page.locator("[role='menuitem']:has-text('Cấp độ tư duy'), [role='menuitem']:has-text('tư duy'), [role='menuitem']:has-text('Thinking')").first
        print("Hovering / Clicking 'Cấp độ tư duy'...")
        await thinking_menu.hover()
        await asyncio.sleep(0.5)
        await thinking_menu.click()
        await asyncio.sleep(1.2)
        
        await page.screenshot(path="scratch/gemini_thinking_submenu.png")
        print("Saved scratch/gemini_thinking_submenu.png")
        
        # Dump all visible menuitems now
        all_items = page.locator("[role='menuitem'], [role='menuitemradio'], .mat-mdc-menu-item")
        cnt = await all_items.count()
        print(f"\nAll visible items ({cnt}):")
        for i in range(cnt):
            it = all_items.nth(i)
            try:
                if await it.is_visible(timeout=100):
                    t = (await it.inner_text()).strip().replace("\n", " | ")
                    r = await it.get_attribute("role")
                    checked = await it.get_attribute("aria-checked")
                    print(f"  Item #{i}: text='{t}' | role='{r}' | checked='{checked}'")
            except:
                pass
                
        await page.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
