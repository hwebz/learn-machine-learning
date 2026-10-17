import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(3)

    info = await page.evaluate("""
    () => {
        const container = document.querySelector("[data-testid='chat-main-conversation']");
        if (!container) {
            // Find anything matching chat, conversation, message, or main
            const candidates = document.querySelectorAll("[data-testid*='chat'], [data-testid*='conversation'], [class*='conversation']");
            return {
                foundMain: false,
                candidates: Array.from(candidates).map(c => ({
                    tag: c.tagName,
                    className: c.className,
                    testId: c.getAttribute('data-testid'),
                    childCount: c.children.length
                }))
            };
        }

        const children = [];
        for (let i = 0; i < container.children.length; i++) {
            const child = container.children[i];
            children.push({
                index: i,
                tag: child.tagName,
                className: child.className,
                testId: child.getAttribute('data-testid'),
                role: child.getAttribute('role'),
                textSnippet: (child.innerText || '').slice(0, 200),
                outerHtmlSample: child.outerHTML.slice(0, 1000)
            });
        }

        return {
            foundMain: true,
            containerClass: container.className,
            childCount: container.children.length,
            children: children
        };
    }
    """)

    Path("scratch/probe_conversation_container.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Found main:", info.get("foundMain"))
    if not info.get("foundMain"):
        print("Candidates:", info.get("candidates"))
    else:
        print(f"Container childCount: {info.get('childCount')}")

asyncio.run(probe())
