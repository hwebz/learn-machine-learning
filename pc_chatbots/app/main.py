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


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Deep Research Local",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)



def proactor_loop_factory():
    """Event loop factory ensuring Playwright subprocess support on Windows."""
    import asyncio

    return asyncio.ProactorEventLoop()


if __name__ == "__main__":
    import sys
    import uvicorn

    loop_arg = "asyncio:ProactorEventLoop" if sys.platform == "win32" else "auto"
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False, loop=loop_arg)
