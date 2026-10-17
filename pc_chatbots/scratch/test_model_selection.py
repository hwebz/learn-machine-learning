import asyncio
from app.browser.session import BrowserSessionManager

async def probe():
    session = BrowserSessionManager.get_session("minimax")
    page = await session.new_page("https://agent.minimax.io/")
    await asyncio.sleep(4)

    # 1. Read current active model
    model_btn = page.locator("[data-testid='model-selector-trigger'], .mavis-model-selector-trigger")
    current_label = (await model_btn.inner_text()).strip()
    print("Current model button text:", current_label)

    # 2. Click to open dropdown
    await model_btn.click()
    await asyncio.sleep(1)

    # 3. Select M3.1-Flash-Preview
    item = page.locator(".mavis-menu-item:has-text('M3.1-Flash-Preview')")
    print("M3.1-Flash-Preview count:", await item.count())
    if await item.count() > 0:
        await item.first.click()
        await asyncio.sleep(1)

    # 4. Check new active model
    new_label = (await model_btn.inner_text()).strip()
    print("New model button text after selecting Flash:", new_label)

    # 5. Switch back to M3
    await model_btn.click()
    await asyncio.sleep(1)
    m3_item = page.locator(".mavis-menu-item:has-text('M3'):not(:has-text('Flash'))")
    if await m3_item.count() > 0:
        await m3_item.first.click()
        await asyncio.sleep(1)
    final_label = (await model_btn.inner_text()).strip()
    print("Final model button text:", final_label)

asyncio.run(probe())
