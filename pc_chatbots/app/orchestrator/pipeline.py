from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

import structlog

from app.adapters.base import ProviderAdapter
from app.adapters.browser_base import ProviderNeedsUserAction
from app.adapters.fake import FakeAdapter
from app.browser.session import BrowserSessionManager
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
from sqlmodel import select
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
        results_lock = asyncio.Lock()
        total_subtasks = len(subtasks)

        async def _run_subtask_core(subtask: Subtask, index: int) -> None:
            if cancel_event.is_set():
                return

            async def _emit_subtask_step(
                step_name: str,
                step_message: str,
                step_data: dict[str, Any] | None = None,
                event_type: str = "step",
            ) -> None:
                if cancel_event.is_set():
                    raise asyncio.CancelledError("Job cancelled by user")
                if step_name == "thinking_progress":
                    event_type = "thinking"

                async with SessionLocal() as s:
                    db_j = await s.get(Job, job_id)
                    if db_j is None or db_j.status == "cancelled":
                        raise asyncio.CancelledError("Job cancelled by user")
                    if db_j.status in TERMINAL_STATUSES:
                        return

                    # Live citation discovery and DB persistence
                    if step_name == "thinking_progress" and step_data and step_data.get("citations"):
                        try:
                            live_citations = step_data.get("citations", [])
                            async with results_lock:
                                cur_sources = json.loads(db_j.sources_json) if db_j.sources_json else []
                                known_urls = {str(cs.get("url")) for cs in cur_sources}
                                new_source_added = False
                                for c in live_citations:
                                    c_url = str(c.get("url") or "")
                                    if c_url and c_url not in known_urls:
                                        known_urls.add(c_url)
                                        s_id = f"{job_id}:S{len(sources) + 1}"
                                        s_item = {
                                            "id": s_id,
                                            "url": c_url,
                                            "title": c.get("title") or "",
                                            "provider": subtask.provider,
                                        }
                                        cur_sources.append(s_item)
                                        sources.append(s_item)
                                        s.add(Source(
                                            id=s_id,
                                            run_id=f"{job_id}:{subtask.provider}:run",
                                            job_id=job_id,
                                            provider=subtask.provider,
                                            url=c_url,
                                            title=c.get("title") or None,
                                        ))
                                        new_source_added = True
                                if new_source_added:
                                    db_j.sources_json = json.dumps(cur_sources)
                                    db_j.updated_at = utc_now()
                        except Exception as c_err:
                            logger.debug("live_citation_persist_skipped", error=str(c_err))

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
                step_message=f"Bắt đầu nghiên cứu với {subtask.provider} ({index}/{total_subtasks})...",
                step_data={"provider": subtask.provider, "index": index, "total": total_subtasks},
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
                async with results_lock:
                    run_statuses.append("needs_user_action")
                    runs.append({"provider": subtask.provider, "status": "needs_user_action", "error": str(exc), "elapsed_ms": 0})
                    done_count = len(runs)
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
                        db_job.subtasks_done = done_count
                        db_job.provider_runs_json = json.dumps(runs)
                        db_job.updated_at = utc_now()
                        session.add(JobEvent(
                            job_id=job_id,
                            status="researching",
                            event_type="progress",
                            message=f"Đã xử lý {done_count}/{db_job.subtasks_total} chatbot ({subtask.provider}: needs_user_action).",
                            subtasks_total=db_job.subtasks_total,
                            subtasks_done=done_count,
                        ))
                        await session.commit()
                return
            except Exception as exc:
                logger.error("subtask_unexpected_error", provider=subtask.provider, error=str(exc))
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
                async with results_lock:
                    run_statuses.append("error")
                    runs.append({"provider": subtask.provider, "status": "error", "error": str(exc), "elapsed_ms": 0})
                    done_count = len(runs)
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
                        db_job.subtasks_done = done_count
                        db_job.provider_runs_json = json.dumps(runs)
                        db_job.updated_at = utc_now()
                        session.add(JobEvent(
                            job_id=job_id,
                            status="researching",
                            event_type="progress",
                            message=f"Đã xử lý {done_count}/{db_job.subtasks_total} chatbot ({subtask.provider}: error).",
                            subtasks_total=db_job.subtasks_total,
                            subtasks_done=done_count,
                        ))
                        await session.commit()
                return

            elapsed_ms = int((result.finished_at - result.started_at).total_seconds() * 1000)

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

            run_id = f"{job_id}:{subtask.provider}:run"
            async with results_lock:
                run_statuses.append(result.status)
                if result.status not in PROVIDER_RESULT_FAILURE_STATUSES and result.answer_markdown.strip():
                    answers.append(f"## {subtask.provider.title()} response\n\n{result.answer_markdown.strip()}")
                runs.append({
                    "provider": subtask.provider,
                    "status": result.status,
                    "elapsed_ms": elapsed_ms,
                    "answer_markdown": result.answer_markdown.strip() if result.answer_markdown else "",
                    "error": result.error,
                })
                done_count = len(runs)

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
                        source_url_str = str(source.url)
                        # Check if already added during live thinking stream
                        existing = next((s for s in sources if s.get("url") == source_url_str), None)
                        if existing:
                            continue
                        source_public_id = f"S{len(sources) + 1}"
                        db_source = Source(
                            id=f"{job_id}:{source_public_id}",
                            run_id=run_id,
                            job_id=job_id,
                            provider=subtask.provider,
                            url=source_url_str,
                            title=source.title,
                            snippet=source.snippet,
                        )
                        session.add(db_source)
                        source_data = {"id": source_public_id, "url": db_source.url, "title": db_source.title or "", "provider": subtask.provider}
                        run_sources.append(source_data)
                        sources.append(source_data)
                    db_subtask = await session.get(Subtask, subtask.id)
                    if db_subtask is not None:
                        db_subtask.status = "completed" if result.status == "ok" else "failed"
                    db_job.subtasks_done = done_count
                    session.add(JobEvent(
                        job_id=job_id,
                        status="researching",
                        event_type="progress",
                        message=f"Đã hoàn thành {done_count}/{db_job.subtasks_total} chatbot ({subtask.provider}: {result.status}).",
                        subtasks_total=db_job.subtasks_total,
                        subtasks_done=done_count,
                    ))
                    db_job.sources_json = json.dumps(sources)
                    db_job.claims_json = json.dumps(claims)
                    db_job.provider_runs_json = json.dumps(runs)
                    db_job.updated_at = utc_now()
                    await session.commit()

        async def _execute_subtask(subtask: Subtask, index: int) -> None:
            if cancel_event.is_set():
                return
            try:
                await _run_subtask_core(subtask, index)
            except asyncio.CancelledError:
                logger.info("subtask_cancelled_gracefully", provider=subtask.provider, job_id=job_id)
                return
            finally:
                if settings.work_mode == "async":
                    await BrowserSessionManager.close_session(subtask.provider)

        try:
            if settings.work_mode == "async":
                logger.info("running_pipeline_async", job_id=job_id, max_concurrent=settings.max_concurrent_browsers)
                semaphore = asyncio.Semaphore(max(1, settings.max_concurrent_browsers))

                async def _worker(st: Subtask, idx: int) -> None:
                    async with semaphore:
                        if cancel_event.is_set():
                            return
                        await _execute_subtask(st, idx)

                await asyncio.gather(*[_worker(st, idx) for idx, st in enumerate(subtasks, start=1)])
            else:
                logger.info("running_pipeline_sync", job_id=job_id)
                for idx, st in enumerate(subtasks, start=1):
                    if cancel_event.is_set():
                        await _set_status(job_id, "cancelled")
                        return
                    await _execute_subtask(st, idx)
        finally:
            await BrowserSessionManager.close_all()

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
            report += "\n".join(f"- [{source['title'] or source['url']}]({source['url']})" for source in sources)
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


async def retry_provider_subtask(job_id: str, provider: str) -> None:
    """Re-run a subtask for a single provider on an existing job after manual login."""
    from app.browser.manual import ManualBrowserManager

    prov = provider.lower().strip()
    # 1. Close manual browser if open so that automated profile lock is released
    await ManualBrowserManager.close_browser(prov)

    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            logger.warning("retry_provider_job_not_found", job_id=job_id, provider=prov)
            return

        # Load or create subtask
        subtask_stmt = select(Subtask).where(Subtask.job_id == job_id, Subtask.provider == prov)
        subtask = (await session.exec(subtask_stmt)).first()
        if subtask is None:
            subtask = Subtask(
                id=f"{job_id}:{prov}",
                job_id=job_id,
                branch=f"Research branch for {prov}",
                provider=prov,
                prompt=job.query,
                status="queued",
            )
            session.add(subtask)
        else:
            subtask.status = "running"
            subtask.attempt += 1

        job.status = "researching"
        job.updated_at = utc_now()
        session.add(JobEvent(
            job_id=job_id,
            status="researching",
            event_type="progress",
            provider=prov,
            step="retry_start",
            message=f"Đang tiếp tục nghiên cứu với {prov} sau khi hoàn tất đăng nhập...",
            subtasks_total=job.subtasks_total,
            subtasks_done=job.subtasks_done,
        ))
        await session.commit()

        # Parse request depth / max_minutes
        try:
            req_data = json.loads(job.config_json)
            max_minutes = int(req_data.get("max_minutes", 5))
            depth = str(req_data.get("depth", "deep"))
        except Exception:
            max_minutes = 5
            depth = "deep"

    async def _emit_step(
        step_name: str,
        step_message: str,
        step_data: dict[str, Any] | None = None,
        event_type: str = "step",
    ) -> None:
        if step_name == "thinking_progress":
            event_type = "thinking"
        async with SessionLocal() as s:
            db_j = await s.get(Job, job_id)
            if db_j is None:
                return
            s.add(JobEvent(
                job_id=job_id,
                status="researching",
                event_type=event_type,
                provider=prov,
                step=step_name,
                message=step_message,
                subtasks_total=db_j.subtasks_total,
                subtasks_done=db_j.subtasks_done,
                data_json=json.dumps(step_data, ensure_ascii=False) if step_data is not None else None,
            ))
            await s.commit()

    adapter = create_adapter(prov)
    ask_params = inspect.signature(adapter.ask).parameters
    ask_kwargs: dict[str, Any] = {"timeout_s": max_minutes * 60, "mode": depth}
    if "on_step" in ask_params or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in ask_params.values()):
        ask_kwargs["on_step"] = _emit_step

    try:
        result = await adapter.ask(subtask.prompt, **ask_kwargs)
    except Exception as exc:
        logger.error("retry_subtask_failed", provider=prov, error=str(exc))
        run_id = f"{job_id}:{prov}:run"
        now = utc_now()
        await _emit_step(
            step_name="failed",
            step_message=f"{prov} gặp lỗi khi thử lại: {str(exc)}",
            step_data={"status": "error", "provider": prov, "error": str(exc)},
        )
        async with SessionLocal() as session:
            db_job = await session.get(Job, job_id)
            if db_job:
                runs = json.loads(db_job.provider_runs_json) if db_job.provider_runs_json else []
                updated = False
                for r in runs:
                    if r.get("provider") == prov:
                        r["status"] = "error"
                        r["error"] = str(exc)
                        updated = True
                        break
                if not updated:
                    runs.append({"provider": prov, "status": "error", "error": str(exc), "elapsed_ms": 0})
                db_job.provider_runs_json = json.dumps(runs)
                db_job.updated_at = utc_now()
                await session.commit()
        return

    elapsed_ms = int((result.finished_at - result.started_at).total_seconds() * 1000)
    run_id = f"{job_id}:{prov}:run"

    if result.status == "ok":
        answer_preview = result.answer_markdown.strip()
        if len(answer_preview) > 300:
            answer_preview = answer_preview[:300] + "..."
        await _emit_step(
            step_name="response_valid",
            step_message=f"{prov} đã trả về phản hồi hợp lệ sau khi đăng nhập.",
            step_data={
                "status": "ok",
                "provider": prov,
                "response_length": len(result.answer_markdown),
                "response_preview": answer_preview,
                "response_markdown": result.answer_markdown,
                "sources_count": len(result.sources),
                "sources": [{"url": str(s.url), "title": s.title} for s in result.sources],
                "conversation_url": str(result.conversation_url) if result.conversation_url else None,
                "elapsed_ms": elapsed_ms,
            },
        )
    else:
        await _emit_step(
            step_name="failed" if result.status != "needs_user_action" else "blocked",
            step_message=f"{prov}: {result.error or result.status}",
            step_data={
                "status": result.status,
                "provider": prov,
                "error": result.error or f"Status: {result.status}",
                "needs_user_action": result.status == "needs_user_action",
            },
        )

    async with SessionLocal() as session:
        db_job = await session.get(Job, job_id)
        if not db_job:
            return

        db_run = await session.get(ProviderRun, run_id)
        if db_run is None:
            db_run = ProviderRun(
                id=run_id,
                subtask_id=subtask.id,
                provider=prov,
                answer_md=result.answer_markdown,
                conversation_url=str(result.conversation_url) if result.conversation_url else None,
                started_at=result.started_at,
                finished_at=result.finished_at,
                status=result.status,
                artifact_paths_json=json.dumps(result.artifact_paths),
            )
            session.add(db_run)
        else:
            db_run.answer_md = result.answer_markdown
            db_run.conversation_url = str(result.conversation_url) if result.conversation_url else None
            db_run.finished_at = result.finished_at
            db_run.status = result.status
            db_run.artifact_paths_json = json.dumps(result.artifact_paths)

        db_sub = await session.get(Subtask, subtask.id)
        if db_sub:
            db_sub.status = "completed" if result.status == "ok" else "failed"

        sources = json.loads(db_job.sources_json) if db_job.sources_json else []
        known_urls = {str(s.get("url")) for s in sources}
        for s in result.sources:
            s_url = str(s.url)
            if s_url not in known_urls:
                known_urls.add(s_url)
                s_id = f"{job_id}:S{len(sources) + 1}"
                sources.append({"id": s_id, "url": s_url, "title": s.title or "", "provider": prov})
                session.add(Source(id=s_id, run_id=run_id, job_id=job_id, provider=prov, url=s_url, title=s.title or None))
        db_job.sources_json = json.dumps(sources)

        runs = json.loads(db_job.provider_runs_json) if db_job.provider_runs_json else []
        updated = False
        for r in runs:
            if r.get("provider") == prov:
                r["status"] = result.status
                r["elapsed_ms"] = elapsed_ms
                r["answer_markdown"] = result.answer_markdown.strip() if result.answer_markdown else ""
                r["error"] = result.error
                updated = True
                break
        if not updated:
            runs.append({
                "provider": prov,
                "status": result.status,
                "elapsed_ms": elapsed_ms,
                "answer_markdown": result.answer_markdown.strip() if result.answer_markdown else "",
                "error": result.error,
            })
        db_job.provider_runs_json = json.dumps(runs)

        answers: list[str] = []
        for r in runs:
            ans = r.get("answer_markdown", "").strip()
            if r.get("status") not in PROVIDER_RESULT_FAILURE_STATUSES and ans:
                answers.append(f"## {r['provider'].title()} response\n\n{ans}")

        report = "# Research response\n\n"
        if answers:
            report += "\n\n".join(answers)
        else:
            report += "No provider returned a usable answer.\n"
        if sources:
            report += "\n\n## Sources\n\n"
            report += "\n".join(f"- [{source['title'] or source['url']}]({source['url']})" for source in sources)
        failed_runs = [r for r in runs if r.get("status") != "ok"]
        if failed_runs:
            report += "\n\n## Provider issues\n\n"
            report += "\n".join(f"- {r['provider']}: {r['status']}" for r in failed_runs)
        report += "\n\nThe provider response is shown as returned; claims have not been independently verified.\n"

        db_job.report_markdown = report
        ok_count = sum(1 for r in runs if r.get("status") == "ok")
        if ok_count == len(runs) and runs:
            final_status = "completed"
        elif ok_count > 0:
            final_status = "partial"
        elif any(r.get("status") == "needs_user_action" for r in runs):
            final_status = "needs_user_action"
        else:
            final_status = "failed"
        db_job.status = final_status
        db_job.finished_at = utc_now()
        db_job.updated_at = utc_now()

        session.add(JobEvent(
            job_id=job_id,
            status=final_status,
            event_type="progress",
            message=f"Hoàn thành xử lý {prov} ({result.status}). Trạng thái phiên: {final_status}.",
            subtasks_total=db_job.subtasks_total,
            subtasks_done=len(runs),
        ))
        await session.commit()

