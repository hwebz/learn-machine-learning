from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.adapters.base import HealthStatus, ProviderResult, Source, StepCallback
from app.core.config import settings


class PerplexityAgentAdapter:
    """Official Perplexity Agent API adapter (no browser UI automation)."""

    name = "perplexity"
    endpoint = "/v1/agent"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        preset: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.perplexity_api_key
        self.base_url = (base_url or settings.perplexity_api_base_url).rstrip("/")
        self.preset = preset or settings.perplexity_api_preset
        self.transport = transport

    async def health(self) -> HealthStatus:
        configured = bool(self.api_key)
        detail = "Official API key configured" if configured else "Set PERPLEXITY_API_KEY to enable live research"
        return HealthStatus(logged_in=configured, selectors_ok=configured, detail=detail)

    async def ask(
        self,
        prompt: str,
        *,
        timeout_s: int,
        mode: str = "default",
        on_step: StepCallback | None = None,
    ) -> ProviderResult:
        started_at = datetime.now(timezone.utc)
        preset = "high" if mode == "deep" else self.preset
        if not self.api_key:
            raise RuntimeError("PERPLEXITY_API_KEY is not configured")

        if on_step is not None:
            await on_step("requesting", "Đang gửi yêu cầu đến Perplexity Agent API...", {"preset": preset})

        timeout = httpx.Timeout(timeout_s)
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(self.endpoint, json={"preset": preset, "input": prompt})
        if response.is_error:
            raise RuntimeError(f"Perplexity Agent API returned HTTP {response.status_code}")

        if on_step is not None:
            await on_step("extracting", "Đang phân tích phản hồi từ Perplexity API...", None)

        payload = response.json()
        answer = _answer_text(payload)
        sources = _sources(payload)
        finished_at = datetime.now(timezone.utc)
        return ProviderResult(
            provider=self.name,
            prompt=prompt,
            answer_markdown=answer,
            sources=sources,
            conversation_url=None,
            status="ok" if answer else "partial",
            started_at=started_at,
            finished_at=finished_at,
            artifact_paths=[],
            error=None if answer else "The API returned no answer text.",
        )


def _answer_text(payload: dict[str, Any]) -> str:
    direct_text = payload.get("output_text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for part in item.get("content", []):
            if isinstance(part, dict) and part.get("type") in {"output_text", "text"}:
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())
    return "\n\n".join(chunks)


def _sources(payload: dict[str, Any]) -> list[Source]:
    sources: list[Source] = []
    seen_urls: set[str] = set()
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "search_results":
            continue
        for result in item.get("results", []):
            if not isinstance(result, dict):
                continue
            url = result.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")) or url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(Source(url=url, title=result.get("title"), snippet=result.get("snippet")))
    return sources
