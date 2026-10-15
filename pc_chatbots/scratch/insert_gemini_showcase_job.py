import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

from app.core.models import Job, JobEvent
from app.core.db import SessionLocal


async def main():
    with open("scratch/gemini_extracted_markdown.md", "r", encoding="utf-8") as f:
        markdown_content = f.read()

    job_id = f"job-gemini-showcase-{uuid.uuid4().hex[:8]}"
    query_text = (
        "Generate a comprehensive showcase of all kinds of markdown components supported by Gemini "
        "(H1-H4 headings, bold, italic, blockquotes, nested lists, task checklists, rich tables, "
        "code blocks with syntax highlighting for Python/TypeScript/SQL, LaTeX math formulas, callout alerts)."
    )

    now = datetime.now(timezone.utc)
    config = {
        "depth": "deep",
        "providers": ["gemini"],
        "provider_options": {
            "gemini": {
                "model_id": "gemini-3.8-flash",
                "thinking_level_id": "medium",
                "mode_id": "standard"
            }
        }
    }

    job = Job(
        id=job_id,
        query=query_text,
        title="Gemini Markdown Components Showcase (3.8 Flash + Medium)",
        status="completed",
        config_json=json.dumps(config),
        created_at=now,
        updated_at=now,
        finished_at=now,
        report_markdown=markdown_content,
        subtasks_total=1,
        subtasks_done=1,
        job_type="research",
        lead_provider="gemini",
        orchestrator_provider="gemini",
    )

    events = [
        JobEvent(
            job_id=job_id,
            status="completed",
            event_type="progress",
            step="provider_start",
            provider="gemini",
            message="Bắt đầu nghiên cứu với gemini (Model: 3.8 Flash, Cấp độ tư duy: Trung bình)...",
            created_at=now,
        ),
        JobEvent(
            job_id=job_id,
            status="completed",
            event_type="thinking",
            step="thinking_progress",
            provider="gemini",
            message="gemini đang sinh câu trả lời: Đang lấy câu trả lời trực tiếp...",
            created_at=now,
        ),
        JobEvent(
            job_id=job_id,
            status="completed",
            event_type="progress",
            step="completed",
            provider="gemini",
            message="Quá trình tạo mẫu Markdown toàn diện hoàn tất.",
            created_at=now,
        ),
    ]

    async with SessionLocal() as session:
        session.add(job)
        for ev in events:
            session.add(ev)
        await session.commit()

    print(f"Successfully inserted showcase job: {job_id}")


if __name__ == "__main__":
    asyncio.run(main())
