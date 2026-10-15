import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager


async def main():
    session = BrowserSessionManager.get_session("mistral")

    async with session.exclusive():
        page = await session.new_page("https://chat.mistral.ai/chat")
        await asyncio.sleep(4.0)

        print(f"Page loaded: {page.url}", flush=True)

        # 1. Switch reasoning mode to 'Think'
        dropdown_btn = page.locator("button:has-text('Fast'), button:has-text('Think'), button[aria-label='Choose model']").first
        if await dropdown_btn.is_visible():
            curr_text = (await dropdown_btn.inner_text()).strip()
            print(f"Current reasoning mode: {curr_text!r}", flush=True)
            if "Think" not in curr_text:
                print("Switching reasoning mode to Think...", flush=True)
                await dropdown_btn.click()
                await asyncio.sleep(0.8)
                think_item = page.locator("[role='menuitem']:has-text('Think')").first
                if await think_item.is_visible():
                    await think_item.click()
                    await asyncio.sleep(0.8)

        # 2. Enter @deep-research skill
        inp = page.locator("div.ProseMirror[contenteditable='true'], [contenteditable='true'], textarea").first
        await inp.wait_for(state="visible", timeout=10000)
        await inp.click()
        await asyncio.sleep(0.5)

        print("Enabling Deep Research via @deep-research...", flush=True)
        await inp.type("@deep-research", delay=40)
        await asyncio.sleep(1.2)

        # Select first skill
        first_skill = page.locator("[role='listbox'] [role='option'], [role='option'], button[role='option'], div:has-text('deep-research')").first
        if await first_skill.count() > 0 and await first_skill.is_visible():
            print("Selecting first skill from popup...", flush=True)
            await page.keyboard.press("Enter")
        else:
            print("Pressing Enter...", flush=True)
            await page.keyboard.press("Enter")

        await asyncio.sleep(0.8)

        # 3. Enter question
        query = "What is the capital of Australia? Answer in one short sentence."
        print(f"Entering prompt: {query!r}", flush=True)
        await inp.type(f" {query}", delay=20)
        await asyncio.sleep(0.8)

        # 4. Submit
        send_btn = page.locator("button[aria-label*='Send' i], button[type='submit']").first
        if await send_btn.is_visible(timeout=3000):
            print("Clicking Send button...", flush=True)
            await send_btn.click()
        else:
            print("Pressing Enter to submit...", flush=True)
            await inp.press("Enter")

        # 5. Wait for answer
        print("Waiting for response from Mistral...", flush=True)
        for s in range(1, 30):
            await asyncio.sleep(1.0)
            stop_btn = page.locator("button[aria-label*='Stop' i]")
            is_gen = (await stop_btn.count() > 0) and (await stop_btn.first.is_visible())

            copy_btn = page.locator("button[aria-label*='Copy' i]")
            copy_cnt = await copy_btn.count()

            ans_loc = page.locator("div[data-message-author-role='assistant'], div[class*='prose'], .markdown-body")
            txt = ""
            if await ans_loc.count() > 0:
                txt = (await ans_loc.last.inner_text()).strip()

            print(f"[{s}s] is_generating={is_gen}, copy_buttons={copy_cnt}, text_len={len(txt)}", flush=True)
            if copy_cnt > 0 and not is_gen and len(txt) > 5:
                print(f"COMPLETE! Answer: {txt!r}", flush=True)
                break

        out_img = Path("scratch/mistral_dr_response.png")
        await page.screenshot(path=str(out_img))
        print(f"Screenshot saved to {out_img}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
