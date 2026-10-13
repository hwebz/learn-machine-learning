from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ProviderName = Literal[
    "perplexity", "gemini", "chatgpt", "claude", "copilot",
    "qwen", "kimi", "deepseek", "zhipu", "grok",
    "minimax", "meta", "pi", "mistral",
]
JobStatus = Literal[
    "queued", "planning", "researching", "extracting", "verifying", "synthesizing",
    "completed", "partial", "failed", "needs_user_action", "cancelled",
]


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    depth: Literal["standard", "deep"] | None = Field(default=None)
    providers: list[ProviderName] = Field(default_factory=lambda: ["perplexity", "gemini"], min_length=1)
    max_minutes: int = Field(default=20, ge=1, le=180)
    provider_options: dict[str, dict[str, Any]] | None = Field(default=None)

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
    answer_markdown: str | None = None


class ResearchResponse(BaseModel):
    job_id: str
    query: str | None = None
    title: str | None = None
    depth: str | None = None
    providers: list[str] = Field(default_factory=list)
    status: JobStatus
    progress: Progress
    report_markdown: str | None
    sources: list[SourceResponse]
    claims: list[ClaimResponse]
    disagreements: list[DisagreementResponse]
    provider_runs: list[ProviderRunResponse]
    steps: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None
    provider_options: dict[str, Any] | None = Field(default=None)
    created_at: datetime
    finished_at: datetime | None


class JobUpdateRequest(BaseModel):
    title: str | None = None
    pinned: bool | None = None


class SettingsResponse(BaseModel):
    available_browsers: list[dict[str, Any]]
    browser: str
    work_mode: str
    max_concurrent_browsers: int
    headless_providers: dict[str, bool]


class SettingsUpdateRequest(BaseModel):
    browser: str | None = None
    browser_executable: str | None = None
    work_mode: str | None = None
    max_concurrent_browsers: int | None = None
    headless_providers: dict[str, bool] | None = None


class VoiceTranscriptionResponse(BaseModel):
    text: str
    provider: str | None = None
    success: bool = True
    error: str | None = None


