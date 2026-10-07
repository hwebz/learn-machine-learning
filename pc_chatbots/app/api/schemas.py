from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ProviderName = Literal["perplexity", "gemini"]
JobStatus = Literal[
    "queued", "planning", "researching", "extracting", "verifying", "synthesizing",
    "completed", "partial", "failed", "needs_user_action", "cancelled",
]


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    depth: Literal["standard", "deep"] = "standard"
    providers: list[ProviderName] = Field(default_factory=lambda: ["perplexity", "gemini"], min_length=1)
    max_minutes: int = Field(default=20, ge=1, le=180)

    @field_validator("query")
    @classmethod
    def trim_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value

    @field_validator("providers")
    @classmethod
    def unique_providers(cls, value: list[ProviderName]) -> list[ProviderName]:
        if len(set(value)) != len(value):
            raise ValueError("providers must not contain duplicates")
        return value


class ResearchAccepted(BaseModel):
    job_id: str


class Progress(BaseModel):
    subtasks_total: int
    subtasks_done: int


class SourceResponse(BaseModel):
    id: str
    url: str
    title: str | None = None


class ClaimResponse(BaseModel):
    id: str
    text: str
    source_ids: list[str]
    verdict: Literal["supported", "single_source", "unsupported", "conflict"]


class DisagreementResponse(BaseModel):
    topic: str
    positions: list[str]


class ProviderRunResponse(BaseModel):
    provider: str
    status: str
    elapsed_ms: int = 0


class ResearchResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: Progress
    report_markdown: str | None
    sources: list[SourceResponse]
    claims: list[ClaimResponse]
    disagreements: list[DisagreementResponse]
    provider_runs: list[ProviderRunResponse]
    error: str | None
    created_at: datetime
    finished_at: datetime | None

