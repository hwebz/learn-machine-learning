from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas import AgentResearchRequest, ResearchRequest
from app.core.config import settings
from app.main import app
from app.orchestrator.agent_pipeline import (
    build_complexity_analysis_prompt,
    build_summarization_prompt,
    build_lead_prompt,
    build_matrix_report_prompt,
    build_orchestrator_prompt,
    build_red_team_prompt,
    build_rebuttal_prompt,
    build_thesis_extraction_prompt,
)

API_HEADERS = {"X-API-Key": settings.api_key}


def test_schema_accepts_12k_words_query() -> None:
    # 12,000 words ~ 72,000 characters
    large_query = "machine learning " * 12_000
    assert len(large_query) > 70_000

    # 1. ResearchRequest validation
    req = ResearchRequest(query=large_query, providers=["perplexity", "gemini"])
    assert len(req.query) > 70_000

    # 2. AgentResearchRequest validation
    agent_req = AgentResearchRequest(
        query=large_query,
        orchestrator_provider="deepseek",
        lead_provider="claude",
    )
    assert len(agent_req.query) > 70_000


def test_schema_rejects_exceeding_500k_chars() -> None:
    excessive_query = "x" * 500_001
    with pytest.raises(ValidationError):
        ResearchRequest(query=excessive_query)

    with pytest.raises(ValidationError):
        AgentResearchRequest(
            query=excessive_query,
            orchestrator_provider="deepseek",
            lead_provider="claude",
        )


def test_endpoint_research_accepts_12k_words_query() -> None:
    large_query = "deep research transcript segment " * 3_000  # 12,000 words
    assert len(large_query) > 80_000

    with TestClient(app) as client:
        # Test standard /research endpoint
        res = client.post(
            "/research",
            headers=API_HEADERS,
            json={"query": large_query, "providers": ["gemini"]},
        )
        assert res.status_code == 202
        data = res.json()
        assert "job_id" in data

        # Test /agent-research endpoint
        res_agent = client.post(
            "/agent-research",
            headers=API_HEADERS,
            json={
                "query": large_query,
                "orchestrator_provider": "gemini",
                "lead_provider": "gemini",
            },
        )
        assert res_agent.status_code == 202
        data_agent = res_agent.json()
        assert "job_id" in data_agent


def test_prompt_builders_safely_handle_large_inputs() -> None:
    large_topic = "Large Video Transcript Content " * 3_000  # ~12,000 words, ~90k chars
    assert len(large_topic) > 80_000

    # 1. Complexity prompt truncates preview to avoid blowing up pre-phase
    comp_prompt = build_complexity_analysis_prompt(large_topic, ["gemini", "claude"])
    assert "Truncated for complexity analysis" in comp_prompt
    assert len(comp_prompt) < 15_000

    # 2. Orchestrator prompt does NOT put raw 12k words inside JSON output schema example
    orch_prompt = build_orchestrator_prompt(large_topic, allowed_providers=["gemini"])
    assert '"research_topic": "<Brief summary or title of the research topic>"' in orch_prompt
    assert "Large Video Transcript Content" in orch_prompt  # Provided in topic to decompose section

    # 3. Context summary prompt truncates long topic reference
    context_prompt = build_summarization_prompt([], large_topic)
    assert "Truncated for summary briefing" in context_prompt

    # 4. Debate and rebuttal prompts truncate topic reference
    rt_prompt = build_red_team_prompt(large_topic, "Finding details")
    assert "[truncated topic reference]" in rt_prompt

    rebuttal_prompt = build_rebuttal_prompt(large_topic, "Orig findings", "Critique", round_number=1)
    assert "[truncated topic reference]" in rebuttal_prompt

    # 5. Thesis prompt truncates topic reference
    thesis_prompt = build_thesis_extraction_prompt(large_topic, "Finding details")
    assert "[truncated topic reference]" in thesis_prompt

    # 6. Matrix report prompt truncates topic reference
    matrix_prompt = build_matrix_report_prompt(large_topic, [], tone="professional")
    assert "[truncated topic reference]" in matrix_prompt

    # 7. Lead synthesis prompt keeps reasonable bounds
    lead_prompt = build_lead_prompt(large_topic, [], tone="professional")
    assert "Truncated for synthesis" in lead_prompt
