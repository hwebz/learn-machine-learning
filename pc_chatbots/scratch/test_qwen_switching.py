import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright

async def test_qwen_switching():
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
        
        # 1. Test Switching to Qwen3.8-Max
        print("=== Test 1: Switch Model to Qwen3.8-Max ===")
        model_btn = page.locator("div.wms-trigger, [class*='mode-select'] div.wms-trigger").first
        curr_text = (await model_btn.inner_text()).strip()
        print("Current model button:", curr_text)
        
        if "max" not in curr_text.lower():
            await model_btn.click()
            await asyncio.sleep(1.0)
            max_opt = page.locator("[class*='option']:has-text('Max'), div:has-text('Qwen3.8-Max')").first
            if await max_opt.count() > 0:
                await max_opt.click()
                print("Clicked Max option")
                await asyncio.sleep(1.5)
            else:
                await page.keyboard.press("Escape")
        
        new_text = (await model_btn.inner_text()).strip()
        print("Model button after switch:", new_text)
        
        # 2. Test Switching Thinking to 'Thinking'
        print("\n=== Test 2: Switch Thinking to 'Thinking' ===")
        think_btn = page.locator(".qwen-thinking-selector").first
        curr_t_text = (await think_btn.inner_text()).strip()
        print("Current thinking button:", curr_t_text)
        
        if "thinking" not in curr_t_text.lower():
            await think_btn.click()
            await asyncio.sleep(1.0)
            t_opt = page.locator(".qwen-chat-v2-dropdown-menu-item:has-text('Thinking'), [role='menuitem']:has-text('Thinking'), div:has-text('Thinking')").first
            if await t_opt.count() > 0:
                await t_opt.click()
                print("Clicked Thinking option")
                await asyncio.sleep(1.5)
            else:
                await page.keyboard.press("Escape")
                
        new_t_text = (await think_btn.inner_text()).strip()
        print("Thinking button after switch:", new_t_text)
        
        await page.screenshot(path=str(root / "data" / "artifacts" / "qwen_switched_max_thinking.png"))
        print("\nScreenshot saved to qwen_switched_max_thinking.png")
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_qwen_switching())
