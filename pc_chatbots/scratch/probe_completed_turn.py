import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = session._ctx.pages[0] if session._ctx and session._ctx.pages else await session.new_page("https://agent.minimax.io/")

    info = await page.evaluate("""
    () => {
        const root = document.querySelector("[data-testid='chat-main-conversation']");
        if (!root) return { error: "no root" };

        const asstTurn = root.querySelector("[data-message-role='assistant']:last-of-type, [data-role='assistant']:last-of-type");
        if (!asstTurn) return { error: "no asstTurn" };

        // Find all copy buttons inside asstTurn
        const copyBtns = asstTurn.querySelectorAll("button[aria-label*='Copy' i], div[aria-label*='Copy' i], [data-testid*='copy']");
        const copyList = Array.from(copyBtns).map(c => ({
            tag: c.tagName,
            aria: c.getAttribute('aria-label'),
            className: c.className,
            testId: c.getAttribute('data-testid'),
            outerHTML: c.outerHTML.slice(0, 300)
        }));

        // Find assistant action bar at the bottom
        const actionBars = asstTurn.querySelectorAll("[class*='action'], [data-testid*='action']");
        const actions = Array.from(actionBars).map(a => ({
            tag: a.tagName,
            className: a.className,
            testId: a.getAttribute('data-testid'),
            buttons: Array.from(a.querySelectorAll("button, div[role='button']")).map(b => ({
                aria: b.getAttribute('aria-label'),
                className: b.className,
                testId: b.getAttribute('data-testid'),
                text: b.innerText
            }))
        }));

        // Find markdown answer container
        const mdBlocks = asstTurn.querySelectorAll(".matrix-markdown, [class*='markdown'], [data-testid='assistant-segment-active']");
        const mdText = Array.from(mdBlocks).map(m => m.innerText.slice(0, 200));

        return {
            asstClass: asstTurn.className,
            copyCount: copyBtns.length,
            copyList: copyList,
            actions: actions,
            mdCount: mdBlocks.length,
            mdText: mdText,
            fullAsstText: asstTurn.innerText
        };
    }
    """)

    Path("scratch/probe_completed_turn.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Captured: copyCount={info.get('copyCount')}, mdCount={info.get('mdCount')}")

asyncio.run(probe())
