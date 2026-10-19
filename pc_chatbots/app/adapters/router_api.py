from __future__ import annotations

import re
from datetime import datetime, timezone
import json
from typing import Any

import httpx
import structlog
from pydantic import HttpUrl

from app.adapters.base import HealthStatus, ProviderResult, Source, StepCallback
from app.core.config import settings

logger = structlog.get_logger(__name__)


class RouterAPIAdapter:
    """Universal OpenAI-compatible API adapter for 9Router and local LLM routers."""

    name = "9router"
    chat_endpoint = "/chat/completions"
    models_endpoint = "/models"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        default_model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.router_api_key
        self.base_url = (base_url or settings.router_base_url).rstrip("/")
        self.default_model = default_model or settings.router_model_lead or "Smartest"
        self.transport = transport

    async def health(self) -> HealthStatus:
        """Probe the 9Router endpoint to verify connectivity and available models."""
        url = f"{self.base_url}{self.models_endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(4.0),
                transport=self.transport,
            ) as client:
                res = await client.get(url, headers=headers)

            if res.status_code == 200:
                payload = res.json()
                models_data = payload.get("data", []) if isinstance(payload, dict) else []
                model_count = len(models_data) if isinstance(models_data, list) else 0
                return HealthStatus(
                    logged_in=True,
                    selectors_ok=True,
                    detail=f"9Router online at {self.base_url} ({model_count} models available)",
                )
            return HealthStatus(
                logged_in=False,
                selectors_ok=False,
                detail=f"9Router returned HTTP {res.status_code}: {res.text[:100]}",
            )
        except Exception as exc:
            return HealthStatus(
                logged_in=False,
                selectors_ok=False,
                detail=f"Cannot reach 9Router at {self.base_url} ({type(exc).__name__}: {exc})",
            )

    async def ask(
        self,
        prompt: str,
        *,
        timeout_s: int,
        mode: str = "default",
        on_step: StepCallback | None = None,
        conversation_url: str | None = None,
        **kwargs: Any,
    ) -> ProviderResult:
        """Query 9Router with full support for all OpenAI-compatible response formats."""
        started_at = datetime.now(timezone.utc)

        # 1. Resolve model & options
        opts: dict[str, Any] = {}
        if isinstance(mode, str) and mode.strip().startswith("{"):
            try:
                parsed = json.loads(mode)
                if isinstance(parsed, dict):
                    opts = parsed
            except Exception:
                pass

        raw_model = (
            kwargs.get("model")
            or kwargs.get("model_id")
            or opts.get("model")
            or opts.get("model_id")
            or (settings.router_model_lead if (mode in ("deep", "thinking") or opts.get("mode_id") == "deep_research") else None)
            or (mode if mode and not mode.strip().startswith("{") and mode not in ("default", "standard") else None)
        )

        if not raw_model or str(raw_model).strip().lower() in ("default", "none", "auto", "standard"):
            model = self.default_model
        else:
            model = str(raw_model).strip()

        if on_step is not None:
            await on_step(
                "requesting",
                f"Đang gửi yêu cầu đến 9Router ({model})...",
                {"model": model, "base_url": self.base_url},
            )

        # 2. Build completion request
        req_body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        if "temperature" in kwargs:
            req_body["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            req_body["max_tokens"] = kwargs["max_tokens"]

        thinking_level = kwargs.get("thinking_level") or kwargs.get("thinking_level_id") or opts.get("thinking_level_id")
        if thinking_level == "high":
            req_body["reasoning_effort"] = "high"
        elif thinking_level == "medium":
            req_body["reasoning_effort"] = "medium"
        elif thinking_level == "off":
            req_body["reasoning_effort"] = "none"

        url = f"{self.base_url}{self.chat_endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(float(timeout_s))
        async with httpx.AsyncClient(
            timeout=timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(url, headers=headers, json=req_body)

        if response.is_error:
            err_msg = f"9Router API returned HTTP {response.status_code}: {response.text[:200]}"
            logger.error("router_api_error", status_code=response.status_code, body=response.text[:200])
            raise RuntimeError(err_msg)

        if on_step is not None:
            await on_step("extracting", "Đang xử lý và chuẩn hóa dữ liệu từ 9Router...", None)

        payload = response.json() if response.content else {}

        # 3. Parse answer text and reasoning across all formats
        answer, reasoning = _extract_answer_and_reasoning(payload)

        # If reasoning/thinking tokens detected, emit thinking progress
        if reasoning and on_step is not None:
            await on_step(
                "thinking_progress",
                f"9Router suy luận ({len(reasoning)} ký tự)...",
                {
                    "is_thinking": True,
                    "thinking_text": reasoning,
                    "thinking_steps": [
                        {
                            "title": f"9Router Reasoning ({model})",
                            "description": reasoning,
                            "status": "completed",
                        }
                    ],
                },
            )

        # 4. Extract citations / search results
        sources = _extract_sources(payload, answer)

        finished_at = datetime.now(timezone.utc)
        status = "ok" if bool(answer and answer.strip()) else "error"
        error_msg = None if status == "ok" else "9Router returned an empty or unparseable response."

        return ProviderResult(
            provider=self.name,
            prompt=prompt,
            answer_markdown=answer,
            sources=sources,
            conversation_url=None,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            artifact_paths=[],
            error=error_msg,
        )

    async def delete_conversation(self, conversation_url: str) -> bool:
        return True


def _extract_answer_and_reasoning(payload: dict[str, Any]) -> tuple[str, str | None]:
    """Universal parser for OpenAI-compatible chat responses, thinking/reasoning tags,
    multimodal parts, tool calls, and legacy completion outputs."""
    if not isinstance(payload, dict):
        return str(payload) if payload is not None else "", None

    reasoning_text: str | None = None
    answer_text: str = ""

    choices = payload.get("choices")
    if isinstance(choices, list) and len(choices) > 0:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict):
                # Format A: Dedicated reasoning fields (DeepSeek-R1 / Qwen / OpenRouter)
                r_content = msg.get("reasoning_content") or msg.get("reasoning") or msg.get("thought")
                if isinstance(r_content, str) and r_content.strip():
                    reasoning_text = r_content.strip()

                content = msg.get("content")

                # Format B: String content (which may contain <think>...</think>)
                if isinstance(content, str):
                    raw_str = content
                    think_match = re.search(r"<think>(.*?)</think>", raw_str, flags=re.DOTALL | re.IGNORECASE)
                    if think_match:
                        embedded_reasoning = think_match.group(1).strip()
                        if not reasoning_text and embedded_reasoning:
                            reasoning_text = embedded_reasoning
                        # Strip <think>...</think> from main answer
                        raw_str = re.sub(r"<think>.*?</think>", "", raw_str, flags=re.DOTALL | re.IGNORECASE).strip()
                    answer_text = raw_str.strip()

                # Format C: Content parts list (multimodal / structured parts)
                elif isinstance(content, list):
                    parts: list[str] = []
                    for item in content:
                        if isinstance(item, dict):
                            t = item.get("text") or item.get("output_text")
                            if t and isinstance(t, str):
                                parts.append(t.strip())
                        elif isinstance(item, str):
                            parts.append(item.strip())
                    answer_text = "\n\n".join(parts)

                # Format D: Refusal field
                if not answer_text and msg.get("refusal"):
                    answer_text = f"Refusal: {msg['refusal']}"

                # Format E: Tool calls fallback representation
                if not answer_text and msg.get("tool_calls"):
                    tool_calls = msg["tool_calls"]
                    if isinstance(tool_calls, list):
                        lines = []
                        for tc in tool_calls:
                            if isinstance(tc, dict):
                                fn = tc.get("function", {})
                                name = fn.get("name", "tool")
                                args = fn.get("arguments", "")
                                lines.append(f"**Tool Call (`{name}`)**:\n```json\n{args}\n```")
                        answer_text = "\n\n".join(lines)

            # Format F: Legacy completion choices[0].text
            if not answer_text and "text" in first and isinstance(first["text"], str):
                answer_text = first["text"].strip()

    # Format G: Top-level root text or fallback output
    if not answer_text:
        for key in ("output_text", "text", "response", "output", "result"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                answer_text = val.strip()
                break

    # Format H: Error payload directly in json
    if not answer_text and "error" in payload:
        err = payload["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        answer_text = f"Error: {msg}"

    return answer_text, reasoning_text


def _extract_sources(payload: dict[str, Any], answer_text: str) -> list[Source]:
    """Extract citations from OpenAI-style annotations, OpenRouter citations,
    Perplexity-style search_results, and markdown reference links."""
    sources: list[Source] = []
    seen_urls: set[str] = set()

    def _add_source(raw_url: Any, title: str | None = None, snippet: str | None = None):
        if not isinstance(raw_url, str):
            return
        u = raw_url.strip()
        if not (u.startswith("http://") or u.startswith("https://")):
            return
        if u in seen_urls:
            return
        try:
            valid_url = HttpUrl(u)
            seen_urls.add(u)
            sources.append(Source(url=valid_url, title=title.strip() if title else None, snippet=snippet.strip() if snippet else None))
        except Exception:
            pass

    if isinstance(payload, dict):
        # 1. choices[0].message.citations
        choices = payload.get("choices")
        if isinstance(choices, list) and len(choices) > 0 and isinstance(choices[0], dict):
            msg = choices[0].get("message")
            if isinstance(msg, dict):
                # citations list
                cits = msg.get("citations")
                if isinstance(cits, list):
                    for c in cits:
                        if isinstance(c, str):
                            _add_source(c)
                        elif isinstance(c, dict):
                            _add_source(c.get("url") or c.get("link"), c.get("title"), c.get("snippet"))

                # annotations (OpenAI url_citation format)
                annotations = msg.get("annotations")
                if isinstance(annotations, list):
                    for a in annotations:
                        if isinstance(a, dict) and a.get("type") == "url_citation":
                            uc = a.get("url_citation", {})
                            if isinstance(uc, dict):
                                _add_source(uc.get("url"), uc.get("title"))

        # 2. Top-level citations
        top_cits = payload.get("citations")
        if isinstance(top_cits, list):
            for c in top_cits:
                if isinstance(c, str):
                    _add_source(c)
                elif isinstance(c, dict):
                    _add_source(c.get("url"), c.get("title"), c.get("snippet"))

        # 3. Top-level search_results
        s_results = payload.get("search_results")
        if isinstance(s_results, list):
            for r in s_results:
                if isinstance(r, dict):
                    _add_source(r.get("url"), r.get("title"), r.get("snippet"))

    # 4. Extract markdown reference links in answer_text: [1]: https://example.com "Title"
    if answer_text:
        ref_matches = re.finditer(
            r"^\[(?P<ref>[^\]]+)\]:\s*(?P<url>https?://[^\s]+)(?:\s+[\"\'](?P<title>[^\"\']+)[\"\'])?",
            answer_text,
            flags=re.MULTILINE,
        )
        for m in ref_matches:
            _add_source(m.group("url"), m.group("title") or m.group("ref"))

        # Extract markdown inline links [Title](https://...)
        inline_matches = re.finditer(
            r"\[(?P<title>[^\]]{2,80})\]\((?P<url>https?://[^\s\)]+)\)",
            answer_text,
        )
        for m in inline_matches:
            title = m.group("title")
            # Filter out non-source links like images or markdown anchors
            if not title.startswith("!") and not title.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                _add_source(m.group("url"), title)

    return sources
