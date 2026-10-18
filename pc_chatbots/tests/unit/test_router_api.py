from __future__ import annotations

import json
from typing import Any
import httpx
import pytest

from app.adapters.capabilities.router import RouterCapabilitiesStrategy
from app.adapters.router_api import RouterAPIAdapter, _extract_answer_and_reasoning, _extract_sources
from app.orchestrator.pipeline import create_adapter


@pytest.mark.asyncio
async def test_health_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        assert request.headers.get("Authorization") == "Bearer test-key"
        return httpx.Response(200, json={"data": [{"id": "Smartest"}, {"id": "Daily"}]})

    adapter = RouterAPIAdapter(
        "test-key",
        base_url="http://localhost:20128/v1",
        transport=httpx.MockTransport(handler),
    )
    h = await adapter.health()
    assert h.logged_in is True
    assert h.selectors_ok is True
    assert "2 models available" in h.detail


@pytest.mark.asyncio
async def test_health_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    adapter = RouterAPIAdapter(
        "test-key",
        base_url="http://localhost:20128/v1",
        transport=httpx.MockTransport(handler),
    )
    h = await adapter.health()
    assert h.logged_in is False
    assert h.selectors_ok is False
    assert "HTTP 502" in h.detail


@pytest.mark.asyncio
async def test_health_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    adapter = RouterAPIAdapter(
        "test-key",
        base_url="http://localhost:20128/v1",
        transport=httpx.MockTransport(handler),
    )
    h = await adapter.health()
    assert h.logged_in is False
    assert h.selectors_ok is False
    assert "ConnectError" in h.detail


@pytest.mark.asyncio
async def test_ask_format_standard_content() -> None:
    seen_request: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_request["url"] = str(request.url)
        seen_request["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "This is standard text content.",
                        },
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    adapter = RouterAPIAdapter(
        "sk-test",
        base_url="http://localhost:20128/v1",
        default_model="Smartest",
        transport=httpx.MockTransport(handler),
    )
    res = await adapter.ask("What is AI?", timeout_s=10)

    assert seen_request["url"] == "http://localhost:20128/v1/chat/completions"
    assert seen_request["body"]["model"] == "Smartest"
    assert seen_request["body"]["messages"][0]["content"] == "What is AI?"
    assert res.status == "ok"
    assert res.answer_markdown == "This is standard text content."
    assert res.provider == "9router"


@pytest.mark.asyncio
async def test_ask_format_reasoning_content_field() -> None:
    steps_received: list[dict[str, Any]] = []

    async def on_step(step: str, message: str, data: Any) -> None:
        steps_received.append({"step": step, "message": message, "data": data})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "The derivative is 2x.",
                            "reasoning_content": "Using the power rule on x^2, we get 2*x^(2-1) = 2x.",
                        }
                    }
                ]
            },
        )

    adapter = RouterAPIAdapter(
        "sk-test",
        transport=httpx.MockTransport(handler),
    )
    res = await adapter.ask("Differentiate x^2", timeout_s=10, on_step=on_step)

    assert res.answer_markdown == "The derivative is 2x."
    # Verify thinking progress step was dispatched
    thinking_step = next((s for s in steps_received if s["step"] == "thinking_progress"), None)
    assert thinking_step is not None
    assert thinking_step["data"]["is_thinking"] is True
    assert "power rule" in thinking_step["data"]["thinking_text"]


@pytest.mark.asyncio
async def test_ask_format_thought_field() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Result with thought.",
                    "thought": "Thinking about the edge cases...",
                }
            }
        ]
    }
    answer, reasoning = _extract_answer_and_reasoning(payload)
    assert answer == "Result with thought."
    assert reasoning == "Thinking about the edge cases..."


@pytest.mark.asyncio
async def test_ask_format_embedded_think_tags() -> None:
    steps_received: list[dict[str, Any]] = []

    async def on_step(step: str, message: str, data: Any) -> None:
        steps_received.append({"step": step, "message": message, "data": data})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "<think>\n1. Identify question type\n2. Solve\n</think>\n42 is the answer.",
                        }
                    }
                ]
            },
        )

    adapter = RouterAPIAdapter(
        "sk-test",
        transport=httpx.MockTransport(handler),
    )
    res = await adapter.ask("Answer to life?", timeout_s=10, on_step=on_step)

    assert res.answer_markdown == "42 is the answer."
    assert "<think>" not in res.answer_markdown
    thinking_step = next(s for s in steps_received if s["step"] == "thinking_progress")
    assert "1. Identify question type" in thinking_step["data"]["thinking_text"]


@pytest.mark.asyncio
async def test_ask_format_multimodal_content_parts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": [
                                {"type": "text", "text": "Section 1: Overview."},
                                {"type": "text", "text": "Section 2: Architecture details."},
                            ],
                        }
                    }
                ]
            },
        )

    adapter = RouterAPIAdapter("sk-test", transport=httpx.MockTransport(handler))
    res = await adapter.ask("Explain architecture", timeout_s=10)
    assert res.answer_markdown == "Section 1: Overview.\n\nSection 2: Architecture details."


@pytest.mark.asyncio
async def test_ask_format_citations_and_annotations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Deep research shows positive growth.\n\n[1]: https://research.org/report '2026 Report'\nCheck [Live Metrics](https://metrics.io/live) for details.",
                            "citations": [
                                {"url": "https://source1.example/paper", "title": "Paper 1", "snippet": "Evidence"}
                            ],
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url_citation": {"url": "https://source2.example/news", "title": "News 2"},
                                }
                            ],
                        }
                    }
                ],
                "search_results": [
                    {"url": "https://source3.example/web", "title": "Web 3"}
                ],
            },
        )

    adapter = RouterAPIAdapter("sk-test", transport=httpx.MockTransport(handler))
    res = await adapter.ask("Market trends", timeout_s=10)

    urls = [str(s.url) for s in res.sources]
    assert "https://source1.example/paper" in urls
    assert "https://source2.example/news" in urls
    assert "https://source3.example/web" in urls
    assert "https://research.org/report" in urls
    assert "https://metrics.io/live" in urls


@pytest.mark.asyncio
async def test_ask_format_tool_calls_fallback() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "fetch_stock_quote",
                                "arguments": '{"ticker": "NVDA"}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    answer, reasoning = _extract_answer_and_reasoning(payload)
    assert "Tool Call (`fetch_stock_quote`)" in answer
    assert '{"ticker": "NVDA"}' in answer


@pytest.mark.asyncio
async def test_ask_format_legacy_completion() -> None:
    payload = {
        "choices": [
            {
                "text": "Legacy davinci completion output.",
                "index": 0,
                "finish_reason": "stop",
            }
        ]
    }
    answer, reasoning = _extract_answer_and_reasoning(payload)
    assert answer == "Legacy davinci completion output."


@pytest.mark.asyncio
async def test_ask_format_root_output_fields() -> None:
    payload1 = {"output_text": "Root level output text"}
    ans1, _ = _extract_answer_and_reasoning(payload1)
    assert ans1 == "Root level output text"

    payload2 = {"response": "Direct response string"}
    ans2, _ = _extract_answer_and_reasoning(payload2)
    assert ans2 == "Direct response string"


@pytest.mark.asyncio
async def test_ask_format_refusal() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "refusal": "Request violates safety policies.",
                }
            }
        ]
    }
    answer, reasoning = _extract_answer_and_reasoning(payload)
    assert answer == "Refusal: Request violates safety policies."


@pytest.mark.asyncio
async def test_ask_format_error_payload() -> None:
    payload = {"error": {"message": "Rate limit exceeded, please retry."}}
    answer, reasoning = _extract_answer_and_reasoning(payload)
    assert answer == "Error: Rate limit exceeded, please retry."


@pytest.mark.asyncio
async def test_ask_http_error_raises_runtime_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error in Router")

    adapter = RouterAPIAdapter("sk-test", transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError, match="9Router API returned HTTP 500"):
        await adapter.ask("Hello", timeout_s=5)


@pytest.mark.asyncio
async def test_ask_model_override() -> None:
    seen_model: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen_model.append(body.get("model"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    adapter = RouterAPIAdapter("sk-test", default_model="Daily", transport=httpx.MockTransport(handler))
    await adapter.ask("Hello", timeout_s=5, model="nvidia/nemotron-3-ultra-550b-a55b")
    assert seen_model == ["nvidia/nemotron-3-ultra-550b-a55b"]


def test_router_capabilities_strategy() -> None:
    strat = RouterCapabilitiesStrategy("9router")
    assert strat.provider_name == "9router"
    assert strat.is_api_only is True
    caps = strat.get_default_capabilities()
    assert caps.provider == "9router"
    assert len(caps.available_models) >= 3
    model_ids = [m.id for m in caps.available_models]
    assert "Smartest" in model_ids
    assert "Daily" in model_ids
    assert caps.deep_thinking is True


@pytest.mark.asyncio
async def test_router_capabilities_inspect_api_success(monkeypatch: pytest.MonkeyPatch) -> None:
    strat = RouterCapabilitiesStrategy("9router")

    sample_api_response = {
        "data": [
            {
                "id": "Smartest",
                "object": "model",
                "owned_by": "combo",
                "capabilities": {
                    "vision": True,
                    "pdf": False,
                    "search": True,
                    "tools": True,
                    "reasoning": True,
                    "thinkingFormat": "openai",
                    "thinkingCanDisable": True,
                    "contextWindow": 1050000,
                    "maxOutput": 128000,
                },
                "context_length": 1050000,
            },
            {
                "id": "cx/gpt-reserve",
                "object": "model",
                "owned_by": "cx",
                "capabilities": {
                    "vision": False,
                    "reasoning": False,
                    "thinkingFormat": None,
                    "contextWindow": 200000,
                },
                "context_length": 200000,
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json=sample_api_response)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: mock_client)

    caps = await strat.inspect_dom(None)
    assert caps.is_live_dom is True
    assert caps.deep_thinking is True
    assert caps.web_search is True
    assert caps.supported_data_types.image is True
    assert len(caps.available_models) == 2
    assert caps.available_models[0].id == "Smartest"
    assert caps.available_models[0].selected is True
    assert caps.available_models[0].metadata["reasoning"] is True
    assert caps.available_models[0].metadata["thinking_format"] == "openai"


@pytest.mark.asyncio
async def test_registry_bypasses_browser_for_9router() -> None:
    from app.adapters.capabilities.registry import CapabilitiesRegistry
    reg = CapabilitiesRegistry.instance()

    # Calling with force_sync=True for 9router should not raise KeyError or need BrowserSessionManager
    caps = await reg.get_capabilities("9router", force_sync=True)
    assert caps.provider == "9router"
    assert len(caps.available_models) > 0


def test_pipeline_create_adapter_router() -> None:
    adapter = create_adapter("9router")
    assert isinstance(adapter, RouterAPIAdapter)
    adapter2 = create_adapter("router")
    assert isinstance(adapter2, RouterAPIAdapter)


def test_router_schema_validation() -> None:
    from app.api.schemas import AgentResearchRequest, ResearchRequest

    req = ResearchRequest(query="Thị trường AI", providers=["9router"])
    assert req.providers == ["9router"]

    agent_req = AgentResearchRequest(
        query="Nghiên cứu về LLM",
        orchestrator_provider="9router",
        lead_provider="9router",
        delegated_providers=["9router", "gemini"],
    )
    assert agent_req.orchestrator_provider == "9router"
    assert agent_req.lead_provider == "9router"
    assert agent_req.delegated_providers == ["9router", "gemini"]


@pytest.mark.asyncio
async def test_ask_resolves_json_mode_and_default_model() -> None:
    seen_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen_models.append(body.get("model"))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "OK"}}]},
        )

    adapter = RouterAPIAdapter(
        "sk-test",
        base_url="http://localhost:20128/v1",
        default_model="Smartest",
        transport=httpx.MockTransport(handler),
    )

    # 1. When mode is a JSON string with model_id: "default", should fall back to default_model "Smartest"
    json_mode = json.dumps({"model_id": "default", "thinking_level_id": "auto", "mode_id": "standard"})
    await adapter.ask("Test 1", timeout_s=5, mode=json_mode)
    assert seen_models[-1] == "Smartest"

    # 2. When mode is a JSON string with specific model_id, should use that model
    json_mode_custom = json.dumps({"model_id": "cx/gpt-6.1-sol", "thinking_level_id": "high"})
    await adapter.ask("Test 2", timeout_s=5, mode=json_mode_custom)
    assert seen_models[-1] == "cx/gpt-6.1-sol"

    # 3. When mode is "default" or "standard", should use default_model "Smartest"
    await adapter.ask("Test 3", timeout_s=5, mode="default")
    assert seen_models[-1] == "Smartest"


