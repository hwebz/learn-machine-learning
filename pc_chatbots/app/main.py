from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from app.api.routes import router
from app.browser.session import close_browser_session
from app.core.db import close_db, init_db
from app.core.logging import configure_logging
from app.core.queue import JobQueue
from app.orchestrator.pipeline import worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await init_db()
    app.state.job_queue = JobQueue()
    app.state.worker_task = asyncio.create_task(worker_loop(app.state.job_queue), name="research-worker")
    try:
        yield
    finally:
        app.state.worker_task.cancel()
        try:
            await app.state.worker_task
        except asyncio.CancelledError:
            pass
        await close_browser_session()
        await close_db()


app = FastAPI(
    title="Deep Research Local",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
