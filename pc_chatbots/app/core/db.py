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
engine = create_async_engine(settings.db_url, connect_args={"check_same_thread": False})
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


from sqlalchemy import text


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

        await connection.run_sync(_migrate_jobevent)


async def close_db() -> None:
    await engine.dispose()
