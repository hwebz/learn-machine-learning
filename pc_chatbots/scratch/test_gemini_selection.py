import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.browser.session import BrowserSessionManager
from app.adapters.capabilities.gemini import GeminiCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest


async def main():
    session = BrowserSessionManager.get_session("gemini")
    strategy = GeminiCapabilitiesStrategy()

    async with session.exclusive():
        page = await session.new_page("https://gemini.google.com/app")
        await asyncio.sleep(2.0)

        # Test 1: Switch to 3.8 Flash + Low thinking
        print("--- Testing Combination 1: 3.8 Flash + Low Thinking ---")
        cfg1 = ProviderSelectionRequest(
            model_id="gemini-3.8-flash",
            thinking_level_id="low",
        )
        await strategy.apply_selection(page, cfg1)
        btn = await strategy._find_dropdown_button(page)
        btn_txt = await btn.inner_text() if btn else "None"
        print(f"Current button text after Comb 1: {btn_txt}")
        await asyncio.sleep(1.0)

        # Test 2: Switch to 3.1 Pro + High thinking
        print("\n--- Testing Combination 2: 3.1 Pro + High Thinking ---")
        cfg2 = ProviderSelectionRequest(
            model_id="gemini-3.1-pro",
            thinking_level_id="high",
        )
        await strategy.apply_selection(page, cfg2)
        btn = await strategy._find_dropdown_button(page)
        btn_txt = await btn.inner_text() if btn else "None"
        print(f"Current button text after Comb 2: {btn_txt}")
        await asyncio.sleep(1.0)

        # Inspect DOM to verify live state
        print("\n--- Inspecting DOM to verify live state ---")
        caps = await strategy.inspect_dom(page)
        print(f"Verified Live Model: {caps.selected_model_id}")
        print(f"Verified Live Thinking Level: {caps.selected_thinking_level_id}")


if __name__ == "__main__":
    asyncio.run(main())
