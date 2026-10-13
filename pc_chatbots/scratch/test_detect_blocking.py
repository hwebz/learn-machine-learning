import asyncio
import os
from playwright.async_api import async_playwright
import yaml

from app.browser.waits import detect_blocking_state

async def main():
    with open("app/adapters/selectors.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    blocking_cfg = cfg.get("blocking", {})

    html_path = os.path.abspath("data/artifacts/ui-chatgpt-1791888941/chatgpt/page-1791889002.html")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page()
        await page.goto(f"file:///{html_path.replace(os.sep, '/')}")
        
        state = await detect_blocking_state(page, blocking_cfg)
        print("Detected blocking state:", state)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
