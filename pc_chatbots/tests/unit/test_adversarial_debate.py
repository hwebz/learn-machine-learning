from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.schemas import AgentResearchRequest, JobStatus
from app.core.db import SessionLocal
from app.core.models import Job, JobEvent
from app.orchestrator.agent_pipeline import (
    build_lead_prompt,
    build_matrix_report_prompt,
    build_rebuttal_prompt,
    build_red_team_prompt,
    run_adversarial_debate,
    run_agent_pipeline,
)


def test_debate_schema_and_defaults() -> None:
    req = AgentResearchRequest(
        query="Test query",
        orchestrator_provider="gemini",
        lead_provider="chatgpt",
    )
    assert req.enable_debate is False
    assert req.debate_provider is None
    assert req.debate_defender_provider is None
    assert req.max_debate_rounds == 2
    assert req.debate_config == {}

    req_custom = AgentResearchRequest(
        query="Test query",
        orchestrator_provider="gemini",
        lead_provider="chatgpt",
        enable_debate=True,
        debate_provider="claude",
        debate_defender_provider="chatgpt",
        max_debate_rounds=3,
        debate_config={"temperature": 0.7},
    )
    assert req_custom.enable_debate is True
    assert req_custom.debate_provider == "claude"
    assert req_custom.debate_defender_provider == "chatgpt"
    assert req_custom.max_debate_rounds == 3
    assert req_custom.debate_config == {"temperature": 0.7}


def test_build_red_team_prompt() -> None:
    prompt = build_red_team_prompt(
        research_topic="Quantum Computing Scalability",
        findings_summary="Superconducting qubits have reached 1000 qubits.",
        fact_check_summary="- ⚠️ Error correction claim is disputed",
    )
    assert "Quantum Computing Scalability" in prompt
    assert "Superconducting qubits" in prompt
    assert "Error correction claim is disputed" in prompt
    assert "Red Team" in prompt
    assert "TOP 5 most critical weaknesses" in prompt


def test_build_rebuttal_prompt() -> None:
    prompt = build_rebuttal_prompt(
        research_topic="Quantum Computing Scalability",
        original_findings="Superconducting qubits have reached 1000 qubits.",
        critique="Qubit fidelity degrades exponentially with volume.",
        round_number=1,
    )
    assert "Round 1" in prompt
    assert "Research Defense Analyst" in prompt
    assert "Qubit fidelity degrades exponentially" in prompt
    assert "CONCEDE" in prompt
    assert "REBUT" in prompt


def test_build_lead_prompt_with_debate_transcript() -> None:
    transcript = [
        {"round": 1, "side": "red_team", "provider": "claude", "content": "Critique point: Lack of thermal isolation data."},
        {"round": 1, "side": "defender", "provider": "chatgpt", "content": "Defense: Cryogenic cooling solves this below 10mK."},
    ]
    prompt = build_lead_prompt(
        research_topic="Quantum Computing",
        findings=[{"provider": "gemini", "branch": "Hardware", "answer_md": "Hardware analysis..."}],
        tone="professional",
        debate_transcript=transcript,
    )
    assert "Adversarial Debate Results:" in prompt
    assert "Lack of thermal isolation data" in prompt
    assert "Cryogenic cooling solves this" in prompt
    assert "Your synthesis MUST address the critiques raised" in prompt


def test_build_matrix_report_prompt_with_debate_transcript() -> None:
    transcript = [
        {"round": 1, "side": "red_team", "provider": "claude", "content": "Red team warning on cost."},
        {"round": 1, "side": "defender", "provider": "chatgpt", "content": "Defender note on ROI."},
    ]
    prompt = build_matrix_report_prompt(
        research_topic="Quantum Computing",
        findings=[{"provider": "gemini", "branch": "Hardware", "answer_md": "Hardware analysis..."}],
        tone="professional",
        debate_transcript=transcript,
    )
    assert "Adversarial Debate Results:" in prompt
    assert "Red team warning on cost" in prompt
    assert "Defender note on ROI" in prompt


@pytest.mark.asyncio
async def test_run_adversarial_debate_success() -> None:
    job_id = f"test-debate-job-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        job = Job(
            id=job_id,
            query="Deep learning architectures",
            config_json="{}",
            status="researching",
            enable_debate=True,
            debate_provider="claude",
            debate_defender_provider="chatgpt",
            max_debate_rounds=2,
        )
        session.add(job)
        await session.commit()

    runs = [
        {"provider": "gemini", "branch": "Transformers", "answer_md": "Transformers scale O(N^2).", "status": "ok"},
        {"provider": "perplexity", "branch": "SSMs", "answer_md": "Mamba scales O(N).", "status": "ok"},
    ]
    fact_check_claims = [
        {"claim": "Transformers scale quadratically", "verdict": "supported"},
        {"claim": "SSMs strictly outperform attention", "verdict": "unsupported"},
    ]

    mock_rt_res = MagicMock()
    mock_rt_res.answer_markdown = "Red Team critique: Attention is still superior for recall."
    mock_rt_res.conversation_url = "http://rt.url"

    mock_def_res = MagicMock()
    mock_def_res.answer_markdown = "Defender defense: Hybrid architectures combine both."
    mock_def_res.conversation_url = "http://def.url"

    mock_rt_adapter = MagicMock()
    mock_rt_adapter.ask = AsyncMock(return_value=mock_rt_res)

    mock_def_adapter = MagicMock()
    mock_def_adapter.ask = AsyncMock(return_value=mock_def_res)

    def adapter_side_effect(prov: str) -> Any:
        if prov == "claude":
            return mock_rt_adapter
        return mock_def_adapter

    with patch("app.orchestrator.agent_pipeline.create_adapter", side_effect=adapter_side_effect), \
         patch("app.orchestrator.agent_pipeline.BrowserSessionManager.close_session", new_callable=AsyncMock):

        cancel_event = asyncio.Event()
        transcript = await run_adversarial_debate(
            job_id=job_id,
            research_topic="Deep learning architectures",
            runs=runs,
            fact_check_claims=fact_check_claims,
            debate_provider="claude",
            debate_defender_provider="chatgpt",
            debate_config={},
            max_rounds=2,
            cancel_event=cancel_event,
            initial_conv_urls={},
        )

    # 2 rounds * 2 sides = 4 entries
    assert len(transcript) == 4
    assert transcript[0]["side"] == "red_team"
    assert transcript[0]["round"] == 1
    assert transcript[1]["side"] == "defender"
    assert transcript[1]["round"] == 1
    assert transcript[2]["side"] == "red_team"
    assert transcript[2]["round"] == 2
    assert transcript[3]["side"] == "defender"
    assert transcript[3]["round"] == 2

    # Check persistence in DB
    async with SessionLocal() as session:
        saved_job = await session.get(Job, job_id)
        assert saved_job is not None
        assert saved_job.debate_transcript_json is not None
        saved_trans = json.loads(saved_job.debate_transcript_json)
        assert len(saved_trans) == 4


@pytest.mark.asyncio
async def test_run_adversarial_debate_red_team_error() -> None:
    job_id = f"test-debate-fail-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        job = Job(
            id=job_id,
            query="Deep learning architectures",
            config_json="{}",
            status="researching",
        )
        session.add(job)
        await session.commit()

    runs = [{"provider": "gemini", "branch": "B1", "answer_md": "Some answer", "status": "ok"}]

    mock_rt_adapter = MagicMock()
    mock_rt_adapter.ask = AsyncMock(side_effect=RuntimeError("Provider timed out"))

    with patch("app.orchestrator.agent_pipeline.create_adapter", return_value=mock_rt_adapter), \
         patch("app.orchestrator.agent_pipeline.BrowserSessionManager.close_session", new_callable=AsyncMock):

        cancel_event = asyncio.Event()
        transcript = await run_adversarial_debate(
            job_id=job_id,
            research_topic="Deep learning architectures",
            runs=runs,
            fact_check_claims=[],
            debate_provider="claude",
            debate_defender_provider=None,
            debate_config={},
            max_rounds=2,
            cancel_event=cancel_event,
            initial_conv_urls={},
        )

    # Debate handles error gracefully and stops
    assert len(transcript) == 1
    assert transcript[0]["side"] == "red_team"
    assert "Provider timed out" in transcript[0].get("error", "")


@pytest.mark.asyncio
async def test_run_adversarial_debate_defender_error() -> None:
    job_id = f"test-debate-def-fail-{uuid.uuid4().hex[:8]}"
    async with SessionLocal() as session:
        job = Job(
            id=job_id,
            query="Deep learning architectures",
            config_json="{}",
            status="researching",
        )
        session.add(job)
        await session.commit()

    runs = [{"provider": "gemini", "branch": "B1", "answer_md": "Some answer", "status": "ok"}]

    mock_rt_res = MagicMock()
    mock_rt_res.answer_markdown = "Critique content"
    mock_rt_adapter = MagicMock()
    mock_rt_adapter.ask = AsyncMock(return_value=mock_rt_res)

    mock_def_adapter = MagicMock()
    mock_def_adapter.ask = AsyncMock(side_effect=RuntimeError("Defender quota exceeded"))

    def adapter_side_effect(prov: str) -> Any:
        if prov == "claude":
            return mock_rt_adapter
        return mock_def_adapter

    with patch("app.orchestrator.agent_pipeline.create_adapter", side_effect=adapter_side_effect), \
         patch("app.orchestrator.agent_pipeline.BrowserSessionManager.close_session", new_callable=AsyncMock):

        cancel_event = asyncio.Event()
        transcript = await run_adversarial_debate(
            job_id=job_id,
            research_topic="Deep learning architectures",
            runs=runs,
            fact_check_claims=[],
            debate_provider="claude",
            debate_defender_provider="chatgpt",
            debate_config={},
            max_rounds=2,
            cancel_event=cancel_event,
            initial_conv_urls={},
        )

    assert len(transcript) == 2
    assert transcript[0]["side"] == "red_team"
    assert transcript[1]["side"] == "defender"
    assert "Defender quota exceeded" in transcript[1].get("error", "")
