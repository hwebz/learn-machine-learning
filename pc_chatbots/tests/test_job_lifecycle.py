from __future__ import annotations

import time
import asyncio

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.adapters.fake import FakeAdapter
from app.adapters.base import ProviderResult
from app.core.config import settings
from app.main import app
from app.orchestrator import pipeline

API_HEADERS = {"X-API-Key": settings.api_key}


def test_health_is_public_and_research_requires_api_key() -> None:
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/research", json={"query": "test"})
        assert response.status_code == 401


def test_fake_pipeline_completes_and_sse_replays_transitions(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: FakeAdapter(provider))
    with TestClient(app) as client:
        accepted = client.post(
            "/research",
            headers=API_HEADERS,
            json={"query": "Explain a test topic", "providers": ["perplexity", "gemini"]},
        )
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = client.get(f"/research/{job_id}", headers=API_HEADERS).json()
            if job["status"] == "completed":
                break
            time.sleep(0.02)

        assert job["status"] == "completed"
        assert job["progress"] == {"subtasks_total": 2, "subtasks_done": 2}
        assert job["report_markdown"].startswith("# Research response")
        assert "placeholder response" in job["report_markdown"]
        assert len(job["sources"]) == 2
        assert len(job["provider_runs"]) == 2

        events = client.get(f"/research/{job_id}/events", headers=API_HEADERS)
        assert events.status_code == 200
        for phase in ("queued", "planning", "researching", "extracting", "verifying", "synthesizing", "completed"):
            assert f'"status": "{phase}"' in events.text


def test_fake_pipeline_with_new_chatbot_providers(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: FakeAdapter(provider))
    with TestClient(app) as client:
        providers = ["chatgpt", "claude", "deepseek", "grok", "copilot", "qwen", "kimi"]
        accepted = client.post(
            "/research",
            headers=API_HEADERS,
            json={"query": "Test across new providers", "providers": providers},
        )
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = client.get(f"/research/{job_id}", headers=API_HEADERS).json()
            if job["status"] == "completed":
                break
            time.sleep(0.02)

        assert job["status"] == "completed"
        assert job["progress"]["subtasks_total"] == len(providers)
        assert len(job["provider_runs"]) == len(providers)


def test_cancel_unknown_job_returns_not_found() -> None:
    with TestClient(app) as client:
        response = client.post("/research/missing/cancel", headers=API_HEADERS)
        assert response.status_code == 404


def test_cancel_active_job_is_cooperative(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: FakeAdapter(provider))
    original_ask = FakeAdapter.ask

    async def slow_ask(self: FakeAdapter, prompt: str, *, timeout_s: int, mode: str = "default") -> ProviderResult:
        await asyncio.sleep(0.15)
        return await original_ask(self, prompt, timeout_s=timeout_s, mode=mode)

    monkeypatch.setattr(FakeAdapter, "ask", slow_ask)
    with TestClient(app) as client:
        accepted = client.post(
            "/research",
            headers=API_HEADERS,
            json={"query": "Cancel this test", "providers": ["perplexity", "gemini"]},
        )
        job_id = accepted.json()["job_id"]
        cancelled = client.post(f"/research/{job_id}/cancel", headers=API_HEADERS)
        assert cancelled.status_code == 204

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = client.get(f"/research/{job_id}", headers=API_HEADERS).json()
            if job["status"] == "cancelled":
                break
            time.sleep(0.02)
        assert job["status"] == "cancelled"


def test_sse_emits_granular_steps_and_valid_responses(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: FakeAdapter(provider))
    with TestClient(app) as client:
        accepted = client.post(
            "/research",
            headers=API_HEADERS,
            json={"query": "Test granular SSE steps", "providers": ["copilot"]},
        )
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = client.get(f"/research/{job_id}", headers=API_HEADERS).json()
            if job["status"] == "completed":
                break
            time.sleep(0.02)
        assert job["status"] == "completed"

        events_resp = client.get(f"/research/{job_id}/events", headers=API_HEADERS)
        assert events_resp.status_code == 200
        text = events_resp.text

        # Verify step events were streamed
        assert "event: step" in text
        assert '"step": "provider_start"' in text
        assert '"step": "generating"' in text
        assert '"step": "response_valid"' in text
        assert '"response_markdown":' in text
        assert '"status": "ok"' in text


def test_sse_emits_failure_step_when_adapter_fails(monkeypatch: MonkeyPatch) -> None:
    from app.adapters.browser_base import ProviderNeedsUserAction

    async def failing_ask(self, prompt: str, *, timeout_s: int, mode: str = "default", on_step=None) -> ProviderResult:
        raise ProviderNeedsUserAction("Simulated login failure on test provider")

    monkeypatch.setattr(FakeAdapter, "ask", failing_ask)
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: FakeAdapter(provider))

    with TestClient(app) as client:
        accepted = client.post(
            "/research",
            headers=API_HEADERS,
            json={"query": "Test failing provider SSE", "providers": ["copilot"]},
        )
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = client.get(f"/research/{job_id}", headers=API_HEADERS).json()
            if job["status"] in {"needs_user_action", "failed"}:
                break
            time.sleep(0.02)

        events_resp = client.get(f"/research/{job_id}/events", headers=API_HEADERS)
        assert events_resp.status_code == 200
        text = events_resp.text

        assert "event: step" in text
        assert '"step": "failed"' in text
        assert "Simulated login failure on test provider" in text
        assert '"status": "needs_user_action"' in text
