from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Job(SQLModel, table=True):
    id: str = Field(primary_key=True)
    query: str
    status: str = "queued"
    config_json: str
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    error: str | None = None
    report_markdown: str | None = None
    subtasks_total: int = 0
    subtasks_done: int = 0
    sources_json: str = "[]"
    claims_json: str = "[]"
    disagreements_json: str = "[]"
    provider_runs_json: str = "[]"


class JobEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(index=True)
    status: str
    subtasks_total: int = 0
    subtasks_done: int = 0
    created_at: datetime = Field(default_factory=utc_now)


class Subtask(SQLModel, table=True):
    id: str = Field(primary_key=True)
    job_id: str = Field(index=True)
    branch: str
    provider: str
    prompt: str
    status: str = "queued"
    attempt: int = 0


class ProviderRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    subtask_id: str = Field(index=True)
    provider: str
    answer_md: str = ""
    conversation_url: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    artifact_paths_json: str = "[]"
    status: str = "queued"


class Source(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    url: str
    title: str | None = None
    snippet: str | None = None


class Claim(SQLModel, table=True):
    id: str = Field(primary_key=True)
    job_id: str = Field(index=True)
    text: str
    branch: str
    source_ids_json: str = "[]"
    verdict: str = "unsupported"


class Report(SQLModel, table=True):
    id: str = Field(primary_key=True)
    job_id: str = Field(index=True)
    markdown: str
    model_used: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
