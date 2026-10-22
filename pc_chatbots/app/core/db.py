from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings


def _ensure_sqlite_parent(db_url: str) -> None:
    prefix = "sqlite+aiosqlite:///"
    if db_url.startswith(prefix):
        raw_path = db_url.removeprefix(prefix)
        if raw_path and raw_path != ":memory:":
            Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent(settings.db_url)
engine = create_async_engine(settings.db_url, connect_args={"check_same_thread": False, "timeout": 15})
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from sqlalchemy import event, text

@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()



async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

        def _migrate_jobevent(sync_conn) -> None:
            result = sync_conn.execute(text("PRAGMA table_info(jobevent)"))
            cols = [row[1] for row in result.fetchall()]
            new_cols = {
                "event_type": "VARCHAR DEFAULT 'progress'",
                "provider": "VARCHAR",
                "step": "VARCHAR",
                "message": "VARCHAR",
                "data_json": "TEXT",
            }
            for col_name, col_type in new_cols.items():
                if col_name not in cols:
                    sync_conn.execute(text(f"ALTER TABLE jobevent ADD COLUMN {col_name} {col_type}"))

        def _migrate_job(sync_conn) -> None:
            result = sync_conn.execute(text("PRAGMA table_info(job)"))
            cols = [row[1] for row in result.fetchall()]
            new_cols = {
                "title": "VARCHAR",
                "pinned": "BOOLEAN DEFAULT 0",
                "job_type": "VARCHAR DEFAULT 'research'",
                "orchestrator_provider": "VARCHAR",
                "orchestrator_config_json": "TEXT",
                "lead_provider": "VARCHAR",
                "lead_config_json": "TEXT",
                "tone": "VARCHAR",
                "orchestrator_dispatch_json": "TEXT",
                "orchestrator_conversation_url": "VARCHAR",
                "lead_conversation_url": "VARCHAR",
                "provider_conversations_json": "TEXT DEFAULT '{}'",
                "summarization_provider": "VARCHAR",
                "summarization_config_json": "TEXT",
                "context_summary": "TEXT",
                "parent_job_id": "VARCHAR",
                "conversation_id": "VARCHAR",
                "enable_fact_check": "BOOLEAN DEFAULT 0",
                "fact_check_provider": "VARCHAR",
                "fact_check_config_json": "TEXT",
                "fact_check_results_json": "TEXT",
                "report_format": "VARCHAR DEFAULT 'narrative'",
                "report_matrix_json": "TEXT",
                "enable_debate": "BOOLEAN DEFAULT 0",
                "debate_provider": "VARCHAR",
                "debate_defender_provider": "VARCHAR",
                "debate_config_json": "TEXT",
                "max_debate_rounds": "INTEGER DEFAULT 2",
                "debate_transcript_json": "TEXT",
                "enable_consensus": "BOOLEAN DEFAULT 0",
                "consensus_providers_json": "TEXT",
                "consensus_threshold": "FLOAT DEFAULT 0.8",
                "max_consensus_rounds": "INTEGER DEFAULT 3",
                "consensus_scores_json": "TEXT",
            }
            for col_name, col_type in new_cols.items():
                if col_name not in cols:
                    sync_conn.execute(text(f"ALTER TABLE job ADD COLUMN {col_name} {col_type}"))

        def _migrate_source(sync_conn) -> None:
            result = sync_conn.execute(text("PRAGMA table_info(source)"))
            cols = [row[1] for row in result.fetchall()]
            new_cols = {
                "job_id": "VARCHAR",
                "provider": "VARCHAR",
                "created_at": "TIMESTAMP",
            }
            for col_name, col_type in new_cols.items():
                if col_name not in cols:
                    sync_conn.execute(text(f"ALTER TABLE source ADD COLUMN {col_name} {col_type}"))

        await connection.run_sync(_migrate_jobevent)
        await connection.run_sync(_migrate_job)
        await connection.run_sync(_migrate_source)


async def close_db() -> None:
    await engine.dispose()
