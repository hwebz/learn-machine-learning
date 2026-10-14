"""Offline verification: run the real ChatGPT extraction JS in Playwright against
a local page with a blob: image, then confirm saved bytes outlive the page.

No provider request is made. Run: .venv/Scripts/python.exe scripts/verify_image_extraction.py
"""
from __future__ import annotations

import asyncio
import base64
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.browser.chatgpt_response import (  # noqa: E402
    CAPTURE_RESPONSES,
    EXTRACT_RESPONSE,
    RESPONSE_READY,
)
from app.browser.media import save_image  # noqa: E402

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
)

PAGE_HTML = """<!doctype html>
<div data-talvt-turn-state="complete" id="old-turn"><p>Old turn</p></div>
<script>
  // Simulates the assistant response arriving after submission: the page gains a
  // new turn containing a gallery with a blob: image.
  window.addResponse = () => {
    const turn = document.createElement('div');
    turn.setAttribute('data-talvt-turn-state', 'complete');
    turn.innerHTML = `<p>Here is your dog on the moon.</p>
      <div data-testid="generated-image-gallery">
        <div data-testid="generated-image-preview">
          <img id="gen-img" alt="Generated image 1">
        </div>
      </div>`;
    document.body.appendChild(turn);
    const bytes = Uint8Array.from(atob("%s"), c => c.charCodeAt(0));
    const blob = new Blob([bytes], {type: "image/png"});
    document.getElementById("gen-img").src = URL.createObjectURL(blob);
  };
</script>
""" % base64.b64encode(PNG_1PX).decode()


async def main() -> int:
    from playwright.async_api import async_playwright

    media_dir = Path(tempfile.mkdtemp(prefix="pc-media-"))
    failures: list[str] = []
    async with async_playwright() as pw:
        # Downloaded Playwright chromium is unavailable here; use the installed
        # Edge channel instead (same Chromium engine).
        try:
            browser = await pw.chromium.launch(headless=True, channel="msedge")
        except Exception:
            browser = await pw.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page()
        await page.set_content(PAGE_HTML, wait_until="load")

        # 1. Capture before submission marks the existing turn as previous.
        await page.evaluate(CAPTURE_RESPONSES)

        # 2. The response arrives (new turn + blob image load).
        await page.evaluate("window.addResponse()")
        await page.wait_for_function("document.getElementById('gen-img')?.complete")

        # 2. Readiness: gallery exists and image loaded -> ready.
        ready = await page.evaluate(RESPONSE_READY)
        if ready is not True:
            failures.append(f"expected ready=True, got {ready!r}")

        # 3. Extraction returns html without the gallery and base64 bytes.
        result = await page.evaluate(EXTRACT_RESPONSE, {"maxBytes": 20 * 1024 * 1024, "maxImages": 8})
        if result is None:
            failures.append("extraction returned None")
            result = {"html": "", "images": []}
        if "generated-image-gallery" in result["html"]:
            failures.append("gallery markup leaked into html")
        if "Here is your dog on the moon." not in result["html"]:
            failures.append("response text missing from html")
        if len(result["images"]) != 1 or result["images"][0].get("error"):
            failures.append(f"image fetch failed: {result['images']}")

        # 4. Page closes; bytes already extracted must still save.
        await browser.close()
    if result["images"] and result["images"][0].get("data"):
        data = base64.b64decode(result["images"][0]["data"])
        filename = save_image(data, result["images"][0]["type"], media_dir)
        saved = (media_dir / filename).read_bytes()
        if saved != PNG_1PX:
            failures.append("saved bytes differ from source PNG")
        print(f"saved image outlived the page: {filename} ({len(saved)} bytes)")
    else:
        failures.append("no image data extracted")

    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT:", "PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
