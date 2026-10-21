from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ProviderName = Literal[
    "perplexity", "gemini", "chatgpt", "claude", "copilot",
    "qwen", "kimi", "deepseek", "zhipu", "grok",
    "minimax", "meta", "pi", "mistral",
    "9router", "router",
]
JobStatus = Literal[
    "queued", "summarizing", "orchestrating", "planning", "researching", "fact_checking", "extracting", "verifying", "synthesizing", "leading",
    "completed", "partial", "failed", "needs_user_action", "cancelled",
]

TonePreset = Literal[
    "academic", "professional", "analytical", "explanatory",
    "journalistic", "creative", "executive", "conversational",
]


class AgentDispatchItem(BaseModel):
    id: str
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    sub_topic: str
    question: str
    role_group: str = Field(default="researcher")


class OrchestratorOutput(BaseModel):
    research_topic: str
    agents_dispatch: list[AgentDispatchItem] = Field(min_length=1, max_length=10)


class AgentResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    orchestrator_provider: ProviderName
    orchestrator_config: dict[str, Any] | None = Field(default_factory=dict)
    lead_provider: ProviderName
    lead_config: dict[str, Any] | None = Field(default_factory=dict)
    tone: str = Field(default="professional")
    max_minutes: int = Field(default=30, ge=1, le=180)
    delegated_providers: list[ProviderName] | None = Field(default=None)
    provider_configs: dict[str, Any] | None = Field(default_factory=dict)
    provider_capabilities: dict[str, Any] | None = Field(default_factory=dict)
    summarization_provider: ProviderName | None = Field(default="9router")
    summarization_config: dict[str, Any] | None = Field(default_factory=lambda: {"model_id": "Daily"})
    enable_fact_check: bool = Field(default=False)
    fact_check_provider: ProviderName | None = Field(default="perplexity")
    fact_check_config: dict[str, Any] | None = Field(default_factory=dict)
    conversation_urls: dict[str, str] | None = Field(default=None)
    parent_job_id: str | None = Field(default=None)

    @field_validator("query")
    @classmethod
    def trim_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    depth: Literal["standard", "deep"] | None = Field(default=None)
    providers: list[ProviderName] = Field(default_factory=lambda: ["perplexity", "gemini"], min_length=1)
    max_minutes: int = Field(default=20, ge=1, le=180)
    provider_options: dict[str, dict[str, Any]] | None = Field(default=None)
    conversation_urls: dict[str, str] | None = Field(default=None)
    parent_job_id: str | None = Field(default=None)

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
    id: str = ""
    text: str = ""
    source_ids: list[str] = Field(default_factory=list)
    verdict: Literal["supported", "single_source", "unsupported", "conflict", "disputed", "verified"] = "unsupported"
    confidence: float | None = None
    reasoning: str | None = None
    branch: str | None = None
    claim: str | None = None


class DisagreementResponse(BaseModel):
    topic: str
    positions: list[str]


class ProviderRunResponse(BaseModel):
    provider: str
    status: str
    elapsed_ms: int = 0
    elapsed_s: float | None = None
    role: str | None = None
    branch: str | None = None
    branch_index: int | None = None
    subtask_id: str | None = None
    provider_role_key: str | None = None
    conversation_url: str | None = None
    answer_markdown: str | None = None
    answer_md: str | None = None


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
    job_type: str = "research"
    orchestrator_provider: str | None = None
    lead_provider: str | None = None
    tone: str | None = None
    orchestrator_dispatch: list[dict[str, Any]] | None = None
    delegated_providers: list[str] | None = None
    orchestrator_config: dict[str, Any] | None = None
    lead_config: dict[str, Any] | None = None
    orchestrator_conversation_url: str | None = None
    lead_conversation_url: str | None = None
    provider_conversations: dict[str, str] | None = None
    summarization_provider: str | None = None
    summarization_config: dict[str, Any] | None = None
    context_summary: str | None = None
    enable_fact_check: bool = False
    fact_check_provider: str | None = None
    fact_check_config: dict[str, Any] | None = None
    fact_check_results: list[dict[str, Any]] | None = None
    parent_job_id: str | None = None
    conversation_id: str | None = None
    created_at: datetime
    finished_at: datetime | None


class ProviderConversationItem(BaseModel):
    provider: str
    role: str
    url: str
    title: str | None = None
    branch: str | None = None
    branch_index: int | None = None


class JobConversationsResponse(BaseModel):
    job_id: str
    conversations: list[ProviderConversationItem]


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


