import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    info = await page.evaluate("""
    () => {
        // Collect buttons, inputs, dropdowns, plus buttons
        const elements = [];
        const all = document.querySelectorAll("button, [role='button'], [contenteditable='true'], textarea, input, div[class*='model'], div[class*='dropdown'], div[class*='select']");
        for (const el of all) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                elements.push({
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || el.textContent || '').trim().slice(0, 100),
                    ariaLabel: el.getAttribute('aria-label'),
                    title: el.getAttribute('title'),
                    id: el.id,
                    className: el.className,
                    testId: el.getAttribute('data-testid'),
                    role: el.getAttribute('role'),
                    placeholder: el.getAttribute('placeholder'),
                    rect: {
                        top: Math.round(rect.top),
                        bottom: Math.round(rect.bottom),
                        left: Math.round(rect.left),
                        right: Math.round(rect.right),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    }
                });
            }
        }

        // Also get composer / input container HTML
        const composer = document.querySelector("[class*='composer'], [class*='input'], [class*='chat-input'], form, [class*='bottom']");
        const composerHtml = composer ? composer.outerHTML.slice(0, 5000) : '';

        return {
            url: window.location.href,
            title: document.title,
            elements: elements,
            composerHtml: composerHtml
        };
    }
    """)

    out_file = Path("scratch/minimax_dom.json")
    out_file.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Dumped {len(info['elements'])} elements to {out_file}")

asyncio.run(probe())
