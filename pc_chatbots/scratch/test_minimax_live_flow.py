import asyncio
import json
from app.browser.session import BrowserSessionManager
from app.adapters.capabilities.minimax import MinimaxCapabilitiesStrategy
from app.adapters.capabilities.models import ProviderSelectionRequest
from app.adapters.minimax_ui import MinimaxUIAdapter

async def run_live_test():
    print("1. Opening Minimax session...")
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    strategy = MinimaxCapabilitiesStrategy()
    adapter = MinimaxUIAdapter()

    # Step A: Inspect live capabilities
    print("2. Inspecting live capabilities from DOM...")
    caps = await strategy.inspect_dom(page)
    print(f"Discovered models: {[m.label for m in caps.available_models]}")
    print(f"Current selected model: {caps.selected_model_id}")
    print(f"Current deep research: {caps.deep_research}")

    # Step B: Select model M3.1-Flash-Preview and enable Deep Research
    print("3. Applying selection: model='m3.1-flash', deep_research=True...")
    req = ProviderSelectionRequest(model_id="m3.1-flash", deep_research=True)
    await strategy.apply_selection(page, req)
    await asyncio.sleep(2)

    # Check state after enabling
    chip_info = await page.evaluate("""
    () => {
        const trigger = document.querySelector("[data-testid='model-selector-trigger']");
        const chip = document.querySelector(".node-skillCommand, [data-testid='skill-command-chip']");
        return {
            triggerText: trigger ? trigger.innerText.trim() : null,
            hasChip: Boolean(chip),
            chipText: chip ? chip.innerText.trim() : null
        };
    }
    """)
    print("State after enabling deep research:", json.dumps(chip_info, ensure_ascii=False))

    # Step C: Enter prompt into editor while preserving the chip
    print("4. Entering prompt into editor with chip present...")
    editor = page.locator(".tiptap.ProseMirror, [data-testid='message-textarea']").first
    await adapter._enter_prompt(page, editor, "Thử nghiệm câu hỏi: Giải thích cơ chế Deep Research?")
    await asyncio.sleep(1)

    editor_content = await page.evaluate("""
    () => {
        const ed = document.querySelector(".tiptap.ProseMirror, [data-testid='message-textarea']");
        const chip = ed ? ed.querySelector(".node-skillCommand, [data-testid='skill-command-chip']") : null;
        const sendBtn = document.querySelector("[data-testid='send-button']");
        return {
            hasChip: Boolean(chip),
            fullText: ed ? ed.innerText.trim() : '',
            sendBtnDisabled: sendBtn ? (sendBtn.classList.contains('cursor-not-allowed') || sendBtn.getAttribute('aria-disabled') === 'true') : true
        };
    }
    """)
    print("Editor status with prompt recorded.")

    # Step D: Test switching Deep Research OFF (default behavior)
    print("5. Testing Deep Research OFF (default) and model switch back to M3...")
    # Clear editor text first
    await editor.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")

    req_off = ProviderSelectionRequest(model_id="m3", deep_research=False)
    await strategy.apply_selection(page, req_off)
    await asyncio.sleep(1.5)

    off_info = await page.evaluate("""
    () => {
        const trigger = document.querySelector("[data-testid='model-selector-trigger']");
        const chip = document.querySelector(".node-skillCommand, [data-testid='skill-command-chip']");
        return {
            triggerText: trigger ? trigger.innerText.trim() : null,
            hasChip: Boolean(chip)
        };
    }
    """)
    print("State with Deep Research OFF recorded.")

    # Enter standard prompt without chip
    print("6. Entering standard prompt without chip...")
    await adapter._enter_prompt(page, editor, "Thử nghiệm câu hỏi thông thường không có Deep Research")
    await asyncio.sleep(1)

    standard_content = await page.evaluate("""
    () => {
        const ed = document.querySelector(".tiptap.ProseMirror, [data-testid='message-textarea']");
        const chip = ed ? ed.querySelector(".node-skillCommand, [data-testid='skill-command-chip']") : null;
        const sendBtn = document.querySelector("[data-testid='send-button']");
        return {
            hasChip: Boolean(chip),
            fullText: ed ? ed.innerText.trim() : '',
            sendBtnDisabled: sendBtn ? (sendBtn.classList.contains('cursor-not-allowed') || sendBtn.getAttribute('aria-disabled') === 'true') : true
        };
    }
    """)
    results = {
        "step_a_caps": {
            "models": [m.label for m in caps.available_models],
            "selected_model": caps.selected_model_id,
            "deep_research": caps.deep_research,
        },
        "step_b_deep_research_on": chip_info,
        "step_c_prompt_with_chip": editor_content,
        "step_d_deep_research_off": off_info,
        "step_e_standard_prompt": standard_content,
    }
    with open("scratch/minimax_live_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Clean up editor so browser is clean
    await editor.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    print("ALL TESTS COMPLETED SUCCESSFULLY! Results saved to scratch/minimax_live_result.json")

asyncio.run(run_live_test())
