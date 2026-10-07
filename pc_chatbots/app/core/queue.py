from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class JobQueue:
    """Single-consumer in-process queue with per-job cancellation signals."""

    def __init__(self) -> None:
        self.items: asyncio.Queue[str] = asyncio.Queue()
        self.cancel_events: dict[str, asyncio.Event] = {}

    async def put(self, job_id: str) -> None:
        self.cancel_events[job_id] = asyncio.Event()
        await self.items.put(job_id)

    def cancel(self, job_id: str) -> asyncio.Event | None:
        event = self.cancel_events.get(job_id)
        if event is not None:
            event.set()
        return event

    async def get(self) -> str:
        return await self.items.get()

    def done(self, job_id: str) -> None:
        self.cancel_events.pop(job_id, None)
        self.items.task_done()

    async def events(self) -> AsyncIterator[str]:
        while True:
            yield await self.get()

