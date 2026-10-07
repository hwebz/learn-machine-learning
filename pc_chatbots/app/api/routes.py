from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

from openai import AsyncOpenAI
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlmodel import select

from app.api.auth import require_api_key
from app.api.schemas import ResearchAccepted, ResearchRequest, ResearchResponse
from app.adapters.perplexity_api import PerplexityAgentAdapter
from app.adapters.gemini_ui import GeminiUIAdapter
from app.adapters.perplexity_ui import PerplexityUIAdapter
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

    return {
        "status": "ok",
        "router_reachable": router_reachable,
        "adapter_mode": settings.research_adapter_mode,
        "adapters": {
            "perplexity": {
                "api_key_configured": perplexity_health.logged_in,
                "api_detail": perplexity_health.detail,
                "ui": await _safe_ui_health(PerplexityUIAdapter),
            },
            "gemini": {
                "ui": await _safe_ui_health(GeminiUIAdapter),
                "detail": "Official API adapter not implemented yet",
            },
        },
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
        session.add(JobEvent(job_id=job_id, status="queued", subtasks_total=job.subtasks_total, subtasks_done=0))
        await session.commit()
    await request.app.state.job_queue.put(job_id)
    logger.info("research_job_queued", job_id=job_id, providers=payload.providers)
    return ResearchAccepted(job_id=job_id)


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
                data = {
                    "job_id": job_id,
                    "status": event.status,
                    "progress": {"subtasks_total": event.subtasks_total, "subtasks_done": event.subtasks_done},
                }
                yield f"id: {last_event_id}\nevent: progress\ndata: {json.dumps(data)}\n\n"
            if job.status in {"completed", "partial", "failed", "needs_user_action", "cancelled"} and not events:
                yield "event: done\ndata: {}\n\n"
                return
            await asyncio.sleep(0.5)

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
