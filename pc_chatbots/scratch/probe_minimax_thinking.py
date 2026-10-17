import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager
from app.adapters.capabilities.minimax import MinimaxCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest
from app.adapters.minimax_ui import MinimaxUIAdapter

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(3)

    strategy = MinimaxCapabilitiesStrategy()
    adapter = MinimaxUIAdapter()

    # 1. Enable Deep Research
    print("Enabling Deep Research...")
    req = ProviderSelectionRequest(model_id="m3", deep_research=True)
    await strategy.apply_selection(page, req)
    await asyncio.sleep(1.5)

    # 2. Enter prompt
    print("Entering prompt...")
    editor = page.locator(".tiptap.ProseMirror, [data-testid='message-textarea']").first
    await adapter._enter_prompt(page, editor, "Tóm tắt 3 xu hướng AI năm 2026 trong 3 gạch đầu dòng ngắn")
    await asyncio.sleep(1)

    # 3. Submit
    send_btn = page.locator("[data-testid='send-button']").first
    await send_btn.click()
    print("Prompt submitted! Polling chat-main-conversation...")

    history = []
    for sec in range(90):
        await asyncio.sleep(1.0)
        snap = await page.evaluate("""
        () => {
            const root = document.querySelector("[data-testid='chat-main-conversation']");
            const stopBtn = document.querySelector("[data-testid='stop-button'], button[aria-label*='Stop' i], div[aria-label*='Stop' i], [class*='stop']");
            const copyBtns = document.querySelectorAll("[data-testid='chat-main-conversation'] button[aria-label*='Copy' i], [data-testid='chat-main-conversation'] div[aria-label*='Copy' i], [data-testid='chat-main-conversation'] [class*='copy']");

            if (!root) {
                return { hasRoot: false, hasStop: Boolean(stopBtn), copyCount: copyBtns.length };
            }

            // Inspect all nodes with thinking, reasoning, steps, or markdown
            const allElements = root.querySelectorAll("*");
            const thinkingNodes = [];
            for (const el of allElements) {
                const cls = (typeof el.className === 'string') ? el.className : '';
                const tid = el.getAttribute('data-testid') || '';
                const txt = (el.innerText || '').trim();
                if (
                    tid.includes('think') || tid.includes('step') || tid.includes('reason') ||
                    cls.includes('think') || cls.includes('thought') || cls.includes('step') ||
                    cls.includes('reason') || cls.includes('collapse') || cls.includes('process')
                ) {
                    if (txt && txt.length < 300) {
                        thinkingNodes.push({
                            tag: el.tagName,
                            testId: tid,
                            className: cls.slice(0, 80),
                            text: txt
                        });
                    }
                }
            }

            // Look for assistant message turns or markdown blocks
            const markdownBlocks = root.querySelectorAll("[class*='markdown'], [class*='prose'], .matrix-markdown, [data-role='assistant']");
            const mdList = Array.from(markdownBlocks).map(m => ({
                tag: m.tagName,
                className: m.className,
                textSnippet: (m.innerText || '').slice(0, 150)
            }));

            // Copy buttons details
            const copies = Array.from(copyBtns).map(c => ({
                tag: c.tagName,
                aria: c.getAttribute('aria-label'),
                className: c.className,
                testId: c.getAttribute('data-testid'),
                rect: c.getBoundingClientRect()
            }));

            return {
                hasRoot: true,
                hasStop: Boolean(stopBtn),
                copyCount: copyBtns.length,
                thinkingNodesCount: thinkingNodes.length,
                thinkingNodes: thinkingNodes.slice(0, 15),
                mdCount: markdownBlocks.length,
                mdList: mdList.slice(0, 5),
                copies: copies,
                rootTextSnippet: root.innerText.slice(0, 300)
            };
        }
        """)

        has_stop = snap.get("hasStop")
        copy_count = snap.get("copyCount", 0)
        print(f"[{sec}s] hasStop={has_stop} copyCount={copy_count} thinkingCount={snap.get('thinkingNodesCount')} mdCount={snap.get('mdCount')}")

        history.append({"sec": sec, **snap})

        if snap.get("hasRoot") and not has_stop and copy_count > 0 and sec > 5:
            print("Finished generation! Stop button gone and Copy button visible.")
            break

    # Capture the full HTML of chat-main-conversation
    full_html = await page.evaluate("""
    () => {
        const root = document.querySelector("[data-testid='chat-main-conversation']");
        return root ? root.outerHTML : '';
    }
    """)

    out = {
        "history": history,
        "full_html": full_html
    }
    Path("scratch/minimax_thinking_probe.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Done! Saved to scratch/minimax_thinking_probe.json")

asyncio.run(probe())
