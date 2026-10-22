import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.api.schemas import AgentResearchRequest, ResearchResponse
from app.core.db import SessionLocal, init_db
from app.core.models import Job
from app.orchestrator.agent_pipeline import (
    build_consensus_scoring_prompt,
    build_lead_prompt,
    build_thesis_extraction_prompt,
    run_delphi_consensus,
)


@pytest.fixture(autouse=True)
async def ensure_db_initialized():
    await init_db()


def test_consensus_schema_and_defaults():
    req = AgentResearchRequest(
        query="So sánh Kubernetes và Nomad",
        orchestrator_provider="gemini",
        lead_provider="chatgpt",
    )
    assert req.enable_consensus is False
    assert req.consensus_providers is None
    assert req.consensus_threshold == 0.8
    assert req.max_consensus_rounds == 3

    custom_req = AgentResearchRequest(
        query="So sánh Kubernetes và Nomad",
        orchestrator_provider="gemini",
        lead_provider="chatgpt",
        enable_consensus=True,
        consensus_providers=["qwen", "deepseek", "chatgpt"],
        consensus_threshold=0.5,
        max_consensus_rounds=4,
    )
    assert custom_req.enable_consensus is True
    assert custom_req.consensus_providers == ["qwen", "deepseek", "chatgpt"]
    assert custom_req.consensus_threshold == 0.5
    assert custom_req.max_consensus_rounds == 4

    job = Job(id="job-consensus-test", query="So sánh Kubernetes và Nomad")
    assert job.enable_consensus is False
    assert job.consensus_threshold == 0.8
    assert job.max_consensus_rounds == 3
    assert job.consensus_scores_json is None


def test_build_thesis_extraction_prompt():
    prompt = build_thesis_extraction_prompt(
        research_topic="Đánh giá hiệu năng và chi phí của Llama 3 so với GPT-4",
        findings_summary="Llama 3 70B đạt 82 MMLU với chi phí hosting thấp hơn 4 lần GPT-4.",
        debate_summary="[red_team R1]: Red Team nghi ngờ chi phí bảo trì cluster khi tự host.",
    )
    assert "Đánh giá hiệu năng và chi phí" in prompt
    assert "Llama 3 70B đạt 82 MMLU" in prompt
    assert "Red Team nghi ngờ chi phí bảo trì" in prompt
    assert "TOP 5-8 most important theses" in prompt


def test_build_consensus_scoring_prompt():
    theses = [
        {"id": "T1", "thesis": "Llama 3 giảm chi phí biên 65% cho khối lượng inference cao."},
        {"id": "T2", "thesis": "Tự host đòi hỏi đội ngũ SRE chuyên nghiệp làm tăng chi phí cố định."},
    ]
    prompt_r1 = build_consensus_scoring_prompt(theses, round_number=1)
    assert "T1" in prompt_r1
    assert "Llama 3 giảm chi phí biên" in prompt_r1
    assert "Delphi Scoring Round 1" in prompt_r1
    assert "Aggregate Scores from Previous Round" not in prompt_r1

    prev_agg = [
        {"id": "T1", "mean": 4.5, "stdev": 0.5},
        {"id": "T2", "mean": 3.8, "stdev": 1.2},
    ]
    prompt_r2 = build_consensus_scoring_prompt(theses, round_number=2, previous_aggregate=prev_agg)
    assert "Delphi Scoring Round 2" in prompt_r2
    assert "Aggregate Scores from Previous Round" in prompt_r2
    assert "4.5" in prompt_r2


def test_build_lead_prompt_with_consensus_result():
    findings = [
        {"provider": "gemini", "branch": "Hiệu năng", "answer_md": "Benchmark vượt trội."},
    ]
    consensus_result = {
        "converged": True,
        "theses": [
            {"id": "T1", "thesis": "Hệ thống đáp ứng SLA 99.9%."},
        ],
        "final_scores": [
            {"id": "T1", "mean": 4.8, "stdev": 0.2},
        ],
    }
    prompt = build_lead_prompt(
        research_topic="Đánh giá SLA hệ thống",
        findings=findings,
        tone="professional",
        consensus_result=consensus_result,
    )
    assert "Delphi Consensus Results" in prompt
    assert "Convergence Achieved: ✅ Yes" in prompt
    assert "Hệ thống đáp ứng SLA 99.9%" in prompt
    assert "Score: 4.8/5" in prompt


class FakeResult:
    def __init__(self, answer_markdown: str):
        self.answer_markdown = answer_markdown
        self.conversation_url = "http://fake-conv-url"


@pytest.mark.asyncio
async def test_run_delphi_consensus_converged_round_1():
    job_id = f"delphi-job-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        session.add(Job(
            id=job_id,
            query="Test Topic",
            config_json="{}",
            status="researching",
            enable_consensus=True,
        ))
        await session.commit()

    thesis_json = json.dumps([
        {"id": "T1", "thesis": "Luận điểm A", "category": "technical", "supporting_evidence": "Bằng chứng A"},
        {"id": "T2", "thesis": "Luận điểm B", "category": "economic", "supporting_evidence": "Bằng chứng B"},
    ])
    score_p1 = json.dumps([
        {"id": "T1", "score": 4, "reasoning": "Rất chuẩn"},
        {"id": "T2", "score": 5, "reasoning": "Rất chuẩn"},
    ])
    score_p2 = json.dumps([
        {"id": "T1", "score": 4, "reasoning": "Đồng tình"},
        {"id": "T2", "score": 5, "reasoning": "Đồng tình"},
    ])

    call_count = 0
    async def fake_ask(prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return FakeResult(thesis_json)
        elif call_count == 2:
            return FakeResult(score_p1)
        else:
            return FakeResult(score_p2)

    mock_adapter = AsyncMock()
    mock_adapter.ask = fake_ask

    runs = [{"provider": "gemini", "branch": "Core", "status": "ok", "answer_md": "Data A"}]
    cancel_event = asyncio.Event()

    with patch("app.orchestrator.agent_pipeline.create_adapter", return_value=mock_adapter), \
         patch("app.orchestrator.agent_pipeline.BrowserSessionManager.close_session", new_callable=AsyncMock):
        res = await run_delphi_consensus(
            job_id=job_id,
            research_topic="Test Topic",
            runs=runs,
            debate_transcript=[],
            consensus_providers=["gemini", "deepseek"],
            threshold=0.8,
            max_rounds=3,
            cancel_event=cancel_event,
        )

        assert res["converged"] is True
        assert len(res["theses"]) == 2
        assert len(res["rounds"]) == 1
        assert res["final_scores"][0]["mean"] == 4.0
        assert res["final_scores"][0]["stdev"] == 0.0


@pytest.mark.asyncio
async def test_run_delphi_consensus_max_rounds_cap():
    job_id = f"delphi-job-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        session.add(Job(
            id=job_id,
            query="Controversial Topic",
            config_json="{}",
            status="researching",
            enable_consensus=True,
        ))
        await session.commit()

    thesis_json = json.dumps([
        {"id": "T1", "thesis": "Luận điểm tranh cãi", "category": "risk", "supporting_evidence": "Chưa rõ"},
    ])
    call_count = 0
    async def fake_ask(prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return FakeResult(thesis_json)
        elif call_count % 2 == 0:
            return FakeResult(json.dumps([{"id": "T1", "score": 1}]))
        else:
            return FakeResult(json.dumps([{"id": "T1", "score": 5}]))

    mock_adapter = AsyncMock()
    mock_adapter.ask = fake_ask
    cancel_event = asyncio.Event()

    with patch("app.orchestrator.agent_pipeline.create_adapter", return_value=mock_adapter), \
         patch("app.orchestrator.agent_pipeline.BrowserSessionManager.close_session", new_callable=AsyncMock):
        res = await run_delphi_consensus(
            job_id=job_id,
            research_topic="Controversial Topic",
            runs=[{"provider": "gemini", "branch": "Branch", "status": "ok", "answer_md": "Data"}],
            debate_transcript=[],
            consensus_providers=["p1", "p2"],
            threshold=0.5,
            max_rounds=2,
            cancel_event=cancel_event,
        )

        assert res["converged"] is False
        assert len(res["rounds"]) == 2
        assert res["final_scores"][0]["stdev"] > 0.5


@pytest.mark.asyncio
async def test_run_delphi_consensus_provider_error_handling():
    job_id = f"delphi-job-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        session.add(Job(
            id=job_id,
            query="Resilience Topic",
            config_json="{}",
            status="researching",
            enable_consensus=True,
        ))
        await session.commit()

    thesis_json = json.dumps([
        {"id": "T1", "thesis": "Luận điểm chịu lỗi", "category": "technical", "supporting_evidence": "OK"},
    ])
    call_count = 0
    async def fake_ask(prompt, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return FakeResult(thesis_json)
        elif call_count == 2:
            raise RuntimeError("Provider 1 network timeout")
        else:
            return FakeResult(json.dumps([{"id": "T1", "score": 4}]))

    mock_adapter = AsyncMock()
    mock_adapter.ask = fake_ask
    cancel_event = asyncio.Event()

    with patch("app.orchestrator.agent_pipeline.create_adapter", return_value=mock_adapter), \
         patch("app.orchestrator.agent_pipeline.BrowserSessionManager.close_session", new_callable=AsyncMock):
        res = await run_delphi_consensus(
            job_id=job_id,
            research_topic="Resilience Topic",
            runs=[{"provider": "gemini", "branch": "Branch", "status": "ok", "answer_md": "Data"}],
            debate_transcript=[],
            consensus_providers=["p1", "p2"],
            threshold=0.8,
            max_rounds=1,
            cancel_event=cancel_event,
        )

        assert len(res["rounds"]) == 1
        assert res["final_scores"][0]["n"] == 1
        assert res["final_scores"][0]["mean"] == 4.0


@pytest.mark.asyncio
async def test_run_delphi_consensus_cancelled():
    job_id = f"delphi-job-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        session.add(Job(
            id=job_id,
            query="Cancelled Topic",
            config_json="{}",
            status="researching",
            enable_consensus=True,
        ))
        await session.commit()

    cancel_event = asyncio.Event()
    cancel_event.set()

    res = await run_delphi_consensus(
        job_id=job_id,
        research_topic="Cancelled Topic",
        runs=[{"provider": "gemini", "branch": "Branch", "status": "ok", "answer_md": "Data"}],
        debate_transcript=[],
        consensus_providers=["gemini"],
        threshold=0.8,
        max_rounds=3,
        cancel_event=cancel_event,
    )
    assert res["converged"] is False
    assert len(res["theses"]) == 0
