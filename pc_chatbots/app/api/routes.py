from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from openai import AsyncOpenAI
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlmodel import select

from app.api.auth import require_api_key
from app.api.schemas import ResearchAccepted, ResearchRequest, ResearchResponse
from app.adapters.perplexity_api import PerplexityAgentAdapter
from app.orchestrator.pipeline import _UI_ADAPTERS
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.models import Job, JobEvent
from app.core.models import utc_now

logger = structlog.get_logger(__name__)
router = APIRouter()
protected = [Depends(require_api_key)]


def _job_response(job: Job) -> ResearchResponse:
    runs = json.loads(job.provider_runs_json)
    return ResearchResponse(
        job_id=job.id,
        status=job.status,
        progress={"subtasks_total": job.subtasks_total, "subtasks_done": job.subtasks_done},
        report_markdown=job.report_markdown,
        sources=json.loads(job.sources_json),
        claims=json.loads(job.claims_json),
        disagreements=json.loads(job.disagreements_json),
        provider_runs=runs,
        error=job.error,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


async def _load_job(job_id: str) -> Job:
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Research job not found")
        return job


async def _safe_ui_health(adapter_cls: type) -> dict[str, object]:
    """Run a UI adapter's static health() and never let it crash /health."""
    try:
        h = await adapter_cls().health()
        return {"logged_in": h.logged_in, "selectors_ok": h.selectors_ok, "detail": h.detail}
    except Exception as exc:  # noqa: BLE001 — selectors.yaml missing/broken must not crash /health
        return {"logged_in": False, "selectors_ok": False, "detail": f"health error: {type(exc).__name__}"}


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    client = AsyncOpenAI(base_url=settings.router_base_url, api_key=settings.router_api_key, timeout=2.0)
    try:
        await client.models.list()
        router_reachable = True
    except Exception:
        router_reachable = False
    finally:
        await client.close()

    perplexity_health = await PerplexityAgentAdapter().health()

    # Build per-provider health dict dynamically from the UI adapter registry.
    adapters_health: dict[str, dict[str, object]] = {}
    for name, adapter_cls in sorted(_UI_ADAPTERS.items()):
        entry: dict[str, object] = {"ui": await _safe_ui_health(adapter_cls)}
        # Attach official API health for providers that have one.
        if name == "perplexity":
            entry["api_key_configured"] = perplexity_health.logged_in
            entry["api_detail"] = perplexity_health.detail
        entry.setdefault("detail", "Official API adapter not implemented yet")
        adapters_health[name] = entry

    return {
        "status": "ok",
        "router_reachable": router_reachable,
        "adapter_mode": settings.research_adapter_mode,
        "adapters": adapters_health,
        "worker_running": request.app.state.worker_task is not None and not request.app.state.worker_task.done(),
    }


@router.post("/research", response_model=ResearchAccepted, status_code=status.HTTP_202_ACCEPTED, dependencies=protected)
async def create_research(payload: ResearchRequest, request: Request) -> ResearchAccepted:
    job_id = str(uuid4())
    job = Job(
        id=job_id,
        query=payload.query,
        config_json=payload.model_dump_json(),
        status="queued",
        subtasks_total=len(payload.providers),
    )
    async with SessionLocal() as session:
        session.add(job)
        session.add(JobEvent(
            job_id=job_id,
            status="queued",
            event_type="progress",
            message="Job nghiên cứu đã được đưa vào hàng đợi xử lý.",
            subtasks_total=job.subtasks_total,
            subtasks_done=0,
        ))
        await session.commit()
    await request.app.state.job_queue.put(job_id)
    logger.info("research_job_queued", job_id=job_id, providers=payload.providers)
    return ResearchAccepted(job_id=job_id)


@router.get("/research", response_model=list[dict[str, Any]], dependencies=protected)
async def list_research(limit: int = 50) -> list[dict[str, Any]]:
    async with SessionLocal() as session:
        statement = select(Job).order_by(Job.created_at.desc()).limit(limit)
        jobs = (await session.exec(statement)).all()
        result = []
        for j in jobs:
            try:
                config = json.loads(j.config_json) if j.config_json else {}
            except Exception:
                config = {}
            try:
                sources = json.loads(j.sources_json) if j.sources_json else []
            except Exception:
                sources = []
            try:
                claims = json.loads(j.claims_json) if j.claims_json else []
            except Exception:
                claims = []
            try:
                runs = json.loads(j.provider_runs_json) if j.provider_runs_json else {}
            except Exception:
                runs = {}

            result.append({
                "job_id": j.id,
                "query": j.query,
                "status": j.status,
                "subtasks_total": j.subtasks_total,
                "subtasks_done": j.subtasks_done,
                "report_markdown": j.report_markdown,
                "sources": sources,
                "claims": claims,
                "provider_runs": runs,
                "error": j.error,
                "depth": config.get("depth", "deep"),
                "providers": config.get("providers", []),
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            })
        return result


@router.get("/research/{job_id}", response_model=ResearchResponse, dependencies=protected)
async def get_research(job_id: str) -> ResearchResponse:
    return _job_response(await _load_job(job_id))


@router.get("/research/{job_id}/events", dependencies=protected)
async def research_events(job_id: str) -> StreamingResponse:
    await _load_job(job_id)

    async def stream() -> AsyncIterator[str]:
        last_event_id = 0
        while True:
            async with SessionLocal() as session:
                events = (await session.exec(
                    select(JobEvent).where(JobEvent.job_id == job_id, JobEvent.id > last_event_id).order_by(JobEvent.id)
                )).all()
                job = await session.get(Job, job_id)
            if job is None:
                return
            for event in events:
                last_event_id = event.id or last_event_id
                event_type = getattr(event, "event_type", None) or "progress"
                data: dict[str, Any] = {
                    "job_id": job_id,
                    "status": event.status,
                    "event_type": event_type,
                    "progress": {"subtasks_total": event.subtasks_total, "subtasks_done": event.subtasks_done},
                }
                if getattr(event, "provider", None):
                    data["provider"] = event.provider
                if getattr(event, "step", None):
                    data["step"] = event.step
                if getattr(event, "message", None):
                    data["message"] = event.message
                if getattr(event, "data_json", None):
                    try:
                        data["data"] = json.loads(event.data_json)
                    except Exception:
                        data["data"] = event.data_json

                yield f"id: {last_event_id}\nevent: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

            if job.status in {"completed", "partial", "failed", "needs_user_action", "cancelled"} and not events:
                yield "event: done\ndata: {}\n\n"
                return
            await asyncio.sleep(0.25)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/research/{job_id}/cancel", dependencies=protected)
async def cancel_research(job_id: str, request: Request) -> Response:
    queue = request.app.state.job_queue
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Research job not found")
        if job.status in {"completed", "partial", "failed", "needs_user_action", "cancelled"}:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        event = queue.cancel(job_id)
        if job.status == "queued":
            job.status = "cancelled"
            job.finished_at = utc_now()
            job.updated_at = utc_now()
        elif event is None:
            job.status = "cancelled"
            job.finished_at = utc_now()
            job.updated_at = utc_now()
        if job.status == "cancelled":
            session.add(JobEvent(job_id=job_id, status="cancelled", subtasks_total=job.subtasks_total, subtasks_done=job.subtasks_done))
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
