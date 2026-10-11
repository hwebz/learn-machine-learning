from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import HealthStatus, ProviderResult, Source, StepCallback


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

    async def ask(
        self,
        prompt: str,
        *,
        timeout_s: int,
        mode: str = "default",
        on_step: StepCallback | None = None,
    ) -> ProviderResult:
        if on_step is not None:
            await on_step(
                "generating",
                f"{self.name} đang sinh câu trả lời...",
                {"provider": self.name},
            )
            await on_step(
                "thinking_progress",
                f"{self.name} đang suy luận: Phân tích chuyên sâu câu hỏi '{prompt[:50]}...'",
                {
                    "provider": self.name,
                    "state": "thinking / generating",
                    "generating": True,
                    "is_thinking": True,
                    "thinking_text": f"1. Phân tích câu hỏi '{prompt}'.\n2. Tra cứu dữ liệu và đối chiếu các nguồn thông tin thực tế.\n3. Tổng hợp luận cứ và trích dẫn bằng chứng.",
                    "citations": [
                        {"url": "https://en.wikipedia.org/wiki/Machine_learning", "title": "Machine Learning Overview - Wikipedia"},
                        {"url": "https://arxiv.org/abs/2303.08774", "title": "GPT-4 Technical Report - arXiv"},
                    ],
                    "citations_count": 2,
                    "elapsed_s": 1.0,
                },
            )
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
