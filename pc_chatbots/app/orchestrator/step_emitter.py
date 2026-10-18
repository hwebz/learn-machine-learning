"""Reusable, thread-safe and cancellation-aware Step Emitter for pipeline events."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable

import structlog

from app.core.db import SessionLocal
from app.core.models import Job, JobEvent

TERMINAL_STATUSES = {"completed", "partial", "failed", "needs_user_action", "cancelled"}

logger = structlog.get_logger(__name__)

# Registry for SSE event notification
_job_subscribers: dict[str, set[asyncio.Event]] = {}


def subscribe_job(job_id: str) -> asyncio.Event:
    """Subscribe to real-time event notifications for a specific job."""
    ev = asyncio.Event()
    _job_subscribers.setdefault(job_id, set()).add(ev)
    return ev


def unsubscribe_job(job_id: str, ev: asyncio.Event) -> None:
    """Unsubscribe and clean up notification event when SSE disconnects."""
    subs = _job_subscribers.get(job_id)
    if subs:
        subs.discard(ev)
        if not subs:
            _job_subscribers.pop(job_id, None)


def notify_job_event(job_id: str) -> None:
    """Notify all waiting SSE subscribers that a new event was emitted for this job."""
    subs = _job_subscribers.get(job_id)
    if subs:
        for ev in list(subs):
            ev.set()


class StepEmitter:
    """Standardized step emitter for pipeline subtasks and agent roles."""

    def __init__(
        self,
        job_id: str,
        provider: str = "",
        status: str = "researching",
        role: str = "",
        cancel_event: asyncio.Event | None = None,
        subtasks_total: int | None = None,
        get_subtasks_done: Callable[[], int] | None = None,
        start_time: float | None = None,
        extra_payload: dict[str, Any] | None = None,
        on_citations: Callable[[list[dict[str, Any]]], Any] | None = None,
    ) -> None:
        self.job_id = job_id
        self.provider = provider
        self.status = status
        self.role = role
        self.cancel_event = cancel_event
        self.subtasks_total = subtasks_total
        self.get_subtasks_done = get_subtasks_done
        self.start_time = start_time
        self.extra_payload = extra_payload
        self.on_citations = on_citations

    async def emit(
        self,
        step_name: str,
        step_message: str,
        step_data: dict[str, Any] | None = None,
        event_type: str = "step",
    ) -> None:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise asyncio.CancelledError("Job cancelled by user")

        if step_name == "thinking_progress":
            event_type = "thinking"

        # Prepare payload
        payload: dict[str, Any] = dict(step_data or {})
        if self.role:
            payload.setdefault("role", self.role)
            payload.setdefault("provider_role_key", self.role)
        if self.extra_payload:
            payload.update(self.extra_payload)
        if self.start_time is not None:
            payload["elapsed_s"] = round(time.monotonic() - self.start_time, 1)

        # Handle live citations hook if provided
        if self.on_citations and step_name == "thinking_progress" and payload and payload.get("citations"):
            try:
                res = self.on_citations(payload["citations"])
                if asyncio.iscoroutine(res):
                    await res
            except Exception as c_err:
                logger.debug("live_citation_hook_error", error=str(c_err))

        async with SessionLocal() as s:
            db_j = await s.get(Job, self.job_id)
            if db_j is None or db_j.status == "cancelled":
                raise asyncio.CancelledError("Job cancelled by user")
            if db_j.status in TERMINAL_STATUSES:
                return

            subtasks_total = self.subtasks_total if self.subtasks_total is not None else db_j.subtasks_total
            subtasks_done = self.get_subtasks_done() if self.get_subtasks_done is not None else db_j.subtasks_done

            s.add(JobEvent(
                job_id=self.job_id,
                status=self.status or db_j.status,
                event_type=event_type,
                provider=self.provider,
                step=step_name,
                message=step_message,
                subtasks_total=subtasks_total,
                subtasks_done=subtasks_done,
                data_json=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
            ))
            await s.commit()

        notify_job_event(self.job_id)

    async def __call__(
        self,
        step_name: str,
        step_message: str,
        step_data: dict[str, Any] | None = None,
        event_type: str = "step",
    ) -> None:
        await self.emit(step_name, step_message, step_data=step_data, event_type=event_type)
