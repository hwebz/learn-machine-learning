import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    # 1. Click model selector trigger
    model_btn = page.locator("[data-testid='model-selector-trigger'], .mavis-model-selector-trigger")
    await model_btn.click()
    await asyncio.sleep(1.5)

    models_info = await page.evaluate("""
    () => {
        const dropdowns = document.querySelectorAll(".ant-dropdown:not(.ant-dropdown-hidden), .mavis-model-selector-dropdown, div[class*='model-selector-popup'], div[class*='dropdown']");
        const items = [];
        for (const drop of dropdowns) {
            const els = drop.querySelectorAll("[role='menuitem'], li, button, div[class*='item'], div[class*='option']");
            for (const el of els) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    items.push({
                        text: (el.innerText || el.textContent || '').trim(),
                        className: el.className,
                        testId: el.getAttribute('data-testid'),
                        role: el.getAttribute('role'),
                        ariaSelected: el.getAttribute('aria-selected')
                    });
                }
            }
        }
        return items;
    }
    """)
    Path("scratch/minimax_models.json").write_text(json.dumps(models_info, indent=2, ensure_ascii=False), encoding="utf-8")

    # Close dropdown
    await page.keyboard.press("Escape")
    await asyncio.sleep(1)

    # 2. Click attach (+) button
    attach_btn = page.locator("[data-testid='attach-button'], div[aria-label='Add attachment']")
    await attach_btn.click()
    await asyncio.sleep(1.5)

    attach_menu = await page.evaluate("""
    () => {
        const dropdowns = document.querySelectorAll(".ant-dropdown:not(.ant-dropdown-hidden)");
        const items = [];
        for (const drop of dropdowns) {
            const els = drop.querySelectorAll("*");
            for (const el of els) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && el.children.length === 0) {
                    const txt = (el.innerText || el.textContent || '').trim();
                    if (txt) {
                        items.push({
                            tag: el.tagName.toLowerCase(),
                            text: txt,
                            className: el.className,
                            parentClass: el.parentElement ? el.parentElement.className : ''
                        });
                    }
                }
            }
        }
        return items;
    }
    """)
    Path("scratch/minimax_attach.json").write_text(json.dumps(attach_menu, indent=2, ensure_ascii=False), encoding="utf-8")

    # Look for Skills item and hover/click it
    skills_el = page.locator("text=Skills, [data-testid*='skill'], .ant-dropdown-menu-submenu-title:has-text('Skills')")
    count = await skills_el.count()
    submenu_items = []
    if count > 0:
        await skills_el.first.hover()
        await asyncio.sleep(1.5)
        submenu_items = await page.evaluate("""
        () => {
            const dropdowns = document.querySelectorAll(".ant-dropdown:not(.ant-dropdown-hidden), .ant-dropdown-menu-submenu");
            const items = [];
            for (const drop of dropdowns) {
                const els = drop.querySelectorAll("*");
                for (const el of els) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && el.children.length === 0) {
                        const txt = (el.innerText || el.textContent || '').trim();
                        if (txt) {
                            items.push({
                                tag: el.tagName.toLowerCase(),
                                text: txt,
                                className: el.className
                            });
                        }
                    }
                }
            }
            return items;
        }
        """)
    Path("scratch/minimax_skills.json").write_text(json.dumps(submenu_items, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Done probing!")

asyncio.run(probe())
