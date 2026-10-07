from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.perplexity_api import PerplexityAgentAdapter


@pytest.mark.asyncio
async def test_agent_adapter_maps_answer_and_search_results() -> None:
    request_details: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        request_details["url"] = str(request.url)
        request_details["authorization"] = request.headers.get("Authorization")
        request_details["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "search_results",
                        "results": [
                            {"title": "Example source", "url": "https://example.org/source", "snippet": "Evidence."}
                        ],
                    },
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "A grounded answer."}],
                    },
                ]
            },
        )

    adapter = PerplexityAgentAdapter(
        "test-key",
        base_url="https://api.example.test",
        preset="fast",
        transport=httpx.MockTransport(handler),
    )
    result = await adapter.ask("A research question", timeout_s=10)

    assert request_details["url"] == "https://api.example.test/v1/agent"
    assert request_details["authorization"] == "Bearer test-key"
    assert request_details["body"] == {"preset": "fast", "input": "A research question"}
    assert result.answer_markdown == "A grounded answer."
    assert len(result.sources) == 1
    assert str(result.sources[0].url) == "https://example.org/source"


@pytest.mark.asyncio
async def test_deep_mode_uses_high_research_preset() -> None:
    seen_body: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_body.update(json.loads(request.content))
        return httpx.Response(200, json={"output_text": "Deep answer."})

    adapter = PerplexityAgentAdapter(
        "test-key",
        transport=httpx.MockTransport(handler),
    )
    await adapter.ask("A deep question", timeout_s=10, mode="deep")

    assert seen_body["preset"] == "high"


@pytest.mark.asyncio
async def test_adapter_requires_official_api_key() -> None:
    adapter = PerplexityAgentAdapter(api_key="")

    with pytest.raises(RuntimeError, match="PERPLEXITY_API_KEY"):
        await adapter.ask("A question", timeout_s=1)

