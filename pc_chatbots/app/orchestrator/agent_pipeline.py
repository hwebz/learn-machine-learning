from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
from typing import Any

import structlog
from sqlmodel import select

from app.adapters.base import ProviderAdapter, Source as AdapterSource
from app.adapters.browser_base import ProviderNeedsUserAction
from app.browser.session import BrowserSessionManager
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.models import Claim, Job, JobEvent, ProviderRun, Report, Source, Subtask, utc_now
from app.orchestrator.pipeline import (
    AdapterNeedsUserAction,
    TERMINAL_STATUSES,
    create_adapter,
)
from app.adapters.capabilities.registry import CapabilitiesRegistry
from app.api.schemas import OrchestratorOutput
from app.orchestrator.step_emitter import StepEmitter, notify_job_event

logger = structlog.get_logger(__name__)

TONE_INSTRUCTIONS: dict[str, str] = {
    "academic": (
        "Write in formal academic style. Use precise terminology, maintain rigorous objectivity, "
        "structure the response with an abstract/overview, methodology & evidence, detailed analysis, and conclusions. "
        "Cite sources and attributing providers with brackets where applicable."
    ),
    "professional": (
        "Write in professional business style. Be concise, results-oriented, and structured. "
        "Use bullet points for key findings, include an executive overview, and highlight practical, actionable takeaways."
    ),
    "analytical": (
        "Write in analytical style. Compare and contrast perspectives from different providers, highlight data patterns, "
        "critique claims, examine trade-offs, and present an evidence-based synthesis."
    ),
    "explanatory": (
        "Write in clear pedagogical style suitable for teaching. Break down complex concepts into digestible parts, "
        "use intuitive analogies, and structure the explanation progressively from fundamentals to advanced applications."
    ),
    "journalistic": (
        "Write in journalistic investigative style. Lead with the core revelation or hook, present balanced multiple viewpoints, "
        "incorporate direct insights from the research, and maintain neutral, objective prose."
    ),
    "creative": (
        "Write in an engaging, narrative-driven style with vivid language. Make the material compelling and memorable "
        "while preserving factual integrity and depth."
    ),
    "executive": (
        "Write as an ultra-concise executive briefing. Start with a 3-sentence TL;DR, followed by key metrics, strategic implications, "
        "and concrete recommendations. Format with tables or quick bullet points suitable for a 2-minute skim."
    ),
    "conversational": (
        "Write in an approachable, conversational tone. Use direct and friendly address, clear natural language, "
        "practical examples, and make complex ideas easily accessible."
    ),
}


from .provider_specs import PROVIDER_CATALOG, resolve_provider_live_prompt_info

__all__ = [
    "AgentPipelineError",
    "AgentPipelineResult",
    "AgentStageStatus",
    "PROVIDER_CATALOG",
    "build_orchestrator_prompt",
    "build_synthesis_prompt",
    "parse_orchestrator_plan",
    "resolve_provider_live_prompt_info",
    "run_agent_pipeline",
]


def build_orchestrator_prompt(
    research_topic: str,
    allowed_providers: list[str] | None = None,
    provider_configs: dict[str, Any] | None = None,
    provider_capabilities: dict[str, Any] | None = None,
) -> str:
    valid_allowed = [p.lower() for p in (allowed_providers or []) if p.lower() in PROVIDER_CATALOG]
    if not valid_allowed:
        valid_allowed = list(PROVIDER_CATALOG.keys())

    pconfigs = provider_configs or {}
    pcaps = provider_capabilities or {}

    provider_lines: list[str] = []
    for idx, pid in enumerate(valid_allowed, start=1):
        info = resolve_provider_live_prompt_info(pid, pconfigs.get(pid), pcaps.get(pid))
        dom_badge = "[REAL DOM SYNCED]" if info.get("is_live_dom") else "[LATEST LIVE CONFIG]"
        provider_lines.append(
            f'{idx}. {info["name"]} (id: "{pid}") {dom_badge}\n'
            f'   - Active DOM Setting: {info["active_summary"]}\n'
            f'   - Expected "config" JSON Schema: {info["config_schema"]}\n'
            f'   - Specialized Sub-topic Role: {info["role"]}'
        )
    providers_text = "\n".join(provider_lines)
    allowed_ids_str = ", ".join(f'"{pid}"' for pid in valid_allowed)

    return f"""You are a Master Research Orchestrator.
Your goal is to analyze the research topic provided by the user and intelligently decompose it into 2 to 5 specialized sub-tasks.
Each sub-task must be assigned to the most appropriate AI provider from the ALLOWED providers list below.

## Available Allowed Providers and Configurations (Live DOM Synced):
{providers_text}

## STRICT REQUIREMENT: Allowed Delegation Providers
You are STRICTLY RESTRICTED to assigning sub-tasks ONLY to providers in this allowed list: [{allowed_ids_str}].
DO NOT assign any sub-task to any provider outside this list. Every single item in "agents_dispatch" MUST have "id" strictly matching one of [{allowed_ids_str}].

## Rules:
- Decompose the topic into 2 to 5 distinct, non-overlapping specialized sub-topics.
- Assign each sub-topic to the provider best suited for that angle among the allowed providers, matching their active capabilities and strengths described above.
- In each "agents_dispatch" item, provide a valid "config" object that matches the provider's active DOM setting and expected schema.
- Each "question" must be a self-contained, detailed prompt for that provider to investigate.
- The output MUST be strictly valid JSON matching the schema below. Do not wrap in markdown or add explanations.

## Output JSON Schema:
{{
  "research_topic": "{research_topic}",
  "agents_dispatch": [
    {{
      "id": "<provider_id>",
      "name": "<provider_name>",
      "config": {{ ... }},
      "sub_topic": "<Brief specialized sub-topic title>",
      "question": "<Detailed research prompt tailored for this provider's capabilities>"
    }}
  ]
}}

Research Topic to decompose:
{research_topic}"""


def build_lead_prompt(research_topic: str, findings: list[dict[str, Any]], tone: str) -> str:
    tone_directive = TONE_INSTRUCTIONS.get(tone.lower(), TONE_INSTRUCTIONS["professional"])

    sections: list[str] = []
    for item in findings:
        prov = item.get("provider", "AI")
        branch = item.get("branch", "Nghiên cứu")
        ans = item.get("answer_md", "").strip()
        sections.append(f"### Nhánh nghiên cứu: {branch} (Cung cấp bởi: {prov})\n\n{ans}")

    findings_text = "\n\n---\n\n".join(sections) if sections else "Không có dữ liệu chi tiết từ các nhà cung cấp."

    return f"""You are the Lead Research Synthesizer.
You have been provided with comprehensive findings gathered by specialized AI agents investigating different aspects of the topic:
"{research_topic}"

## Findings from Autonomous AI Providers:
{findings_text}

## Your Task:
Synthesize all the above findings into a single, cohesive, high-quality Markdown research report.
- Synthesize facts, cross-compare differing points, and eliminate redundancy.
- Attribute key findings to the respective agents/sources where helpful.
- Organize clearly with headers, bullet points, and analytical conclusions.

## Tone & Style Directive:
{tone_directive}

Produce the final comprehensive Markdown report now:"""


def _clean_json_str(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


async def _set_agent_status(
    job_id: str,
    status: str,
    *,
    message: str | None = None,
    event_type: str = "progress",
    data: dict[str, Any] | None = None,
    subtasks_total: int | None = None,
    subtasks_done: int | None = None,
) -> None:
    phase_messages = {
        "queued": "Nhiệm vụ nghiên cứu đa tác nhân đã vào hàng đợi.",
        "orchestrating": "Orchestrator đang phân rã nhiệm vụ và lập kế hoạch...",
        "researching": "Các chatbot chuyên biệt đang đồng loạt nghiên cứu...",
        "leading": "Lead Provider đang tổng hợp và tinh chỉnh báo cáo hoàn chỉnh...",
        "completed": "Nghiên cứu đa tác nhân hoàn tất thành công.",
        "partial": "Nghiên cứu hoàn tất một phần.",
        "failed": "Quá trình nghiên cứu đa tác nhân thất bại.",
        "cancelled": "Nhiệm vụ nghiên cứu đã bị hủy.",
        "needs_user_action": "Cần can thiệp người dùng (đăng nhập hoặc giải CAPTCHA).",
    }
    msg = message or phase_messages.get(status, f"Trạng thái: {status}")
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None and job.status not in TERMINAL_STATUSES:
            job.status = status
            if subtasks_total is not None:
                job.subtasks_total = subtasks_total
            if subtasks_done is not None:
                job.subtasks_done = subtasks_done
            job.updated_at = utc_now()
            session.add(JobEvent(
                job_id=job_id,
                status=status,
                event_type=event_type,
                message=msg,
                subtasks_total=job.subtasks_total,
                subtasks_done=job.subtasks_done,
                data_json=json.dumps(data, ensure_ascii=False) if data is not None else None,
            ))
            await session.commit()
        notify_job_event(job_id)


async def run_agent_pipeline(job_id: str, cancel_event: asyncio.Event) -> None:
    """Executes the 3-stage Deep Research Orchestrator pipeline:
    1. Orchestrate: Decompose topic into subtasks with a chosen Orchestrator provider.
    2. Research: Dispatch each subtask to assigned providers in parallel.
    3. Lead Synthesize: Synthesize all responses using chosen Lead provider with selected tone.
    """
    logger.info("run_agent_pipeline_started", job_id=job_id)
    try:
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status == "cancelled":
                return
            research_topic = job.query
            orchestrator_prov = job.orchestrator_provider or "gemini"
            lead_prov = job.lead_provider or "chatgpt"
            tone = job.tone or "professional"
            try:
                orch_config = json.loads(job.orchestrator_config_json) if job.orchestrator_config_json else {}
            except Exception:
                orch_config = {}
            try:
                lead_config = json.loads(job.lead_config_json) if job.lead_config_json else {}
            except Exception:
                lead_config = {}

            delegated_providers: list[str] = []
            provider_configs: dict[str, Any] = {}
            provider_capabilities: dict[str, Any] = {}
            try:
                cfg_obj = json.loads(job.config_json) if job.config_json else {}
                raw_delegated = cfg_obj.get("delegated_providers") or []
                delegated_providers = [str(p).lower() for p in raw_delegated if str(p).lower() in PROVIDER_CATALOG]
                provider_configs = cfg_obj.get("provider_configs") or {}
                provider_capabilities = cfg_obj.get("provider_capabilities") or {}
            except Exception:
                delegated_providers = []

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # ---------------------------------------------------------
        # PHASE 1: ORCHESTRATING (Task decomposition)
        # ---------------------------------------------------------
        orch_start = time.monotonic()
        await _set_agent_status(
            job_id,
            "orchestrating",
            message=f"Orchestrator ({orchestrator_prov}) đang phân tích chủ đề và lập kế hoạch phân rã...",
            data={"orchestrator": orchestrator_prov, "config": orch_config, "role": "orchestrator", "elapsed_s": 0.0},
        )

        orch_adapter = create_adapter(orchestrator_prov)
        orch_prompt = build_orchestrator_prompt(
            research_topic,
            allowed_providers=delegated_providers,
            provider_configs=provider_configs,
            provider_capabilities=provider_capabilities,
        )

        ask_kwargs: dict[str, Any] = {
            "timeout_s": 300,
            "mode": json.dumps(orch_config) if orch_config else "default",
        }
        if "on_step" in inspect.signature(orch_adapter.ask).parameters:
            ask_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=orchestrator_prov,
                status="orchestrating",
                role="orchestrator",
                cancel_event=cancel_event,
                start_time=orch_start,
            )

        try:
            orch_res = await orch_adapter.ask(orch_prompt, **ask_kwargs)
        except Exception as exc:
            logger.error("orchestrator_provider_failed", provider=orchestrator_prov, error=str(exc))
            await _set_agent_status(job_id, "failed", message=f"Orchestrator ({orchestrator_prov}) gặp lỗi: {exc}")
            return
        finally:
            await BrowserSessionManager.close_session(orchestrator_prov)

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        cleaned_json = _clean_json_str(orch_res.answer_markdown)
        dispatch_items: list[dict[str, Any]] = []
        try:
            parsed = json.loads(cleaned_json)
            validated = OrchestratorOutput.model_validate(parsed)
            dispatch_items = [item.model_dump() for item in validated.agents_dispatch]
        except Exception as json_err:
            logger.warning("orchestrator_json_parse_failed", error=str(json_err), raw=orch_res.answer_markdown[:300])
            # Fallback default plan using allowed delegated providers with live DOM configs
            p1 = delegated_providers[0] if delegated_providers else "deepseek"
            p2 = delegated_providers[1 % len(delegated_providers)] if delegated_providers else "perplexity"
            p1_info = resolve_provider_live_prompt_info(p1, provider_configs.get(p1), provider_capabilities.get(p1))
            p2_info = resolve_provider_live_prompt_info(p2, provider_configs.get(p2), provider_capabilities.get(p2))
            dispatch_items = [
                {
                    "id": p1,
                    "name": p1_info["name"],
                    "config": p1_info["default_config"],
                    "sub_topic": "Nền tảng lý thuyết & Giải thuật",
                    "question": f"Phân tích chuyên sâu về kiến trúc và thuật toán liên quan đến: {research_topic}",
                },
                {
                    "id": p2,
                    "name": p2_info["name"],
                    "config": p2_info["default_config"],
                    "sub_topic": "Dữ liệu ứng dụng thực tế & Nguồn dẫn chứng",
                    "question": f"Tìm kiếm các số liệu, tài liệu học thuật và trường hợp ứng dụng thực tế mới nhất của: {research_topic}",
                },
            ]

        # Enforce that only allowed delegated providers are used
        if delegated_providers:
            sanitized_dispatch: list[dict[str, Any]] = []
            for item in dispatch_items:
                pid = str(item.get("id", "")).lower()
                if pid not in delegated_providers:
                    fallback_id = delegated_providers[len(sanitized_dispatch) % len(delegated_providers)]
                    fallback_info = resolve_provider_live_prompt_info(fallback_id, provider_configs.get(fallback_id), provider_capabilities.get(fallback_id))
                    item["id"] = fallback_id
                    item["name"] = fallback_info["name"]
                    if not item.get("config"):
                        item["config"] = fallback_info["default_config"]
                sanitized_dispatch.append(item)
            dispatch_items = sanitized_dispatch

        orch_conv_url = str(orch_res.conversation_url) if getattr(orch_res, "conversation_url", None) else None
        orch_duration = round(time.monotonic() - orch_start, 1)
        for idx, item in enumerate(dispatch_items, start=1):
            item["branch_index"] = idx
            item["provider_role_key"] = f"subtask:{item['id']}_{idx}"

        # Update Job with dispatch plan
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                db_j.orchestrator_dispatch_json = json.dumps(dispatch_items, ensure_ascii=False)
                db_j.orchestrator_conversation_url = orch_conv_url
                db_j.subtasks_total = len(dispatch_items)
                db_j.subtasks_done = 0
                db_j.updated_at = utc_now()
                session.add(ProviderRun(
                    id=f"{job_id}:orchestrator:run",
                    subtask_id=f"{job_id}:orchestrator",
                    provider=orchestrator_prov,
                    answer_md=orch_res.answer_markdown,
                    conversation_url=orch_conv_url,
                    status="ok",
                ))
                session.add(JobEvent(
                    job_id=job_id,
                    status="orchestrating",
                    event_type="orchestrator_result",
                    provider=orchestrator_prov,
                    step="orchestrator_result",
                    message=f"Orchestrator ({orchestrator_prov}) đã phân rã thành {len(dispatch_items)} nhiệm vụ nghiên cứu chuyên sâu.",
                    subtasks_total=len(dispatch_items),
                    subtasks_done=0,
                    data_json=json.dumps({
                        "dispatch": dispatch_items,
                        "role": "orchestrator",
                        "provider_role_key": "orchestrator",
                        "elapsed_s": orch_duration,
                        "conversation_url": orch_conv_url,
                    }, ensure_ascii=False),
                ))
                await session.commit()

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # ---------------------------------------------------------
        # PHASE 2: RESEARCHING (Parallel dispatch of subtasks)
        # ---------------------------------------------------------
        await _set_agent_status(
            job_id,
            "researching",
            message=f"Bắt đầu điều phối {len(dispatch_items)} tác nhân nghiên cứu đồng thời...",
            subtasks_total=len(dispatch_items),
            subtasks_done=0,
        )

        subtasks: list[Subtask] = []
        async with SessionLocal() as session:
            for idx, item in enumerate(dispatch_items, start=1):
                st = Subtask(
                    id=f"{job_id}:{item['id']}_{idx}",
                    job_id=job_id,
                    branch=item.get("sub_topic", f"Nhánh {idx}"),
                    provider=item["id"],
                    prompt=item["question"],
                )
                subtasks.append(st)
                session.add(st)
            await session.commit()

        sources: list[dict[str, str]] = []
        runs: list[dict[str, Any]] = []
        results_lock = asyncio.Lock()
        total_subtasks = len(subtasks)

        async def _run_subtask(st: Subtask, item_cfg: dict[str, Any], idx: int) -> None:
            if cancel_event.is_set():
                return

            prov = st.provider
            subtask_start = time.monotonic()
            role_key = f"subtask:{prov}_{idx}"
            adapter = create_adapter(prov)
            ask_args: dict[str, Any] = {
                "timeout_s": 600,
                "mode": json.dumps(item_cfg) if item_cfg else "default",
            }
            if "on_step" in inspect.signature(adapter.ask).parameters:
                ask_args["on_step"] = StepEmitter(
                    job_id=job_id,
                    provider=prov,
                    status="researching",
                    role="subtask",
                    cancel_event=cancel_event,
                    subtasks_total=total_subtasks,
                    get_subtasks_done=lambda: len(runs),
                    start_time=subtask_start,
                    extra_payload={
                        "subtask_id": st.id,
                        "branch": st.branch,
                        "branch_index": idx,
                        "provider_role_key": role_key,
                    },
                )

            try:
                result = await adapter.ask(st.prompt, **ask_args)
                status_str = result.status
                ans_text = result.answer_markdown
                res_sources = result.sources
            except Exception as exc:
                logger.error("subtask_execution_failed", provider=prov, error=str(exc))
                status_str = "error"
                ans_text = f"Không thể lấy câu trả lời từ {prov}: {exc}"
                res_sources = []
            finally:
                await BrowserSessionManager.close_session(prov)

            subtask_duration = round(time.monotonic() - subtask_start, 1)
            sub_conv_url = str(result.conversation_url) if getattr(result, "conversation_url", None) else None
            async with results_lock:
                run_item = {
                    "provider": prov,
                    "branch": st.branch,
                    "branch_index": idx,
                    "status": status_str,
                    "answer_md": ans_text,
                    "answer_markdown": ans_text,
                    "conversation_url": sub_conv_url,
                    "elapsed_ms": int(subtask_duration * 1000),
                    "elapsed_s": subtask_duration,
                    "subtask_id": st.id,
                    "role": "subtask",
                    "provider_role_key": role_key,
                }
                runs.append(run_item)
                done_cnt = len(runs)

                async with SessionLocal() as s:
                    db_j = await s.get(Job, job_id)
                    db_st = await s.get(Subtask, st.id)
                    if db_st is not None:
                        db_st.status = "completed" if status_str == "ok" else "failed"

                    s.add(ProviderRun(
                        id=f"{job_id}:{prov}_{idx}:run",
                        subtask_id=st.id,
                        provider=prov,
                        answer_md=ans_text,
                        conversation_url=sub_conv_url,
                        status=status_str,
                    ))

                    for src in res_sources:
                        s_id = f"{job_id}:S{len(sources) + 1}"
                        s_dict = {"id": s_id, "url": str(src.url), "title": src.title or "", "provider": prov}
                        sources.append(s_dict)
                        s.add(Source(
                            id=s_id,
                            run_id=f"{job_id}:{prov}_{idx}:run",
                            job_id=job_id,
                            provider=prov,
                            url=str(src.url),
                            title=src.title,
                        ))

                    if db_j is not None:
                        db_j.subtasks_done = done_cnt
                        db_j.provider_runs_json = json.dumps(runs, ensure_ascii=False)
                        db_j.sources_json = json.dumps(sources, ensure_ascii=False)
                        db_j.updated_at = utc_now()
                        s.add(JobEvent(
                            job_id=job_id,
                            status="researching",
                            event_type="progress",
                            provider=prov,
                            step="completed" if status_str == "ok" else "failed",
                            message=f"Đã hoàn thành {done_cnt}/{total_subtasks} tác nhân ({prov}: {status_str}).",
                            subtasks_total=total_subtasks,
                            subtasks_done=done_cnt,
                            data_json=json.dumps({
                                "provider": prov,
                                "branch": st.branch,
                                "branch_index": idx,
                                "status": status_str,
                                "elapsed_s": subtask_duration,
                                "role": "subtask",
                                "subtask_id": st.id,
                                "provider_role_key": role_key,
                                "conversation_url": sub_conv_url,
                            }, ensure_ascii=False),
                        ))
                    await s.commit()

        try:
            if settings.work_mode == "async":
                sem = asyncio.Semaphore(max(1, settings.max_concurrent_browsers))
                async def _throttled_task(st: Subtask, cfg: dict[str, Any], idx: int) -> None:
                    async with sem:
                        if cancel_event.is_set():
                            return
                        await _run_subtask(st, cfg, idx)

                await asyncio.gather(*[
                    _throttled_task(st, dispatch_items[i].get("config", {}), i + 1)
                    for i, st in enumerate(subtasks)
                ])
            else:
                for i, st in enumerate(subtasks):
                    if cancel_event.is_set():
                        break
                    await _run_subtask(st, dispatch_items[i].get("config", {}), i + 1)
        finally:
            await BrowserSessionManager.close_all()

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # ---------------------------------------------------------
        # PHASE 3: LEADING (Lead Provider Synthesis)
        # ---------------------------------------------------------
        lead_start = time.monotonic()
        await _set_agent_status(
            job_id,
            "leading",
            message=f"Lead Provider ({lead_prov}) đang tổng hợp báo cáo chuyên sâu theo văn phong '{tone}'...",
            data={"lead": lead_prov, "tone": tone, "config": lead_config, "role": "lead", "provider_role_key": "lead", "elapsed_s": 0.0},
            subtasks_total=total_subtasks,
            subtasks_done=total_subtasks,
        )

        lead_adapter = create_adapter(lead_prov)
        lead_prompt = build_lead_prompt(research_topic, runs, tone)

        lead_kwargs: dict[str, Any] = {
            "timeout_s": 600,
            "mode": json.dumps(lead_config) if lead_config else "default",
        }
        if "on_step" in inspect.signature(lead_adapter.ask).parameters:
            lead_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=lead_prov,
                status="leading",
                role="lead",
                cancel_event=cancel_event,
                subtasks_total=total_subtasks,
                get_subtasks_done=lambda: total_subtasks,
                start_time=lead_start,
            )

        lead_conv_url = None
        try:
            lead_res = await lead_adapter.ask(lead_prompt, **lead_kwargs)
            final_report = lead_res.answer_markdown
            lead_conv_url = str(lead_res.conversation_url) if getattr(lead_res, "conversation_url", None) else None
        except Exception as exc:
            logger.error("lead_synthesis_failed", provider=lead_prov, error=str(exc))
            # Fallback report compilation
            final_report = f"# Báo cáo Nghiên cứu: {research_topic}\n\n"
            for r in runs:
                final_report += f"## {r.get('branch', r.get('provider'))}\n\n{r.get('answer_md', '')}\n\n"
        finally:
            await BrowserSessionManager.close_session(lead_prov)

        lead_duration = round(time.monotonic() - lead_start, 1)

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # Complete the job
        ok_count = sum(1 for r in runs if r.get("status") == "ok")
        final_status = "completed" if ok_count > 0 else "failed"

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None and db_j.status not in TERMINAL_STATUSES:
                db_j.status = final_status
                db_j.report_markdown = final_report
                db_j.lead_conversation_url = lead_conv_url
                db_j.finished_at = utc_now()
                db_j.updated_at = utc_now()

                # Build consolidated map of all provider conversation URLs
                all_convs: dict[str, str] = {}
                if db_j.orchestrator_conversation_url:
                    all_convs["orchestrator"] = db_j.orchestrator_conversation_url
                if lead_conv_url:
                    all_convs["lead"] = lead_conv_url
                for r in runs:
                    role_key = r.get("provider_role_key") or r.get("provider")
                    if role_key and r.get("conversation_url"):
                        all_convs[role_key] = r["conversation_url"]
                        if r.get("provider") and r["provider"] not in all_convs:
                            all_convs[r["provider"]] = r["conversation_url"]
                db_j.provider_conversations_json = json.dumps(all_convs, ensure_ascii=False)

                session.add(Report(id=job_id, job_id=job_id, markdown=final_report))
                session.add(ProviderRun(
                    id=f"{job_id}:lead:run",
                    subtask_id=f"{job_id}:lead",
                    provider=lead_prov,
                    answer_md=final_report,
                    conversation_url=lead_conv_url,
                    status="ok" if final_status == "completed" else "partial",
                ))
                session.add(JobEvent(
                    job_id=job_id,
                    status=final_status,
                    event_type="progress",
                    provider=lead_prov,
                    step="completed",
                    message=f"Nhiệm vụ nghiên cứu đa tác nhân hoàn thành ({final_status}).",
                    subtasks_total=total_subtasks,
                    subtasks_done=total_subtasks,
                    data_json=json.dumps({
                        "lead_provider": lead_prov,
                        "elapsed_s": lead_duration,
                        "role": "lead",
                        "provider_role_key": "lead",
                        "tone": tone,
                        "conversation_url": lead_conv_url,
                    }, ensure_ascii=False),
                ))
                await session.commit()

        logger.info("run_agent_pipeline_finished", job_id=job_id, status=final_status)
        await BrowserSessionManager.close_all()

    except asyncio.CancelledError:
        logger.info("run_agent_pipeline_cancelled", job_id=job_id)
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None and db_j.status not in TERMINAL_STATUSES:
                db_j.status = "cancelled"
                db_j.finished_at = utc_now()
                db_j.updated_at = utc_now()
                session.add(JobEvent(
                    job_id=job_id,
                    status="cancelled",
                    event_type="progress",
                    message="Người dùng đã dừng phiên nghiên cứu tác nhân.",
                ))
                await session.commit()
        notify_job_event(job_id)
        await BrowserSessionManager.close_all()
        raise

    except Exception as exc:
        logger.exception("agent_pipeline_fatal_error", job_id=job_id, error=str(exc))
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None and db_j.status not in TERMINAL_STATUSES:
                db_j.status = "failed"
                db_j.error = f"Lỗi hệ thống tác nhân: {exc}"
                db_j.finished_at = utc_now()
                db_j.updated_at = utc_now()
                session.add(JobEvent(job_id=job_id, status="failed", event_type="progress", message=f"Lỗi hệ thống tác nhân: {exc}"))
                await session.commit()
