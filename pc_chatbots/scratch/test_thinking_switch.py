import asyncio
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from playwright.async_api import async_playwright

async def test_thinking_switch():
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
        
        think_btn = page.locator(".qwen-thinking-selector").first
        print("Initial thinking text:", (await think_btn.inner_text()).strip())
        await think_btn.click()
        await asyncio.sleep(1.0)
        
        # In ant-dropdown:
        opts = page.locator(".ant-dropdown, [class*='dropdown']").locator("[role='menuitem'], [class*='item'], div").filter(has_text="Thinking")
        cnt = await opts.count()
        print(f"Thinking matches: {cnt}")
        for i in range(cnt):
            e = opts.nth(i)
            if await e.is_visible():
                txt = (await e.inner_text()).strip()
                tag = await e.evaluate("el => el.tagName + '.' + el.className")
                print(f"Visible item [{i}]: tag={tag}, text={txt}")
                await e.click(timeout=3000)
                await asyncio.sleep(1.5)
                break
                
        new_text = (await think_btn.inner_text()).strip()
        print("Thinking after click:", new_text)
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_thinking_switch())
