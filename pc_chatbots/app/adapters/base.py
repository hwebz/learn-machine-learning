from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable, Literal, Protocol

from pydantic import BaseModel, HttpUrl

StepCallback = Callable[[str, str, dict[str, Any] | None], Awaitable[None]]


class Source(BaseModel):
    url: HttpUrl
    title: str | None = None
    snippet: str | None = None


class ProviderResult(BaseModel):
    provider: str
    prompt: str
    answer_markdown: str
    sources: list[Source]
    conversation_url: HttpUrl | None = None
    status: Literal["ok", "partial", "timeout", "needs_user_action", "error"]
    started_at: datetime
    finished_at: datetime
    artifact_paths: list[str]
    error: str | None = None


class HealthStatus(BaseModel):
    logged_in: bool
    selectors_ok: bool
    detail: str | None = None


class ProviderAdapter(Protocol):
    name: str

    async def health(self) -> HealthStatus: ...

    async def ask(
        self,
        prompt: str,
        *,
        timeout_s: int,
        mode: str = "default",
        on_step: StepCallback | None = None,
    ) -> ProviderResult: ...

