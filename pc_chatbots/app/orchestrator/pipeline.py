from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

import structlog

from app.adapters.base import ProviderAdapter
from app.adapters.browser_base import ProviderNeedsUserAction
from app.adapters.fake import FakeAdapter
from app.adapters.gemini_ui import GeminiUIAdapter
from app.adapters.perplexity_api import PerplexityAgentAdapter
from app.adapters.perplexity_ui import PerplexityUIAdapter
from app.adapters.chatgpt_ui import ChatGPTUIAdapter
from app.adapters.claude_ui import ClaudeUIAdapter
from app.adapters.copilot_ui import CopilotUIAdapter
from app.adapters.deepseek_ui import DeepSeekUIAdapter
from app.adapters.grok_ui import GrokUIAdapter
from app.adapters.kimi_ui import KimiUIAdapter
from app.adapters.meta_ui import MetaUIAdapter
from app.adapters.minimax_ui import MinimaxUIAdapter
from app.adapters.mistral_ui import MistralUIAdapter
from app.adapters.pi_ui import PiUIAdapter
from app.adapters.qwen_ui import QwenUIAdapter
from app.adapters.zhipu_ui import ZhipuUIAdapter
from app.api.schemas import ResearchRequest
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.models import Claim, Job, JobEvent, ProviderRun, Report, Source, Subtask, utc_now

logger = structlog.get_logger(__name__)
TERMINAL_STATUSES = {"completed", "partial", "failed", "needs_user_action", "cancelled"}
PROVIDER_RESULT_FAILURE_STATUSES = {"needs_user_action", "error", "timeout"}


class AdapterNeedsUserAction(RuntimeError):
    pass


# Maps provider name -> UI adapter class for browser automation mode.
_UI_ADAPTERS: dict[str, type] = {
    "perplexity": PerplexityUIAdapter,
    "gemini": GeminiUIAdapter,
    "chatgpt": ChatGPTUIAdapter,
    "claude": ClaudeUIAdapter,
    "copilot": CopilotUIAdapter,
    "deepseek": DeepSeekUIAdapter,
    "grok": GrokUIAdapter,
    "kimi": KimiUIAdapter,
    "meta": MetaUIAdapter,
    "minimax": MinimaxUIAdapter,
    "mistral": MistralUIAdapter,
    "pi": PiUIAdapter,
    "qwen": QwenUIAdapter,
    "zhipu": ZhipuUIAdapter,
}


def create_adapter(provider: str) -> ProviderAdapter:
    mode = settings.research_adapter_mode
    if mode == "fake":
        return FakeAdapter(provider)
    if mode == "ui":
        adapter_cls = _UI_ADAPTERS.get(provider)
        if adapter_cls is not None:
            return adapter_cls()
        raise AdapterNeedsUserAction(f"No UI adapter configured for provider: {provider}")
    if mode == "official_api":
        if provider == "perplexity":
            if not settings.perplexity_api_key:
                raise AdapterNeedsUserAction("Set PERPLEXITY_API_KEY in .env to run Perplexity research.")
            return PerplexityAgentAdapter()
        raise AdapterNeedsUserAction(f"The official API adapter for {provider} is not configured yet.")
    raise AdapterNeedsUserAction(f"Unknown RESEARCH_ADAPTER_MODE={mode!r}. Use fake, official_api, or ui.")


async def _set_status(
    job_id: str,
    status: str,
    *,
    message: str | None = None,
    event_type: str = "progress",
    data: dict[str, Any] | None = None,
) -> None:
    phase_messages = {
        "planning": "Đang lập kế hoạch nghiên cứu...",
        "researching": "Bắt đầu nghiên cứu qua các chatbot...",
        "extracting": "Đang trích xuất dữ liệu và chuẩn hóa thông tin...",
        "verifying": "Đang đối chiếu và kiểm chứng chéo các câu trả lời...",
        "synthesizing": "Đang tổng hợp báo cáo nghiên cứu hoàn chỉnh...",
        "completed": "Nghiên cứu hoàn tất thành công.",
        "partial": "Nghiên cứu hoàn tất một phần.",
        "failed": "Quá trình nghiên cứu thất bại.",
        "cancelled": "Job nghiên cứu đã bị hủy.",
        "needs_user_action": "Cần can thiệp người dùng (đăng nhập hoặc CAPTCHA).",
    }
    msg = message or phase_messages.get(status, f"Trạng thái: {status}")
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None and job.status not in TERMINAL_STATUSES:
            job.status = status
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


async def run_pipeline(job_id: str, cancel_event: asyncio.Event) -> None:
    try:
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status == "cancelled":
                return
            request = ResearchRequest.model_validate_json(job.config_json)
            job.status = "planning"
            job.updated_at = utc_now()
            session.add(JobEvent(
                job_id=job_id,
                status="planning",
                event_type="progress",
                message="Đang lập kế hoạch nghiên cứu và phân rã nhiệm vụ cho từng chatbot...",
                subtasks_total=job.subtasks_total,
                subtasks_done=job.subtasks_done,
            ))
            subtasks = [
                Subtask(id=f"{job_id}:{provider}", job_id=job_id, branch=f"Research branch for {provider}", provider=provider, prompt=request.query)
                for provider in request.providers
            ]
            session.add_all(subtasks)
            await session.commit()

        await _set_status(job_id, "researching")
        sources: list[dict[str, str]] = []
        claims: list[dict[str, object]] = []
        runs: list[dict[str, object]] = []
        answers: list[str] = []
        run_statuses: list[str] = []

        for index, subtask in enumerate(subtasks, start=1):
            if cancel_event.is_set():
                await _set_status(job_id, "cancelled")
                return

            async def _emit_subtask_step(
                step_name: str,
                step_message: str,
                step_data: dict[str, Any] | None = None,
                event_type: str = "step",
            ) -> None:
                async with SessionLocal() as s:
                    db_j = await s.get(Job, job_id)
                    if db_j is None or db_j.status in TERMINAL_STATUSES:
                        return
                    s.add(JobEvent(
                        job_id=job_id,
                        status=db_j.status,
                        event_type=event_type,
                        provider=subtask.provider,
                        step=step_name,
                        message=step_message,
                        subtasks_total=db_j.subtasks_total,
                        subtasks_done=db_j.subtasks_done,
                        data_json=json.dumps(step_data, ensure_ascii=False) if step_data is not None else None,
                    ))
                    await s.commit()

            await _emit_subtask_step(
                step_name="provider_start",
                step_message=f"Bắt đầu nghiên cứu với {subtask.provider} ({index}/{len(subtasks)})...",
                step_data={"provider": subtask.provider, "index": index, "total": len(subtasks)},
            )

            adapter = create_adapter(subtask.provider)
            ask_params = inspect.signature(adapter.ask).parameters
            ask_kwargs: dict[str, Any] = {"timeout_s": request.max_minutes * 60, "mode": request.depth}
            if "on_step" in ask_params or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in ask_params.values()):
                ask_kwargs["on_step"] = _emit_subtask_step

            try:
                result = await adapter.ask(subtask.prompt, **ask_kwargs)
            except (AdapterNeedsUserAction, ProviderNeedsUserAction) as exc:
                logger.warning("subtask_needs_user_action", provider=subtask.provider, reason=str(exc))
                run_statuses.append("needs_user_action")
                run_id = f"{job_id}:{subtask.provider}:run"
                now = utc_now()
                await _emit_subtask_step(
                    step_name="failed",
                    step_message=f"{subtask.provider} yêu cầu can thiệp người dùng: {str(exc)}",
                    step_data={
                        "status": "needs_user_action",
                        "provider": subtask.provider,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                async with SessionLocal() as session:
                    db_job = await session.get(Job, job_id)
                    if db_job is None or db_job.status in TERMINAL_STATUSES:
                        return
                    session.add(ProviderRun(
                        id=run_id, subtask_id=subtask.id, provider=subtask.provider,
                        answer_md="", started_at=now, finished_at=now, status="needs_user_action",
                    ))
                    db_subtask = await session.get(Subtask, subtask.id)
                    if db_subtask is not None:
                        db_subtask.status = "failed"
                    db_job.subtasks_done = index
                    runs.append({"provider": subtask.provider, "status": "needs_user_action", "elapsed_ms": 0})
                    db_job.provider_runs_json = json.dumps(runs)
                    db_job.updated_at = utc_now()
                    session.add(JobEvent(
                        job_id=job_id,
                        status="researching",
                        event_type="progress",
                        message=f"Đã xử lý {index}/{db_job.subtasks_total} chatbot ({subtask.provider}: needs_user_action).",
                        subtasks_total=db_job.subtasks_total,
                        subtasks_done=index,
                    ))
                    await session.commit()
                continue
            except Exception as exc:
                logger.error("subtask_unexpected_error", provider=subtask.provider, error=str(exc))
                run_statuses.append("error")
                run_id = f"{job_id}:{subtask.provider}:run"
                now = utc_now()
                await _emit_subtask_step(
                    step_name="failed",
                    step_message=f"{subtask.provider} gặp lỗi bất ngờ: {str(exc)}",
                    step_data={
                        "status": "error",
                        "provider": subtask.provider,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                async with SessionLocal() as session:
                    db_job = await session.get(Job, job_id)
                    if db_job is None or db_job.status in TERMINAL_STATUSES:
                        return
                    session.add(ProviderRun(
                        id=run_id, subtask_id=subtask.id, provider=subtask.provider,
                        answer_md="", started_at=now, finished_at=now, status="error",
                    ))
                    db_subtask = await session.get(Subtask, subtask.id)
                    if db_subtask is not None:
                        db_subtask.status = "failed"
                    db_job.subtasks_done = index
                    runs.append({"provider": subtask.provider, "status": "error", "elapsed_ms": 0})
                    db_job.provider_runs_json = json.dumps(runs)
                    db_job.updated_at = utc_now()
                    session.add(JobEvent(
                        job_id=job_id,
                        status="researching",
                        event_type="progress",
                        message=f"Đã xử lý {index}/{db_job.subtasks_total} chatbot ({subtask.provider}: error).",
                        subtasks_total=db_job.subtasks_total,
                        subtasks_done=index,
                    ))
                    await session.commit()
                continue

            elapsed_ms = int((result.finished_at - result.started_at).total_seconds() * 1000)
            run_statuses.append(result.status)

            if result.status == "ok":
                answer_preview = result.answer_markdown.strip()
                if len(answer_preview) > 300:
                    answer_preview = answer_preview[:300] + "..."
                await _emit_subtask_step(
                    step_name="response_valid",
                    step_message=f"{subtask.provider} đã trả về phản hồi hợp lệ.",
                    step_data={
                        "status": "ok",
                        "provider": subtask.provider,
                        "response_length": len(result.answer_markdown),
                        "response_preview": answer_preview,
                        "response_markdown": result.answer_markdown,
                        "sources_count": len(result.sources),
                        "sources": [{"url": str(s.url), "title": s.title} for s in result.sources],
                        "conversation_url": str(result.conversation_url) if result.conversation_url else None,
                        "elapsed_ms": elapsed_ms,
                    },
                )
            elif result.status == "partial":
                answer_preview = result.answer_markdown.strip()
                if len(answer_preview) > 300:
                    answer_preview = answer_preview[:300] + "..."
                await _emit_subtask_step(
                    step_name="response_partial",
                    step_message=f"{subtask.provider} trả về kết quả một phần: {result.error or 'chưa hoàn tất'}",
                    step_data={
                        "status": "partial",
                        "provider": subtask.provider,
                        "error": result.error,
                        "response_length": len(result.answer_markdown),
                        "response_preview": answer_preview,
                        "response_markdown": result.answer_markdown,
                        "sources_count": len(result.sources),
                        "elapsed_ms": elapsed_ms,
                    },
                )
            else:
                await _emit_subtask_step(
                    step_name="failed",
                    step_message=f"{subtask.provider} thất bại: {result.error or result.status}",
                    step_data={
                        "status": result.status,
                        "provider": subtask.provider,
                        "error": result.error or f"Provider returned status {result.status}",
                        "artifact_paths": result.artifact_paths,
                        "elapsed_ms": elapsed_ms,
                    },
                )

            if result.status not in PROVIDER_RESULT_FAILURE_STATUSES and result.answer_markdown.strip():
                answers.append(f"## {subtask.provider.title()} response\n\n{result.answer_markdown.strip()}")
            run_id = f"{job_id}:{subtask.provider}:run"
            async with SessionLocal() as session:
                db_job = await session.get(Job, job_id)
                if db_job is None or db_job.status in TERMINAL_STATUSES:
                    return
                provider_run = ProviderRun(
                    id=run_id,
                    subtask_id=subtask.id,
                    provider=subtask.provider,
                    answer_md=result.answer_markdown,
                    conversation_url=str(result.conversation_url) if result.conversation_url else None,
                    started_at=result.started_at,
                    finished_at=result.finished_at,
                    status=result.status,
                    artifact_paths_json=json.dumps(result.artifact_paths),
                )
                session.add(provider_run)
                run_sources: list[dict[str, str]] = []
                for source_index, source in enumerate(result.sources, start=1):
                    source_public_id = f"S{len(sources) + len(run_sources) + 1}"
                    db_source = Source(
                        id=f"{job_id}:{source_public_id}", run_id=run_id, url=str(source.url),
                        title=source.title, snippet=source.snippet,
                    )
                    session.add(db_source)
                    source_data = {"id": source_public_id, "url": db_source.url, "title": db_source.title or ""}
                    run_sources.append(source_data)
                    sources.append(source_data)
                db_subtask = await session.get(Subtask, subtask.id)
                if db_subtask is not None:
                    db_subtask.status = "completed" if result.status == "ok" else "failed"
                db_job.subtasks_done = index
                session.add(JobEvent(
                    job_id=job_id,
                    status="researching",
                    event_type="progress",
                    message=f"Đã hoàn thành {index}/{db_job.subtasks_total} chatbot ({subtask.provider}: {result.status}).",
                    subtasks_total=db_job.subtasks_total,
                    subtasks_done=index,
                ))
                db_job.sources_json = json.dumps(sources)
                runs.append({"provider": subtask.provider, "status": result.status, "elapsed_ms": elapsed_ms})
                db_job.claims_json = json.dumps(claims)
                db_job.provider_runs_json = json.dumps(runs)
                db_job.updated_at = utc_now()
                await session.commit()

        for phase in ("extracting", "verifying", "synthesizing"):
            if cancel_event.is_set():
                await _set_status(job_id, "cancelled")
                return
            await _set_status(job_id, phase)
            await asyncio.sleep(0.01)

        if cancel_event.is_set():
            await _set_status(job_id, "cancelled")
            return

        ok_count = sum(1 for status in run_statuses if status == "ok")
        if ok_count == len(run_statuses) and run_statuses:
            final_status = "completed"
        elif ok_count > 0:
            final_status = "partial"
        elif any(status == "needs_user_action" for status in run_statuses):
            final_status = "needs_user_action"
        else:
            final_status = "failed"

        report = "# Research response\n\n"
        if answers:
            report += "\n\n".join(answers)
        else:
            report += "No provider returned a usable answer.\n"
        if sources:
            report += "\n\n## Sources\n\n"
            report += "\n".join(f"- [{source['id']}] [{source['title'] or source['url']}]({source['url']})" for source in sources)
        failed_runs = [run for run in runs if run.get("status") != "ok"]
        if failed_runs:
            report += "\n\n## Provider issues\n\n"
            report += "\n".join(f"- {run['provider']}: {run['status']}" for run in failed_runs)
        report += "\n\nThe provider response is shown as returned; claims have not been independently verified.\n"
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status in TERMINAL_STATUSES or cancel_event.is_set():
                if job is not None and job.status not in TERMINAL_STATUSES and cancel_event.is_set():
                    job.status = "cancelled"
                    job.finished_at = utc_now()
                    job.updated_at = utc_now()
                    session.add(JobEvent(
                        job_id=job_id,
                        status="cancelled",
                        event_type="progress",
                        message="Job đã bị hủy.",
                        subtasks_total=job.subtasks_total,
                        subtasks_done=job.subtasks_done,
                    ))
                    await session.commit()
                return
            session.add(Report(id=job_id, job_id=job_id, markdown=report))
            job.report_markdown = report
            job.disagreements_json = json.dumps([])
            job.status = final_status
            if final_status == "failed":
                job.error = "All provider runs failed."
            elif final_status == "needs_user_action":
                job.error = "Providers require manual login/CAPTCHA completion. Check data/artifacts/."
            elif final_status == "partial":
                job.error = "Some provider runs did not complete."
            job.finished_at = utc_now()
            job.updated_at = utc_now()
            session.add(JobEvent(
                job_id=job_id,
                status=final_status,
                event_type="progress",
                message=f"Quá trình nghiên cứu hoàn tất với trạng thái: {final_status}.",
                subtasks_total=job.subtasks_total,
                subtasks_done=job.subtasks_done,
            ))
            await session.commit()
    except AdapterNeedsUserAction as exc:
        logger.warning("research_job_needs_user_action", job_id=job_id, reason=str(exc))
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is not None and job.status not in TERMINAL_STATUSES:
                job.status = "needs_user_action"
                job.error = str(exc)
                job.finished_at = utc_now()
                job.updated_at = utc_now()
                session.add(JobEvent(
                    job_id=job_id,
                    status="needs_user_action",
                    event_type="progress",
                    message=f"Cần can thiệp người dùng: {str(exc)}",
                    subtasks_total=job.subtasks_total,
                    subtasks_done=job.subtasks_done,
                ))
                await session.commit()

    except Exception as exc:
        logger.exception("research_job_failed", job_id=job_id, error_type=type(exc).__name__)
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is not None and job.status not in TERMINAL_STATUSES:
                job.status = "failed"
                job.error = "The research worker encountered an internal error."
                job.finished_at = utc_now()
                job.updated_at = utc_now()
                session.add(JobEvent(job_id=job_id, status="failed", subtasks_total=job.subtasks_total, subtasks_done=job.subtasks_done))
                await session.commit()


async def worker_loop(queue: object) -> None:
    while True:
        job_id = await queue.get()
        event = queue.cancel_events.get(job_id)
        if event is None:
            event = asyncio.Event()
        try:
            await run_pipeline(job_id, event)
        finally:
            queue.done(job_id)
