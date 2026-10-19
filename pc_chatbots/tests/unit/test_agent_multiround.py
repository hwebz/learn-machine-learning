from __future__ import annotations

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


class RecordingFakeAdapter(FakeAdapter):
    """A fake adapter that records incoming prompts and conversation URLs."""
    recorded_calls: list[dict[str, Any]] = []

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.provider = name

    async def ask(
        self,
        prompt: str,
        *,
        timeout_s: int = 120,
        mode: str = "default",
        on_step: Any = None,
        conversation_url: str | None = None,
        **kwargs: Any,
    ) -> Any:
        RecordingFakeAdapter.recorded_calls.append({
            "provider": self.provider,
            "prompt": prompt,
            "conversation_url": conversation_url,
            "kwargs": kwargs,
        })
        res = await super().ask(
            prompt,
            timeout_s=timeout_s,
            mode=mode,
            on_step=on_step,
            conversation_url=conversation_url,
        )
        res.conversation_url = conversation_url or f"https://{self.provider}.example.com/chat/session_123"
        return res


def test_agent_multiround_lifecycle_with_summarization(monkeypatch: MonkeyPatch) -> None:
    RecordingFakeAdapter.recorded_calls = []

    def make_adapter(provider: str) -> RecordingFakeAdapter:
        return RecordingFakeAdapter(provider)

    monkeypatch.setattr(pipeline, "create_adapter", make_adapter)
    monkeypatch.setattr(agent_pipeline, "create_adapter", make_adapter)

    with TestClient(app) as client:
        # === ROUND 1: Initial Agent Research ===
        r1_payload = {
            "query": "Tìm hiểu kiến trúc Transformer và Attention Mechanism",
            "orchestrator_provider": "gemini",
            "orchestrator_config": {"model": "pro"},
            "lead_provider": "chatgpt",
            "lead_config": {"thinking": True},
            "summarization_provider": "9router",
            "summarization_config": {"model_id": "Daily"},
            "tone": "professional",
            "delegated_providers": ["copilot", "deepseek"],
        }
        res1 = client.post("/agent-research", headers=API_HEADERS, json=r1_payload)
        assert res1.status_code == 202
        job1_id = res1.json()["job_id"]

        # Wait for round 1 completion
        deadline = time.monotonic() + 10
        job1 = None
        while time.monotonic() < deadline:
            resp = client.get(f"/research/{job1_id}", headers=API_HEADERS)
            assert resp.status_code == 200
            job1 = resp.json()
            if job1["status"] in ("completed", "failed"):
                break
            time.sleep(0.05)

        assert job1 is not None
        assert job1["status"] == "completed"
        assert job1["summarization_provider"] == "9router"
        assert job1["summarization_config"] == {"model_id": "Daily"}
        assert job1["provider_conversations"] is not None
        assert "orchestrator" in job1["provider_conversations"]
        assert "lead" in job1["provider_conversations"]

        r1_urls = job1["provider_conversations"]
        orch_url = r1_urls["orchestrator"]
        lead_url = r1_urls["lead"]

        # Clear recorded calls to verify round 2 behavior specifically
        RecordingFakeAdapter.recorded_calls = []

        # === ROUND 2: Follow-up Prompt in the same Conversation ===
        r2_payload = {
            "query": "So sánh chi tiết Self-Attention và Cross-Attention",
            "parent_job_id": job1_id,
            "orchestrator_provider": "gemini",
            "orchestrator_config": {"model": "pro"},
            "lead_provider": "chatgpt",
            "lead_config": {"thinking": True},
            "summarization_provider": "9router",
            "summarization_config": {"model_id": "Daily"},
            "tone": "professional",
            "delegated_providers": ["copilot", "deepseek"],
            "conversation_urls": r1_urls,
        }
        res2 = client.post("/agent-research", headers=API_HEADERS, json=r2_payload)
        assert res2.status_code == 202
        job2_id = res2.json()["job_id"]

        # Wait for round 2 completion
        deadline = time.monotonic() + 10
        job2 = None
        while time.monotonic() < deadline:
            resp = client.get(f"/research/{job2_id}", headers=API_HEADERS)
            assert resp.status_code == 200
            job2 = resp.json()
            if job2["status"] in ("completed", "failed"):
                break
            time.sleep(0.05)

        assert job2 is not None
        assert job2["status"] == "completed"
        assert job2["parent_job_id"] == job1_id
        assert job2["conversation_id"] == job1.get("conversation_id", job1_id)
        assert job2["context_summary"] is not None
        assert len(job2["context_summary"]) > 0

        # Verify Sequential Phase 0 executed with 9router
        summarizer_calls = [
            c for c in RecordingFakeAdapter.recorded_calls if c["provider"] == "9router"
        ]
        assert len(summarizer_calls) >= 1
        sum_prompt = summarizer_calls[0]["prompt"]
        assert "Ongoing Research History" in sum_prompt
        assert "So sánh chi tiết Self-Attention và Cross-Attention" in sum_prompt

        # Verify Orchestrator received previous round's conversation URL and context
        orch_calls = [
            c for c in RecordingFakeAdapter.recorded_calls if c["provider"] == "gemini"
        ]
        assert len(orch_calls) >= 1
        assert "Research Context & Established Facts from Previous Rounds" in orch_calls[0]["prompt"]

        # Verify Subtask delegated providers received Context Briefing
        sub_calls = [
            c for c in RecordingFakeAdapter.recorded_calls
            if c["provider"] in ("copilot", "deepseek")
        ]
        assert len(sub_calls) >= 1
        for sub_call in sub_calls:
            assert "[BỐI CẢNH NGHIÊN CỨU TỪ CÁC VÒNG TRƯỚC]" in sub_call["prompt"]

        # Verify Lead received previous round's conversation URL and context
        lead_calls = [
            c for c in RecordingFakeAdapter.recorded_calls if c["provider"] == "chatgpt"
        ]
        assert len(lead_calls) >= 1
        assert lead_calls[0]["conversation_url"] == lead_url
        assert "Background Context from Previous Research Rounds" in lead_calls[0]["prompt"]

        # Verify SSE events included "summarizing" phase
        events_resp = client.get(f"/research/{job2_id}/events", headers=API_HEADERS)
        assert events_resp.status_code == 200
        events_text = events_resp.text
        assert "summarizing" in events_text
        assert "context_summarized" in events_text
