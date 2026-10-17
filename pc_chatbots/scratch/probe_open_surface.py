import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    await session.start()
    pages = session._ctx.pages
    print(f"Total open pages: {len(pages)}")

    target_page = None
    for p in pages:
        print("Page URL:", p.url)
        if "agent.minimax.io" in p.url:
            target_page = p
            break

    if not target_page:
        print("No agent.minimax.io page found, opening new...")
        target_page = await session.new_page("https://agent.minimax.io/")
        await asyncio.sleep(3)

    data = await target_page.evaluate("""
    () => {
        const container = document.querySelector("[data-testid='chat-main-conversation']");
        if (!container) return { error: "chat-main-conversation not found", url: window.location.href };

        const surface = container.querySelector("[data-testid='chat-panel-messages-surface']");
        if (!surface) return { error: "surface not found", url: window.location.href };

        return {
            url: window.location.href,
            containerClass: container.className,
            surfaceHtml: surface.innerHTML
        };
    }
    """)

    Path("scratch/probe_surface_html.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Done! url:", data.get("url"), "hasHtml:", bool(data.get("surfaceHtml")))

asyncio.run(probe())
