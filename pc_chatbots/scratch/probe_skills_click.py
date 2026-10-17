import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    # Click attach (+) button
    attach_btn = page.locator("[data-testid='attach-button'], div[aria-label='Add attachment']")
    await attach_btn.click()
    await asyncio.sleep(1)

    # Click Skills ONLY inside the attach dropdown menu!
    skills_item = page.locator(".ant-dropdown:not(.ant-dropdown-hidden) .mavis-menu-item:has-text('Skills')")
    count = await skills_item.count()
    print("Attach menu Skills item count:", count)
    if count > 0:
        await skills_item.first.click()
        await asyncio.sleep(2)

    # Now let's see what is visible in the DOM
    info = await page.evaluate("""
    () => {
        // Collect visible elements in dropdowns, modals, popovers
        const all = document.querySelectorAll(".ant-dropdown:not(.ant-dropdown-hidden) *, .ant-modal *, [role='dialog'] *, [role='menu'] *, .mavis-popover *");
        const items = [];
        const seen = new Set();
        for (const el of all) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                const txt = (el.innerText || el.textContent || '').trim();
                if (txt && !seen.has(txt) && txt.length < 100) {
                    seen.add(txt);
                    items.push({
                        tag: el.tagName.toLowerCase(),
                        text: txt,
                        className: el.className,
                        testId: el.getAttribute('data-testid')
                    });
                }
            }
        }
        return items;
    }
    """)
    Path("scratch/attach_skills_clicked.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Dumped {len(info)} items to attach_skills_clicked.json")

asyncio.run(probe())
