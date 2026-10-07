from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def _sanitize(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "-" for c in value).strip("-") or "run"


async def save_artifacts(
    page: Any,
    *,
    job_tag: str,
    provider: str,
    artifact_dir: Path | None = None,
) -> list[str]:
    """Save raw HTML and a full-page screenshot for the given page.

    Artifacts land under ``{artifact_dir}/{job_tag}/{provider}-<epoch>.{ext}``
    (defaults to ``ARTIFACT_DIR``). Returns the list of absolute paths written
    (empty if nothing could be saved). Never raises — artifact saving must not
    break an in-flight job.
    """
    root = artifact_dir or settings.artifact_dir
    base = root / _sanitize(job_tag) / _sanitize(provider)
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("artifact_dir_unavailable", dir=str(base), error=str(exc))
        return []

    stamp = f"{int(time.time())}"
    html_path = base / f"page-{stamp}.html"
    png_path = base / f"page-{stamp}.png"
    written: list[str] = []

    try:
        html = await page.content()
        html_path.write_text(html, encoding="utf-8", errors="replace")
        written.append(str(html_path))
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("artifact_html_save_failed", error=str(exc))

    try:
        await page.screenshot(path=str(png_path), full_page=True)
        written.append(str(png_path))
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("artifact_screenshot_save_failed", error=str(exc))

    logger.info("artifacts_saved", count=len(written), dir=str(base))
    return written


def artifact_dir_for(job_tag: str) -> Path:
    return settings.artifact_dir / _sanitize(job_tag)
