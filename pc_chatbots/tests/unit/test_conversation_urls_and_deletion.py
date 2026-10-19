from __future__ import annotations

import asyncio
import time
from typing import Any
import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.adapters.fake import FakeAdapter
from app.core.config import settings
from app.main import app
from app.orchestrator import pipeline, agent_pipeline

API_HEADERS = {"X-API-Key": settings.api_key}


class TrackingFakeAdapter(FakeAdapter):
    deleted_urls: list[str] = []

    def __init__(self, name: str) -> None:
        super().__init__(name)

    async def delete_conversation(self, conversation_url: str) -> bool:
        self.deleted_urls.append(conversation_url)
        return True


def test_normal_research_saves_conversation_urls_and_deletion(monkeypatch: MonkeyPatch) -> None:
    TrackingFakeAdapter.deleted_urls.clear()
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: TrackingFakeAdapter(provider))
    monkeypatch.setattr("app.api.routes.create_adapter", lambda provider: TrackingFakeAdapter(provider))

    with TestClient(app) as client:
        res = client.post(
            "/research",
            headers=API_HEADERS,
            json={"query": "Test conversation URLs", "providers": ["perplexity", "gemini"]},
        )
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        # Wait for completion
        deadline = time.monotonic() + 10
        job = None
        while time.monotonic() < deadline:
            resp = client.get(f"/research/{job_id}", headers=API_HEADERS)
            assert resp.status_code == 200
            job = resp.json()
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.05)

        assert job is not None
        assert job["status"] == "completed"

        # Check provider_runs contains conversation_url
        runs = job.get("provider_runs", [])
        assert len(runs) == 2
        for r in runs:
            assert r.get("conversation_url") is not None
            assert "fake-" in r["conversation_url"]

        # Check /conversations endpoint
        conv_resp = client.get(f"/research/{job_id}/conversations", headers=API_HEADERS)
        assert conv_resp.status_code == 200
        conv_data = conv_resp.json()
        assert conv_data["job_id"] == job_id
        assert len(conv_data["conversations"]) >= 2
        urls = [c["url"] for c in conv_data["conversations"]]

        # Delete research job and verify remote deletion was triggered
        del_resp = client.delete(f"/research/{job_id}", headers=API_HEADERS)
        assert del_resp.status_code == 204

        # Job is now deleted from DB
        get_after = client.get(f"/research/{job_id}", headers=API_HEADERS)
        assert get_after.status_code == 404

        # Verify TrackingFakeAdapter tracked deletion of the URLs
        assert len(TrackingFakeAdapter.deleted_urls) >= 2
        for u in urls:
            assert u in TrackingFakeAdapter.deleted_urls


def test_agent_research_saves_orchestrator_subtasks_lead_conversation_urls_and_deletes(monkeypatch: MonkeyPatch) -> None:
    TrackingFakeAdapter.deleted_urls.clear()
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: TrackingFakeAdapter(provider))
    monkeypatch.setattr(agent_pipeline, "create_adapter", lambda provider: TrackingFakeAdapter(provider))
    monkeypatch.setattr("app.api.routes.create_adapter", lambda provider: TrackingFakeAdapter(provider))

    with TestClient(app) as client:
        payload = {
            "query": "Nghiên cứu kiến trúc AI",
            "orchestrator_provider": "gemini",
            "lead_provider": "chatgpt",
            "tone": "academic",
            "max_minutes": 5,
        }
        res = client.post("/agent-research", headers=API_HEADERS, json=payload)
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        deadline = time.monotonic() + 10
        job = None
        while time.monotonic() < deadline:
            resp = client.get(f"/research/{job_id}", headers=API_HEADERS)
            assert resp.status_code == 200
            job = resp.json()
            if job["status"] in ("completed", "failed"):
                break
            time.sleep(0.05)

        assert job is not None
        assert job["status"] == "completed"
        assert job["orchestrator_conversation_url"] is not None
        assert "gemini" in job["orchestrator_conversation_url"]
        assert job["lead_conversation_url"] is not None
        assert "chatgpt" in job["lead_conversation_url"]

        # Check provider_runs contains conversation_url for subtasks
        runs = job.get("provider_runs", [])
        assert len(runs) >= 2
        for r in runs:
            assert r.get("conversation_url") is not None

        # Check /conversations endpoint returns orchestrator, lead, and subtasks
        conv_resp = client.get(f"/research/{job_id}/conversations", headers=API_HEADERS)
        assert conv_resp.status_code == 200
        conv_data = conv_resp.json()
        roles = {c["role"] for c in conv_data["conversations"]}
        assert "orchestrator" in roles
        assert "lead" in roles
        assert "subtask" in roles
        expected_urls = {c["url"] for c in conv_data["conversations"]}

        # Test DELETE deletes all remote provider chats
        del_resp = client.delete(f"/research/{job_id}", headers=API_HEADERS)
        assert del_resp.status_code == 204

        for u in expected_urls:
            assert u in TrackingFakeAdapter.deleted_urls


@pytest.mark.asyncio
async def test_gemini_ui_adapter_delete_conversation() -> None:
    from unittest.mock import AsyncMock, MagicMock
    from contextlib import asynccontextmanager
    from app.adapters.gemini_ui import GeminiUIAdapter

    # Mock page elements
    mock_menu_btn = AsyncMock()
    mock_menu_btn.is_visible = AsyncMock(return_value=True)
    mock_menu_btn.bounding_box = AsyncMock(return_value={"x": 1200, "y": 50, "width": 40, "height": 40})
    mock_menu_btn.click = AsyncMock()

    mock_del_btn = AsyncMock()
    mock_del_btn.is_visible = AsyncMock(return_value=True)
    mock_del_btn.click = AsyncMock()
    mock_del_btn.inner_text = AsyncMock(return_value="Xóa")

    mock_confirm_btn = AsyncMock()
    mock_confirm_btn.is_visible = AsyncMock(return_value=True)
    mock_confirm_btn.click = AsyncMock()
    mock_confirm_btn.inner_text = AsyncMock(return_value="Xóa")

    mock_toast = AsyncMock()
    mock_toast.is_visible = AsyncMock(return_value=True)
    mock_toast.inner_text = AsyncMock(return_value="Đã xóa cuộc trò chuyện")

    # Mock locator dispatching
    def locator_factory(selector: str) -> Any:
        mock_loc = AsyncMock()
        if "more_vert" in selector:
            mock_loc.count = AsyncMock(return_value=1)
            mock_loc.nth = MagicMock(return_value=mock_menu_btn)
            mock_loc.first = mock_menu_btn
        elif "dialog" in selector:
            mock_loc.count = AsyncMock(return_value=1)
            mock_loc.nth = MagicMock(return_value=mock_confirm_btn)
            mock_loc.first = mock_confirm_btn
        elif "Xóa" in selector or "Xoá" in selector:
            mock_loc.count = AsyncMock(return_value=1)
            mock_loc.nth = MagicMock(return_value=mock_del_btn)
            mock_loc.first = mock_del_btn
        elif "snack-bar" in selector:
            mock_loc.count = AsyncMock(return_value=1)
            mock_loc.nth = MagicMock(return_value=mock_toast)
            mock_loc.first = mock_toast
        else:
            mock_loc.count = AsyncMock(return_value=0)
            mock_loc.first = AsyncMock(is_visible=AsyncMock(return_value=False))
        return mock_loc

    mock_page = AsyncMock()
    mock_page.url = "https://gemini.google.com/app/abc123xyz"
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.locator = MagicMock(side_effect=locator_factory)
    mock_page.close = AsyncMock()
    mock_page.goto = AsyncMock()

    mock_session = AsyncMock()
    @asynccontextmanager
    async def fake_exclusive():
        yield
    mock_session.exclusive = fake_exclusive
    mock_session.new_page = AsyncMock(return_value=mock_page)
    mock_session._ctx = AsyncMock()
    mock_session._ctx.pages = [mock_page, AsyncMock()]

    adapter = GeminiUIAdapter(session=mock_session)
    res = await adapter.delete_conversation("https://gemini.google.com/app/abc123xyz")

    assert res is True
    mock_menu_btn.click.assert_awaited()
    mock_del_btn.click.assert_awaited()
    mock_confirm_btn.click.assert_awaited()
    mock_page.close.assert_awaited()
