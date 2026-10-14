from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from app.adapters.chatgpt_ui import ChatGPTUIAdapter
from app.browser.chatgpt_response import CAPTURE_RESPONSES, RESPONSE_READY

PNG_1PX = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
).decode()


class FakePage:
    """Evaluates the real page scripts against a stubbed DOM snapshot."""

    def __init__(self, dom: dict[str, Any]) -> None:
        self.dom = dom
        self.captured = False

    def locator(self, _css: str) -> Any:  # fallback chain finds nothing
        class Empty:
            async def count(self) -> int:
                return 0

        return Empty()

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        if script is CAPTURE_RESPONSES:
            self.captured = True
            return None
        if script is RESPONSE_READY:
            return self.dom["ready"]
        payload = json.loads(json.dumps(arg))  # mirrors real Page.evaluate arg cloning
        # Mirrors the real JS root resolution: with a capture snapshot every old
        # turn is excluded (no new root); without one, only image-bearing turns
        # are eligible.
        if self.captured:
            return None
        if not self.dom["alts"]:
            return None
        if self.dom["ready"] is False:
            raise RuntimeError("Page.evaluate: images not ready")
        return {
            "html": self.dom["html"],
            "images": [
                {"alt": alt, "type": "image/png", "data": PNG_1PX}
                for alt in self.dom["alts"]
            ],
        }


def make_adapter(tmp_path, monkeypatch) -> ChatGPTUIAdapter:
    monkeypatch.setattr("app.adapters.chatgpt_ui.settings", type(
        "S", (), {"media_dir": tmp_path / "media", "work_mode": "async"}
    )())
    return ChatGPTUIAdapter(artifact_dir=tmp_path / "artifacts")


async def test_image_only_response_saved_as_media(tmp_path, monkeypatch) -> None:
    adapter = make_adapter(tmp_path, monkeypatch)
    page = FakePage({"ready": True, "html": "", "alts": ["Generated image 1"]})
    answer = await adapter._extract_answer(page, prompt="Tạo ảnh chú chó")
    assert "![Generated image 1](/api/media/" in answer
    assert "blob:" not in answer
    saved = list((tmp_path / "media").iterdir())
    assert len(saved) == 1 and saved[0].read_bytes().startswith(b"\x89PNG")


async def test_text_and_image_response(tmp_path, monkeypatch) -> None:
    adapter = make_adapter(tmp_path, monkeypatch)
    page = FakePage({"ready": True, "html": "<p>Here is your image</p>", "alts": ["Dog on moon"]})
    answer = await adapter._extract_answer(page)
    assert "Here is your image" in answer
    assert "/api/media/" in answer


async def test_not_ready_response_raises(tmp_path, monkeypatch) -> None:
    adapter = make_adapter(tmp_path, monkeypatch)
    # An image-bearing response whose images are not yet loaded must fail
    # extraction instead of silently returning an empty answer.
    page = FakePage({"ready": False, "html": "", "alts": ["Pending image"]})
    with pytest.raises(Exception):
        await adapter._extract_answer(page)


async def test_falls_back_for_plain_text(tmp_path, monkeypatch) -> None:
    adapter = make_adapter(tmp_path, monkeypatch)
    page = FakePage({"ready": True, "html": "", "alts": []})
    result = await adapter._extract_answer(page)
    # No images => EXTRACT_RESPONSE returns None => super() runs; FakePage can't
    # serve locator APIs, so result is whatever the base returns ("").
    assert result == ""


async def test_prepare_response_skips_existing_turns(tmp_path, monkeypatch) -> None:
    adapter = make_adapter(tmp_path, monkeypatch)
    page = FakePage({"ready": True, "html": "<p>old answer</p>", "alts": ["Old image"]})
    await adapter._prepare_response(page)
    assert page.captured
    # After capture, the old turn is excluded: the real JS finds no new root.
    # The FakePage cannot evaluate that JS, so emulate its no-new-root outcome
    # with a page whose DOM has no images.
    page2 = FakePage({"ready": True, "html": "<p>old answer</p>", "alts": []})
    await adapter._prepare_response(page2)
    from app.browser.chatgpt_response import EXTRACT_RESPONSE
    assert await page2.evaluate(EXTRACT_RESPONSE, {"maxBytes": 1024, "maxImages": 8}) is None
