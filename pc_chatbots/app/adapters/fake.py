from __future__ import annotations

from datetime import datetime, timezone

from app.adapters.base import HealthStatus, ProviderResult, Source, StepCallback


class FakeAdapter:
    """Deterministic local adapter used to exercise the job lifecycle."""

    _KNOWN_PROVIDERS = {
        "perplexity", "gemini", "chatgpt", "claude", "copilot",
        "qwen", "kimi", "deepseek", "zhipu", "grok",
        "minimax", "meta", "pi", "mistral",
        "9router", "router",
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
        conversation_url: str | None = None,
    ) -> ProviderResult:
        self.last_conversation_url = conversation_url
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

        if "agents_dispatch" in prompt or "Research Orchestrator" in prompt:
            import json
            answer = json.dumps({
                "research_topic": prompt.split("\n")[-1].strip() or "Nghiên cứu công nghệ",
                "agents_dispatch": [
                    {
                        "id": "deepseek",
                        "name": "DeepSeek",
                        "config": {"thinking": True},
                        "sub_topic": "Kiến trúc mô hình và giải thuật chuyên sâu",
                        "question": "Phân tích các giải thuật và cấu trúc mô hình nền tảng.",
                    },
                    {
                        "id": "perplexity",
                        "name": "Perplexity",
                        "config": {"thinking": True},
                        "sub_topic": "Dữ liệu ứng dụng thực tế và nguồn kiểm chứng",
                        "question": "Tìm kiếm các bằng chứng và số liệu ứng dụng thực tế trên toàn cầu.",
                    },
                ],
            }, ensure_ascii=False)
        elif "Lead Research Synthesizer" in prompt or "TONE DIRECTIVE" in prompt:
            answer = (
                f"# Báo cáo Nghiên cứu Chuyên sâu (Lead: {self.name})\n\n"
                "## 1. Tổng quan & Luận điểm chính\n"
                "Kết quả nghiên cứu đã được tổng hợp mạch lạc từ các nhánh điều tra chuyên biệt.\n\n"
                "## 2. Phân tích chi tiết theo nguồn dẫn\n"
                "- Nhánh thuật toán đã làm rõ cơ chế suy luận và tính toán.\n"
                "- Nhánh dữ liệu thực tế đã bổ sung các trường hợp thành công nổi bật.\n\n"
                "## 3. Kết luận & Đề xuất hành động\n"
                "Hệ thống đa tác nhân đã hoàn thành việc khảo sát và đúc kết tri thức toàn diện."
            )
        else:
            answer = f"This is a placeholder response for the requested research. Provider: {self.name}."
        conv_url = conversation_url or f"https://{self.name}.example.com/c/fake-{self.name}-123"
        return ProviderResult(
            provider=self.name,
            prompt=prompt,
            answer_markdown=answer,
            sources=[Source(url=source, title=title, snippet="Placeholder source from the fake adapter.")],
            conversation_url=conv_url,
            status="ok",
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            artifact_paths=[],
        )

    deleted_conversations: list[str] = []

    async def delete_conversation(self, conversation_url: str) -> bool:
        self.deleted_conversations.append(conversation_url)
        return True
