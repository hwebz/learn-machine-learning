import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(2)

    details = await page.evaluate("""
    () => {
        const surface = document.querySelector("[data-testid='chat-panel-messages-surface']");
        if (!surface) return { error: "surface not found" };

        // Look for messages / conversation turns
        const allNodes = surface.querySelectorAll("*");
        const interesting = [];
        for (const el of allNodes) {
            const tid = el.getAttribute('data-testid');
            const role = el.getAttribute('data-role') || el.getAttribute('role');
            const cls = el.className || '';
            if (tid || (typeof cls === 'string' && (cls.includes('message') || cls.includes('assistant') || cls.includes('user') || cls.includes('think') || cls.includes('thought') || cls.includes('process') || cls.includes('markdown') || cls.includes('copy')))) {
                interesting.push({
                    tag: el.tagName,
                    testId: tid,
                    role: role,
                    className: typeof cls === 'string' ? cls.slice(0, 100) : '',
                    text: (el.innerText || '').slice(0, 100),
                    childElementCount: el.childElementCount
                });
            }
        }

        // Specifically find assistant turns
        const assistantItems = surface.querySelectorAll("[data-role='assistant'], [class*='assistant'], [data-testid*='assistant']");
        const assistantHtml = [];
        for (const a of assistantItems) {
            assistantHtml.push({
                testId: a.getAttribute('data-testid'),
                className: a.className,
                outerHTML: a.outerHTML.slice(0, 4000)
            });
        }

        // Also check any copy buttons
        const copyButtons = surface.querySelectorAll("button[aria-label*='Copy' i], div[aria-label*='Copy' i], button[class*='copy' i], div[class*='copy' i], [data-testid*='copy']");
        const copyList = Array.from(copyButtons).map(b => ({
            tag: b.tagName,
            ariaLabel: b.getAttribute('aria-label'),
            className: b.className,
            testId: b.getAttribute('data-testid'),
            parentClass: b.parentElement ? b.parentElement.className : ''
        }));

        return {
            interestingCount: interesting.length,
            interesting: interesting.slice(0, 40),
            assistantCount: assistantItems.length,
            assistantHtml: assistantHtml,
            copyList: copyList
        };
    }
    """)

    Path("scratch/probe_messages_surface.json").write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Captured {details.get('assistantCount')} assistant items, {len(details.get('copyList', []))} copy buttons.")

asyncio.run(probe())
