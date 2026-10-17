import asyncio
import json
from pathlib import Path
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = session.current_page
    if not page:
        print("No current page found!")
        return

    print("Current page URL:", page.url)

    details = await page.evaluate("""
    () => {
        const container = document.querySelector("[data-testid='chat-main-conversation']");
        if (!container) return { error: "chat-main-conversation not found", url: window.location.href };

        const surface = container.querySelector("[data-testid='chat-panel-messages-surface']");
        if (!surface) return { error: "surface not found", containerHtml: container.outerHTML.slice(0, 2000) };

        // Get inner HTML of surface
        return {
            url: window.location.href,
            surfaceHtml: surface.innerHTML.slice(0, 30000)
        };
    }
    """)

    Path("scratch/probe_surface_html.json").write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Done! Keys:", list(details.keys()))

asyncio.run(probe())
