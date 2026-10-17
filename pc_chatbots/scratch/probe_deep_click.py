import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    # 1. Click attach (+)
    attach_btn = page.locator("[data-testid='attach-button'], div[aria-label='Add attachment']")
    await attach_btn.click()
    await asyncio.sleep(1)

    # 2. Click Skills
    skills_item = page.locator(".ant-dropdown:not(.ant-dropdown-hidden) .mavis-menu-item:has-text('Skills')")
    await skills_item.first.click()
    await asyncio.sleep(1)

    # 3. Click deep-research
    deep_btn = page.locator("button.mavis-menu-item:has-text('deep-research'), button:has-text('deep-research')")
    print("deep-research count:", await deep_btn.count())
    await deep_btn.first.click()
    await asyncio.sleep(2)

    # 4. Inspect composer and surrounding elements to see how deep-research is shown when enabled
    info = await page.evaluate("""
    () => {
        const composer = document.querySelector(".tiptap, [data-testid='message-textarea'], [class*='composer']");
        const chips = Array.from(document.querySelectorAll("[class*='chip'], [class*='tag'], [class*='skill'], [class*='badge'], button, div")).filter(el => {
            const t = (el.innerText || el.textContent || '').toLowerCase();
            return t.includes("deep-research") || t.includes("deep research");
        }).map(el => ({
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.textContent || '').trim().slice(0, 100),
            className: el.className,
            testId: el.getAttribute('data-testid')
        }));

        return {
            chips: chips,
            composerText: composer ? (composer.innerText || '') : ''
        };
    }
    """)
    Path("scratch/deep_research_active.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote deep_research_active.json")

asyncio.run(probe())
