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

        # 1. Click the 'Fast' dropdown nearby Send button
        dropdown_btn = page.locator("button:has-text('Fast'), button:has-text('Think'), button[aria-label='Choose model']").first
        if await dropdown_btn.is_visible():
            print(f"Found reasoning dropdown with text: {await dropdown_btn.inner_text()!r}", flush=True)
            await dropdown_btn.click()
            await asyncio.sleep(1.0)

            # Inspect menu items
            menu_items = await page.locator("[role='menuitem'], [role='option'], div[class*='menu'] button, [data-radix-collection-item]").all()
            print(f"Menu items count: {len(menu_items)}", flush=True)
            for i, item in enumerate(menu_items):
                txt = (await item.inner_text()).strip().replace('\n', ' -- ')
                role = await item.get_attribute("role")
                print(f"  [{i}] role={role!r}: {txt!r}")

            await page.screenshot(path="scratch/mistral_dropdown_open.png")
            print("Dropdown screenshot saved to scratch/mistral_dropdown_open.png", flush=True)
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

        # 2. Test typing @deep-research
        inp = page.locator("div.ProseMirror[contenteditable='true'], [contenteditable='true'], textarea").first
        await inp.wait_for(state="visible", timeout=10000)
        await inp.click()
        await asyncio.sleep(0.5)

        print("\nTyping '@deep-research' into input...", flush=True)
        # Type character by character to trigger autocomplete
        await inp.type("@deep-research", delay=50)
        await asyncio.sleep(1.5)

        await page.screenshot(path="scratch/mistral_mention_open.png")
        print("Mention popup screenshot saved to scratch/mistral_mention_open.png", flush=True)

        # Inspect autocomplete popup
        skills = await page.locator("[role='listbox'] [role='option'], div[class*='popover'] [role='button'], div[class*='popover'] div, [data-radix-collection-item]").all()
        print(f"\nAutocomplete elements count: {len(skills)}", flush=True)
        for i, s in enumerate(skills[:10]):
            txt = (await s.inner_text()).strip().replace('\n', ' -- ')
            vis = await s.is_visible()
            if vis:
                print(f"  [{i}] {txt!r}")

        # Test selecting the first skill (e.g. Enter or clicking first item)
        first_skill = page.locator("[role='listbox'] [role='option'], [role='option'], button[role='option']").first
        if await first_skill.count() > 0 and await first_skill.is_visible():
            print(f"Clicking first skill: {await first_skill.inner_text()!r}", flush=True)
            await first_skill.click()
        else:
            print("Pressing Enter to select first skill...", flush=True)
            await page.keyboard.press("Enter")

        await asyncio.sleep(1.0)
        await page.screenshot(path="scratch/mistral_skill_selected.png")
        print("Skill selected screenshot saved to scratch/mistral_skill_selected.png", flush=True)

        # Test typing the rest of the prompt after skill
        prompt_suffix = " What are the key milestones of AI in 2025?"
        print(f"Typing suffix prompt: {prompt_suffix!r}", flush=True)
        await inp.type(prompt_suffix, delay=20)
        await asyncio.sleep(1.0)

        await page.screenshot(path="scratch/mistral_prompt_ready.png")
        print("Prompt ready screenshot saved to scratch/mistral_prompt_ready.png", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
