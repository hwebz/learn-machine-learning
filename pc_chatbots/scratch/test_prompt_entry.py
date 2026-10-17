import asyncio
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    # 1. Enable deep research
    attach_btn = page.locator("[data-testid='attach-button'], div[aria-label='Add attachment']")
    await attach_btn.click()
    await asyncio.sleep(1)

    skills_item = page.locator(".ant-dropdown:not(.ant-dropdown-hidden) .mavis-menu-item:has-text('Skills')")
    await skills_item.first.click()
    await asyncio.sleep(1)

    deep_btn = page.locator("button.mavis-menu-item:has-text('deep-research'), button:has-text('deep-research')")
    await deep_btn.first.click()
    await asyncio.sleep(1)

    # 2. Enter prompt into editor
    editor = page.locator(".tiptap.ProseMirror, [data-testid='message-textarea']")
    await editor.click()
    await page.keyboard.type("What is quantum computing?", delay=20)
    await asyncio.sleep(1)

    # Check editor contents
    res = await page.evaluate("""
    () => {
        const editor = document.querySelector(".tiptap.ProseMirror, [data-testid='message-textarea']");
        const chip = editor ? editor.querySelector(".node-skillCommand, [data-testid='skill-command-chip']") : null;
        const sendBtn = document.querySelector("[data-testid='send-button']");
        return {
            hasChip: Boolean(chip),
            editorText: editor ? editor.innerText : '',
            sendBtnDisabled: sendBtn ? (sendBtn.classList.contains('cursor-not-allowed') || sendBtn.getAttribute('aria-disabled') === 'true') : true
        };
    }
    """)
    print("Editor result after typing:", res)

asyncio.run(probe())
