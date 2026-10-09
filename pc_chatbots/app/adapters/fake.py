from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import HealthStatus, ProviderResult, Source


class FakeAdapter:
    """Deterministic local adapter used to exercise the job lifecycle."""

    _KNOWN_PROVIDERS = {
        "perplexity", "gemini", "chatgpt", "claude", "copilot",
        "qwen", "kimi", "deepseek", "zhipu", "grok",
        "minimax", "meta", "pi", "mistral",
    }

    def __init__(self, name: str) -> None:
        if name not in self._KNOWN_PROVIDERS:
            raise ValueError(f"Unsupported fake provider: {name}")
        self.name = name

    async def health(self) -> HealthStatus:
        return HealthStatus(logged_in=False, selectors_ok=True, detail="Fake adapter is ready")

    async def ask(self, prompt: str, *, timeout_s: int, mode: str = "default") -> ProviderResult:
        started = datetime.now(timezone.utc)
        source = "https://example.com/research-method"
        title = "Example research method"
        answer = f"This is a placeholder response for the requested research. Provider: {self.name}."
        return ProviderResult(
            provider=self.name,
            prompt=prompt,
            answer_markdown=answer,
            sources=[Source(url=source, title=title, snippet="Placeholder source from the fake adapter.")],
            conversation_url=None,
            status="ok",
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            artifact_paths=[],
        )
