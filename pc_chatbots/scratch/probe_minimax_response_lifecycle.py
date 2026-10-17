import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(3)

    # 1. Type prompt into editor
    editor = page.locator(".tiptap.ProseMirror, [data-testid='message-textarea']").first
    await editor.click()
    await page.keyboard.type("Say hello in 5 words", delay=10)
    await asyncio.sleep(1)

    # 2. Click send button
    send_btn = page.locator("[data-testid='send-button']").first
    await send_btn.click()
    print("Clicked send button. Now polling conversation DOM...")

    snapshots = []
    # Poll for up to 30 seconds
    for t in range(60):
        await asyncio.sleep(0.5)
        snap = await page.evaluate("""
        () => {
            const container = document.querySelector("[data-testid='chat-main-conversation']");
            const stopBtn = document.querySelector("[data-testid='stop-button'], button[aria-label*='Stop' i], div[aria-label*='Stop' i]");
            const copyBtns = document.querySelectorAll("button[aria-label*='Copy' i], div[aria-label*='Copy' i], button[class*='copy' i], div[class*='copy' i], [data-testid*='copy']");

            if (!container) {
                return {
                    time: Date.now(),
                    hasContainer: false,
                    hasStopBtn: Boolean(stopBtn),
                    copyBtnCount: copyBtns.length,
                    bodySnippet: document.body.innerText.slice(0, 300)
                };
            }

            // Inspect children of container
            const children = [];
            for (let i = 0; i < container.children.length; i++) {
                const child = container.children[i];
                // Check for thought/thinking elements inside this child
                const thoughtEls = child.querySelectorAll("[class*='think'], [class*='thought'], [data-testid*='think'], [class*='reasoning'], [class*='collapse'], [class*='step']");
                const thoughts = Array.from(thoughtEls).map(th => ({
                    tag: th.tagName,
                    className: th.className,
                    text: (th.innerText || '').slice(0, 100)
                }));

                // Check for copy button inside this child
                const childCopy = child.querySelectorAll("button[aria-label*='Copy' i], div[aria-label*='Copy' i], button[class*='copy' i], div[class*='copy' i], [data-testid*='copy']");

                // Check markdown / answer content
                const mdEls = child.querySelectorAll("[class*='markdown'], [class*='prose'], [class*='content'], [class*='message']");
                const mds = Array.from(mdEls).map(m => ({
                    className: m.className,
                    textSnippet: (m.innerText || '').slice(0, 150)
                }));

                children.push({
                    index: i,
                    tag: child.tagName,
                    className: child.className,
                    testId: child.getAttribute('data-testid'),
                    role: child.getAttribute('data-role') || child.getAttribute('role'),
                    textSnippet: (child.innerText || '').slice(0, 200),
                    hasCopyBtn: childCopy.length > 0,
                    copyBtnCount: childCopy.length,
                    thoughts: thoughts.slice(0, 5),
                    mds: mds.slice(0, 5)
                });
            }

            return {
                time: Date.now(),
                hasContainer: true,
                containerClass: container.className,
                childCount: container.children.length,
                hasStopBtn: Boolean(stopBtn),
                copyBtnCount: copyBtns.length,
                children: children
            };
        }
        """)

        # Keep a few distinct snapshots
        if not snapshots or snapshots[-1].get("hasStopBtn") != snap.get("hasStopBtn") or snapshots[-1].get("copyBtnCount") != snap.get("copyBtnCount") or (t % 6 == 0):
            snapshots.append({"t_sec": t * 0.5, **snap})
            print(f"[{t*0.5}s] hasContainer={snap.get('hasContainer')} childCount={snap.get('childCount')} hasStopBtn={snap.get('hasStopBtn')} copyBtnCount={snap.get('copyBtnCount')}")

        # Stop early if completed (stopBtn gone and copyBtn found)
        if snap.get("hasContainer") and not snap.get("hasStopBtn") and snap.get("copyBtnCount", 0) > 0 and t > 4:
            print("Response complete! Stop button gone and Copy button found.")
            break

    # Also capture outerHTML of the last child of container
    last_child_html = await page.evaluate("""
    () => {
        const container = document.querySelector("[data-testid='chat-main-conversation']");
        if (!container || !container.lastElementChild) return null;
        return {
            outerHTML: container.lastElementChild.outerHTML.slice(0, 15000),
            innerText: container.lastElementChild.innerText
        };
    }
    """)

    result = {
        "snapshots": snapshots,
        "last_child": last_child_html
    }
    Path("scratch/probe_minimax_response.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Done! Saved to scratch/probe_minimax_response.json")

asyncio.run(probe())
