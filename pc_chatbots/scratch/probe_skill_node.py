import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    # Click attach (+) -> Skills -> deep-research
    attach_btn = page.locator("[data-testid='attach-button'], div[aria-label='Add attachment']")
    await attach_btn.click()
    await asyncio.sleep(1)

    skills_item = page.locator(".ant-dropdown:not(.ant-dropdown-hidden) .mavis-menu-item:has-text('Skills')")
    await skills_item.first.click()
    await asyncio.sleep(1)

    deep_btn = page.locator("button.mavis-menu-item:has-text('deep-research'), button:has-text('deep-research')")
    await deep_btn.first.click()
    await asyncio.sleep(1.5)

    info = await page.evaluate("""
    () => {
        const node = document.querySelector(".node-skillCommand, [class*='node-skillCommand']");
        return {
            html: node ? node.outerHTML : '',
            buttons: node ? Array.from(node.querySelectorAll("*")).map(e => ({ tag: e.tagName, class: e.className, text: e.innerText })) : []
        };
    }
    """)
    print("Node HTML:", info["html"])
    print("Node elements:", info["buttons"])

asyncio.run(probe())
