from __future__ import annotations

import asyncio
import json
import pytest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

from app.api.schemas import AgentResearchRequest
from app.orchestrator.agent_pipeline import (
    analyze_complexity,
    build_complexity_analysis_prompt,
    build_orchestrator_prompt,
    run_agent_pipeline,
)
from app.core.db import SessionLocal, init_db
from app.core.models import Job, JobEvent
from app.adapters.base import ProviderResult
from sqlmodel import select


def _make_result(prov: str, prompt: str, text: str) -> ProviderResult:
    now = datetime.now(timezone.utc)
    return ProviderResult(
        provider=prov,
        prompt=prompt,
        answer_markdown=text,
        sources=[],
        conversation_url=f"https://{prov}.com/c/test",
        status="ok",
        started_at=now,
        finished_at=now,
        artifact_paths=[],
    )


def test_schema_auto_scale_defaults():
    req = AgentResearchRequest(
        query="So sánh Kubernetes và Nomad",
        orchestrator_provider="chatgpt",
        lead_provider="claude",
    )
    assert req.auto_scale_agents is True
    assert req.min_agents == 2
    assert req.max_agents == 5

    # Check bounds validation auto-clamps max_agents if min > max
    req_clamped = AgentResearchRequest(
        query="Test query",
        orchestrator_provider="chatgpt",
        lead_provider="claude",
        min_agents=6,
        max_agents=4,
    )
    assert req_clamped.min_agents == 6
    assert req_clamped.max_agents == 6


def test_build_complexity_analysis_prompt():
    prompt = build_complexity_analysis_prompt(
        research_topic="Đánh giá hiệu năng và chi phí của Kafka vs RabbitMQ",
        available_providers=["chatgpt", "claude", "deepseek"],
        min_agents=2,
        max_agents=6,
    )
    assert "Đánh giá hiệu năng và chi phí của Kafka vs RabbitMQ" in prompt
    assert "Available Provider Count: 3" in prompt
    assert "Allowed Range: 2 to 6 agents" in prompt
    assert "complexity_level" in prompt
    assert "recommended_agent_count" in prompt
    assert "recommended_groups" in prompt


def test_build_orchestrator_prompt_dynamic_vs_default():
    # Without complexity info
    prompt_default = build_orchestrator_prompt(
        research_topic="Test topic",
        allowed_providers=["chatgpt", "claude"],
    )
    assert "2 to 5 specialized sub-tasks" in prompt_default
    assert "Decompose the topic into 2 to 5 distinct" in prompt_default

    # With complexity info
    complexity = {
        "complexity_level": "high",
        "recommended_agent_count": 4,
        "recommended_groups": ["researcher", "infra", "red_team"],
        "reasoning": "Complex architectural decision requiring benchmarks and critique.",
    }
    prompt_dynamic = build_orchestrator_prompt(
        research_topic="Test topic",
        allowed_providers=["chatgpt", "claude"],
        complexity_info=complexity,
    )
    assert "into exactly 4 specialized sub-tasks" in prompt_dynamic
    assert "Decompose the topic into exactly 4 distinct" in prompt_dynamic
    assert "Prioritize assigning agents to these role groups: researcher, infra, red_team." in prompt_dynamic


@pytest.mark.asyncio
async def test_analyze_complexity_success_and_clamping():
    fake_response = _make_result(
        "chatgpt",
        "test prompt",
        """```json
{
  "complexity_level": "high",
  "recommended_agent_count": 8,
  "recommended_groups": ["researcher", "infra", "invalid_group", "red_team"],
  "reasoning": "Very complex distributed systems challenge."
}
```""",
    )

    mock_adapter = AsyncMock()
    mock_adapter.ask.return_value = fake_response

    with patch("app.orchestrator.agent_pipeline.create_adapter", return_value=mock_adapter), \
         patch("app.browser.session.BrowserSessionManager.close_session", new_callable=AsyncMock):
        result = await analyze_complexity(
            job_id="test-job-scale",
            research_topic="Architecture of Distributed Raft Consensus",
            orchestrator_prov="chatgpt",
            orch_config={"model": "gpt-4o"},
            available_providers=["chatgpt", "claude"],
            min_agents=2,
            max_agents=5,  # 8 should be clamped to 5
        )

    assert result["complexity_level"] == "high"
    assert result["recommended_agent_count"] == 5
    # "invalid_group" must be filtered out
    assert result["recommended_groups"] == ["researcher", "infra", "red_team"]
    assert "Very complex" in result["reasoning"]


@pytest.mark.asyncio
async def test_analyze_complexity_fallback_on_error():
    mock_adapter = AsyncMock()
    mock_adapter.ask.side_effect = RuntimeError("Provider timeout")

    with patch("app.orchestrator.agent_pipeline.create_adapter", return_value=mock_adapter), \
         patch("app.browser.session.BrowserSessionManager.close_session", new_callable=AsyncMock):
        result = await analyze_complexity(
            job_id="test-job-scale-fail",
            research_topic="Simple query",
            orchestrator_prov="chatgpt",
            orch_config={},
            available_providers=["chatgpt"],
            min_agents=2,
            max_agents=4,
        )

    # Should safely return fallback without raising
    assert result["complexity_level"] == "medium"
    assert 2 <= result["recommended_agent_count"] <= 4
    assert result["recommended_groups"] == ["researcher", "infra"]


import uuid

@pytest.mark.asyncio
async def test_run_agent_pipeline_emits_complexity_event():
    await init_db()

    job_id = f"test-scale-pipeline-{uuid.uuid4().hex[:8]}"
    topic = "So sánh Vue 3 Composition API vs React Hooks"
    config_dict = {
        "auto_scale_agents": True,
        "min_agents": 2,
        "max_agents": 4,
    }

    async with SessionLocal() as session:
        job = Job(
            id=job_id,
            query=topic,
            config_json=json.dumps(config_dict),
            status="queued",
            job_type="agent",
            orchestrator_provider="chatgpt",
            lead_provider="chatgpt",
            subtasks_total=1,
        )
        session.add(job)
        await session.commit()

    cancel_event = asyncio.Event()

    # Complexity analysis response recommending 3 agents
    complexity_json = json.dumps({
        "complexity_level": "medium",
        "recommended_agent_count": 3,
        "recommended_groups": ["researcher", "infra"],
        "reasoning": "Frontend framework comparison requiring benchmark and DX analysis.",
    })

    # Orchestrator response with 2 agents
    orch_json = json.dumps({
        "research_topic": topic,
        "agents_dispatch": [
            {
                "id": "chatgpt",
                "name": "ChatGPT",
                "role_group": "researcher",
                "sub_topic": "DX & Syntax Comparison",
                "question": "Compare DX of React Hooks vs Vue 3",
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "role_group": "infra",
                "sub_topic": "Reactivity & Performance",
                "question": "Compare reactivity engine performance",
            },
        ],
    })

    class FakeAdapterForScale:
        def __init__(self, prov: str):
            self.prov = prov

        async def ask(
            self,
            prompt: str,
            *,
            timeout_s: int = 60,
            mode: str = "default",
            on_step: Any = None,
            conversation_url: str | None = None,
        ) -> ProviderResult:
            if "Research Planning Analyst" in prompt:
                return _make_result(self.prov, prompt, f"```json\n{complexity_json}\n```")
            elif "Master Research Orchestrator" in prompt:
                # Verify complexity instruction was present in prompt
                assert "into exactly 3 specialized sub-tasks" in prompt
                return _make_result(self.prov, prompt, f"```json\n{orch_json}\n```")
            elif "Lead Research Synthesizer" in prompt:
                return _make_result(self.prov, prompt, "# Final Comparison Report\nAll good.")
            return _make_result(self.prov, prompt, f"Detailed research from {self.prov}.")

    with patch("app.orchestrator.agent_pipeline.create_adapter", side_effect=FakeAdapterForScale), \
         patch("app.browser.session.BrowserSessionManager.close_session", new_callable=AsyncMock):
        await run_agent_pipeline(
            job_id=job_id,
            cancel_event=cancel_event,
        )

    async with SessionLocal() as session:
        db_j = await session.get(Job, job_id)
        assert db_j is not None
        assert db_j.status == "completed"

    # Verify complexity_analyzed event was recorded
    async with SessionLocal() as session:
        events = (await session.exec(
            select(JobEvent).where(JobEvent.job_id == job_id, JobEvent.event_type == "complexity_analyzed")
        )).all()

        assert len(events) == 1
        ev = events[0]
        assert "medium" in ev.message
        data = json.loads(ev.data_json)
        assert data["complexity_level"] == "medium"
        assert data["recommended_agent_count"] == 3
