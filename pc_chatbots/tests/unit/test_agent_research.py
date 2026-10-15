from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.adapters.fake import FakeAdapter
from app.core.config import settings
from app.main import app
from app.orchestrator import pipeline, agent_pipeline

API_HEADERS = {"X-API-Key": settings.api_key}


def test_agent_research_validation() -> None:
    with TestClient(app) as client:
        # Requires API key
        res = client.post("/agent-research", json={"query": "test"})
        assert res.status_code == 401

        # Blank query error
        res = client.post(
            "/agent-research",
            headers=API_HEADERS,
            json={
                "query": "   ",
                "orchestrator_provider": "gemini",
                "lead_provider": "chatgpt",
            },
        )
        assert res.status_code == 422

        # Invalid provider error
        res = client.post(
            "/agent-research",
            headers=API_HEADERS,
            json={
                "query": "Machine learning",
                "orchestrator_provider": "nonexistent_provider",
                "lead_provider": "chatgpt",
            },
        )
        assert res.status_code == 422


def test_agent_pipeline_lifecycle_with_fake_adapter(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: FakeAdapter(provider))
    monkeypatch.setattr(agent_pipeline, "create_adapter", lambda provider: FakeAdapter(provider))

    with TestClient(app) as client:
        payload = {
            "query": "Ứng dụng của Deep Learning trong y tế",
            "orchestrator_provider": "gemini",
            "orchestrator_config": {"model": "pro", "mode": "high"},
            "lead_provider": "chatgpt",
            "lead_config": {"thinking": True},
            "tone": "academic",
            "max_minutes": 5,
        }
        res = client.post("/agent-research", headers=API_HEADERS, json=payload)
        assert res.status_code == 202
        data = res.json()
        assert "job_id" in data
        job_id = data["job_id"]

        # Wait for worker to finish
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
        assert job["job_type"] == "agent"
        assert job["orchestrator_provider"] == "gemini"
        assert job["lead_provider"] == "chatgpt"
        assert job["tone"] == "academic"
        assert job["orchestrator_dispatch"] is not None
        assert len(job["orchestrator_dispatch"]) >= 2
        assert job["report_markdown"] is not None
        assert "Báo cáo Nghiên cứu Chuyên sâu" in job["report_markdown"]

        # Check list endpoint includes agent fields
        list_resp = client.get("/research?limit=5", headers=API_HEADERS)
        assert list_resp.status_code == 200
        matching = [item for item in list_resp.json() if item["job_id"] == job_id]
        assert len(matching) == 1
        assert matching[0]["job_type"] == "agent"
        assert matching[0]["tone"] == "academic"

        # Check SSE events contain orchestrating, researching, leading
        events_resp = client.get(f"/research/{job_id}/events", headers=API_HEADERS)
        assert events_resp.status_code == 200
        assert "orchestrating" in events_resp.text
        assert "leading" in events_resp.text

        # Verify 3-tier thinking steps and duration tracking
        steps = job.get("steps", [])
        assert len(steps) > 0
        roles_found = {s.get("data", {}).get("role") for s in steps if isinstance(s.get("data"), dict)}
        assert "orchestrator" in roles_found
        assert "subtask" in roles_found
        assert "lead" in roles_found

        # Verify time taken / elapsed_s exists in provider runs and steps
        runs = job.get("provider_runs", [])
        assert len(runs) >= 2
        for r in runs:
            assert "elapsed_s" in r
            assert r["elapsed_s"] >= 0
            assert "elapsed_ms" in r


def test_agent_pipeline_same_provider_for_all_roles(monkeypatch: MonkeyPatch) -> None:
    """Verifies that when Orchestrator, Sub-providers, and Lead provider are ALL the same provider
    (e.g. Copilot), each entity receives a distinct role and provider_role_key without colliding.
    """
    class AllCopilotFakeAdapter(FakeAdapter):
        async def ask(self, prompt: str, **kwargs: Any):
            # If prompt asks for orchestrator plan, return a plan where subtasks are also copilot
            if "Master Research Orchestrator" in prompt or "agents_dispatch" in prompt:
                from app.adapters.base import ProviderResult
                plan_json = """{
  "research_topic": "Test Topic",
  "agents_dispatch": [
    {
      "id": "copilot",
      "name": "Microsoft Copilot",
      "config": {"thinking": true},
      "sub_topic": "Kiến trúc tổng quan",
      "question": "Phân tích kiến trúc tổng quan"
    },
    {
      "id": "copilot",
      "name": "Microsoft Copilot",
      "config": {"thinking": true},
      "sub_topic": "Dẫn chứng thực tế",
      "question": "Tìm kiếm dẫn chứng thực tế"
    }
  ]
}"""
                now = datetime.now(timezone.utc)
                return ProviderResult(
                    provider=self.name,
                    prompt=prompt,
                    status="ok",
                    answer_markdown=plan_json,
                    artifact_paths=[],
                    artifacts=[],
                    sources=[],
                    started_at=now,
                    finished_at=now,
                )
            return await super().ask(prompt, **kwargs)

    monkeypatch.setattr(pipeline, "create_adapter", lambda provider: AllCopilotFakeAdapter(provider))
    monkeypatch.setattr(agent_pipeline, "create_adapter", lambda provider: AllCopilotFakeAdapter(provider))

    with TestClient(app) as client:
        payload = {
            "query": "So sánh Copilot trong mọi vai trò",
            "orchestrator_provider": "copilot",
            "lead_provider": "copilot",
            "tone": "professional",
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

        # Check dispatch items have unique branch_index and provider_role_key
        dispatch = job.get("orchestrator_dispatch", [])
        assert len(dispatch) == 2
        assert dispatch[0]["branch_index"] == 1
        assert dispatch[0]["provider_role_key"] == "subtask:copilot_1"
        assert dispatch[1]["branch_index"] == 2
        assert dispatch[1]["provider_role_key"] == "subtask:copilot_2"

        # Check provider runs have distinct provider_role_key
        runs = job.get("provider_runs", [])
        assert len(runs) == 2
        assert runs[0]["provider_role_key"] == "subtask:copilot_1"
        assert runs[1]["provider_role_key"] == "subtask:copilot_2"

        # Check steps have distinct provider_role_key across orchestrator, subtask, and lead
        steps = job.get("steps", [])
        role_keys_found = {
            s.get("data", {}).get("provider_role_key")
            for s in steps
            if isinstance(s.get("data"), dict) and s.get("data", {}).get("provider_role_key")
        }
        assert "orchestrator" in role_keys_found
        assert "subtask:copilot_1" in role_keys_found
        assert "subtask:copilot_2" in role_keys_found
        assert "lead" in role_keys_found

