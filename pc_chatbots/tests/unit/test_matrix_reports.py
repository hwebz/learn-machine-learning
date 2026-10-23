from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.adapters.base import ProviderResult
from app.adapters.fake import FakeAdapter
from app.api.schemas import AgentResearchRequest
from app.core.config import settings
from app.core.models import utc_now
from app.main import app
from app.orchestrator import pipeline, agent_pipeline
from app.orchestrator.agent_pipeline import (
    build_matrix_report_prompt,
    render_matrix_to_markdown,
)

API_HEADERS = {"X-API-Key": settings.api_key}


SAMPLE_MATRIX_DATA = {
    "title": "So sánh Giải pháp Lưu trữ Đám mây",
    "executive_summary": "Đánh giá chi tiết giữa AWS S3, Cloudflare R2 và Google Cloud Storage cho ứng dụng tải cao.",
    "alternatives": [
        {
            "name": "Cloudflare R2",
            "description": "Lưu trữ đối tượng tương thích S3 không tính phí egress data.",
            "scores": {
                "cost": 5,
                "performance": 4,
                "complexity": 4,
                "maturity": 3,
                "scalability": 4,
            },
            "pros": ["Không tốn phí egress bandwidth", "Dễ tích hợp qua S3 API"],
            "cons": ["Hệ sinh thái công cụ hỗ trợ chưa phong phú bằng AWS"],
        },
        {
            "name": "AWS S3",
            "description": "Tiêu chuẩn ngành về lưu trữ đối tượng với độ bền 99.999999999%.",
            "scores": {
                "cost": 2,
                "performance": 5,
                "complexity": 3,
                "maturity": 5,
                "scalability": 5,
            },
            "pros": ["Độ ổn định tối đa", "Hệ sinh thái tính năng bảo mật toàn diện"],
            "cons": ["Chi phí egress băng thông rất đắt khi tải lớn"],
        },
    ],
    "recommendation": "Nên sử dụng Cloudflare R2 nếu lưu lượng tải ra lớn để tối ưu chi phí hạ tầng.",
    "caveats": ["Cần kiểm tra độ trễ mạng tại các khu vực chưa có edge data center."],
    "disagreements": ["Một số kỹ sư vẫn ưu tiên AWS S3 vì sự gắn kết chặt chẽ với IAM policies."],
}


def test_agent_research_report_format_schema() -> None:
    # Default is "narrative"
    req_default = AgentResearchRequest(
        query="Research Topic",
        orchestrator_provider="gemini",
        lead_provider="chatgpt",
    )
    assert req_default.report_format == "narrative"

    # Valid matrix format
    req_matrix = AgentResearchRequest(
        query="Research Topic",
        orchestrator_provider="gemini",
        lead_provider="chatgpt",
        report_format="matrix",
    )
    assert req_matrix.report_format == "matrix"

    # Valid hybrid format
    req_hybrid = AgentResearchRequest(
        query="Research Topic",
        orchestrator_provider="gemini",
        lead_provider="chatgpt",
        report_format="hybrid",
    )
    assert req_hybrid.report_format == "hybrid"

    # Invalid format raises validation error
    with pytest.raises(Exception):
        AgentResearchRequest(
            query="Research Topic",
            orchestrator_provider="gemini",
            lead_provider="chatgpt",
            report_format="invalid_format",  # type: ignore
        )


def test_build_matrix_report_prompt() -> None:
    findings = [
        {"provider": "copilot", "branch": "Chi phí", "answer_md": "R2 rẻ hơn S3 rất nhiều."},
        {"provider": "gemini", "branch": "Hiệu năng", "answer_md": "S3 có throughput cao hơn."},
    ]
    prompt = build_matrix_report_prompt(
        research_topic="AWS S3 vs Cloudflare R2",
        findings=findings,
        tone="analytical",
        context_summary="Ngữ cảnh vòng 1 đã nghiên cứu về Object Storage.",
        fact_check_claims=[
            {"claim": "R2 miễn phí egress hoàn toàn", "verdict": "supported"},
            {"claim": "S3 không hỗ trợ HTTP/3", "verdict": "conflict"},
        ],
    )

    assert "AWS S3 vs Cloudflare R2" in prompt
    assert "Chi phí" in prompt
    assert "Hiệu năng" in prompt
    assert "Previous Research Context:" in prompt
    assert "Disputed Claims:" in prompt
    assert "S3 không hỗ trợ HTTP/3" in prompt
    assert '"alternatives"' in prompt
    assert '"scores"' in prompt
    assert "Output ONLY the JSON" in prompt


def test_render_matrix_to_markdown() -> None:
    md = render_matrix_to_markdown(SAMPLE_MATRIX_DATA)

    # Title & summary
    assert "# So sánh Giải pháp Lưu trữ Đám mây" in md
    assert "Đánh giá chi tiết giữa AWS S3, Cloudflare R2" in md

    # Matrix table
    assert "## Comparative Matrix" in md
    assert "| Dimension | Cloudflare R2 | AWS S3 |" in md
    assert "💰 Cost" in md
    assert "⚡ Performance" in md
    assert "🔧 Complexity" in md
    assert "📊 Maturity" in md
    assert "📈 Scalability" in md

    # Pros and Cons
    assert "### Cloudflare R2" in md
    assert "**✅ Pros:**" in md
    assert "- Không tốn phí egress bandwidth" in md
    assert "**❌ Cons:**" in md
    assert "- Chi phí egress băng thông rất đắt khi tải lớn" in md

    # Recommendations and Caveats
    assert "## 🎯 Recommendation" in md
    assert "Nên sử dụng Cloudflare R2" in md
    assert "## ⚠️ Caveats" in md
    assert "Cần kiểm tra độ trễ mạng" in md
    assert "## 🔀 Disagreements & Open Questions" in md
    assert "Một số kỹ sư vẫn ưu tiên AWS S3" in md


def test_matrix_format_api_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "create_adapter", lambda prov: FakeAdapter(prov))
    monkeypatch.setattr(agent_pipeline, "create_adapter", lambda prov: FakeAdapter(prov))

    with TestClient(app) as client:
        # 1. Create with report_format="matrix"
        res = client.post(
            "/agent-research",
            headers=API_HEADERS,
            json={
                "query": "So sánh Postgres và MySQL cho microservices",
                "orchestrator_provider": "gemini",
                "lead_provider": "chatgpt",
                "report_format": "matrix",
            },
        )
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        # 2. Verify /research/{job_id} includes report_format="matrix"
        deadline = time.monotonic() + 10
        data = None
        while time.monotonic() < deadline:
            job_res = client.get(f"/research/{job_id}", headers=API_HEADERS)
            assert job_res.status_code == 200
            data = job_res.json()
            if data["status"] in ("completed", "failed"):
                break
            time.sleep(0.05)
        assert data is not None
        assert data["report_format"] == "matrix"
        assert "report_matrix" in data

        # 3. Create with report_format="hybrid"
        res_h = client.post(
            "/agent-research",
            headers=API_HEADERS,
            json={
                "query": "So sánh REST và GraphQL",
                "orchestrator_provider": "gemini",
                "lead_provider": "chatgpt",
                "report_format": "hybrid",
            },
        )
        assert res_h.status_code == 202
        job_h_id = res_h.json()["job_id"]
        deadline = time.monotonic() + 10
        data_h = None
        while time.monotonic() < deadline:
            job_h_res = client.get(f"/research/{job_h_id}", headers=API_HEADERS)
            assert job_h_res.status_code == 200
            data_h = job_h_res.json()
            if data_h["status"] in ("completed", "failed"):
                break
            time.sleep(0.05)
        assert data_h is not None
        assert data_h["report_format"] == "hybrid"


def test_matrix_report_pipeline_synthesis(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test that run_agent_pipeline with report_format="matrix" produces the matrix markdown and report_matrix_json
    matrix_response_text = json.dumps(SAMPLE_MATRIX_DATA)

    class MatrixFakeAdapter(FakeAdapter):
        async def ask(
            self,
            prompt: str,
            *,
            timeout_s: int = 60,
            mode: str = "default",
            on_step: Any = None,
            conversation_url: str | None = None,
        ) -> ProviderResult:
            if "STRUCTURED COMPARATIVE REPORT" in prompt:
                now = datetime.now(timezone.utc)
                return ProviderResult(
                    provider="chatgpt",
                    prompt=prompt,
                    answer_markdown=f"```json\n{matrix_response_text}\n```",
                    sources=[],
                    conversation_url="https://chatgpt.com/c/test-lead-matrix",
                    status="ok",
                    started_at=now,
                    finished_at=now,
                    artifact_paths=[],
                )
            return await super().ask(prompt, timeout_s=timeout_s, mode=mode, on_step=on_step, conversation_url=conversation_url)

    monkeypatch.setattr(pipeline, "create_adapter", lambda prov: FakeAdapter(prov) if prov != "chatgpt" else MatrixFakeAdapter("chatgpt"))
    monkeypatch.setattr(agent_pipeline, "create_adapter", lambda prov: FakeAdapter(prov) if prov != "chatgpt" else MatrixFakeAdapter("chatgpt"))

    with TestClient(app) as client:
        res = client.post(
            "/agent-research",
            headers=API_HEADERS,
            json={
                "query": "So sánh S3 và R2",
                "orchestrator_provider": "gemini",
                "lead_provider": "chatgpt",
                "report_format": "matrix",
                "delegated_providers": ["gemini"],
            },
        )
        assert res.status_code == 202
        job_id = res.json()["job_id"]

        # Poll until done
        deadline = time.monotonic() + 10
        r = None
        while time.monotonic() < deadline:
            resp = client.get(f"/research/{job_id}", headers=API_HEADERS)
            assert resp.status_code == 200
            r = resp.json()
            if r["status"] in ("completed", "partial", "failed"):
                break
            time.sleep(0.05)

        assert r is not None
        assert r["status"] == "completed"
        assert r["report_format"] == "matrix"
        assert r["report_matrix"] is not None
        assert r["report_matrix"]["title"] == "So sánh Giải pháp Lưu trữ Đám mây"
        assert "## Comparative Matrix" in (r["report_markdown"] or "")
        assert "| Dimension | Cloudflare R2 | AWS S3 |" in (r["report_markdown"] or "")

