import asyncio
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright

async def inspect_menus():
    profile_dir = root / "data" / "profiles" / "qwen"
    result = {"models": [], "thinking": []}
    
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
        
        # 1. Inspect model dropdown
        model_btn = page.locator("div.wms-trigger, [class*='mode-select'] div.wms-trigger")
        if await model_btn.count() > 0:
            result["current_model"] = (await model_btn.first.inner_text()).strip()
            await model_btn.first.click()
            await asyncio.sleep(1.2)
            
            # Save screenshot of opened model dropdown
            await page.screenshot(path=str(root / "data" / "artifacts" / "qwen_model_dropdown.png"))
            
            # Look for popup options container
            popover = page.locator(".ant-dropdown, .ant-popover, .wms-dropdown, [class*='dropdown'], [class*='popover']")
            p_cnt = await popover.count()
            for p_idx in range(p_cnt):
                p_elem = popover.nth(p_idx)
                if await p_elem.is_visible():
                    items = p_elem.locator("[class*='option'], [class*='item'], div")
                    for i in range(await items.count()):
                        t = (await items.nth(i).inner_text()).strip()
                        if "Qwen" in t or "Max" in t or "Plus" in t:
                            lines = [l.strip() for l in t.split("\n") if l.strip()]
                            if lines and lines[0] not in result["models"]:
                                result["models"].append(lines[0])
            
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.6)
            
        # 2. Inspect thinking dropdown
        think_btn = page.locator(".qwen-thinking-selector")
        if await think_btn.count() > 0:
            result["current_thinking"] = (await think_btn.first.inner_text()).strip()
            await think_btn.first.click()
            await asyncio.sleep(1.2)
            
            # Save screenshot of opened thinking dropdown
            await page.screenshot(path=str(root / "data" / "artifacts" / "qwen_thinking_dropdown.png"))
            
            popover = page.locator(".ant-dropdown, .ant-popover, [class*='dropdown'], [class*='popover'], [role='menu']")
            p_cnt = await popover.count()
            for p_idx in range(p_cnt):
                p_elem = popover.nth(p_idx)
                if await p_elem.is_visible():
                    items = p_elem.locator("[role='menuitem'], [class*='item'], div")
                    for i in range(await items.count()):
                        t = (await items.nth(i).inner_text()).strip()
                        if t in {"Thinking", "Auto", "Fast", "Deep Thinking", "Think"} or "thinking" in t.lower() or "auto" in t.lower():
                            if t not in result["thinking"]:
                                result["thinking"].append(t)
                                
            await page.keyboard.press("Escape")
            
        await context.close()
        
    out_file = root / "data" / "artifacts" / "qwen_dom_details.json"
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("DONE_INSPECTION")

if __name__ == "__main__":
    asyncio.run(inspect_menus())
