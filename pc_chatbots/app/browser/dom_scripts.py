from __future__ import annotations

import functools
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"


@functools.lru_cache(maxsize=1)
def get_thinking_and_citations_script() -> str:
    """Loads and caches the DOM extraction script for thinking steps and citations."""
    script_path = SCRIPTS_DIR / "thinking_and_citations.js"
    try:
        if script_path.is_file():
            return script_path.read_text(encoding="utf-8")
        logger.error("dom_script_missing", path=str(script_path))
    except Exception as exc:
        logger.error("dom_script_load_error", path=str(script_path), error=str(exc))

    # Minimal fallback in case file is somehow missing
    return """
    (provider) => {
        return { is_thinking: false, thinking_text: "", thinking_steps: [], citations: [] };
    }
    """


# Module-level constant evaluated on import for backward compatibility
DOM_SCAN_THINKING_AND_CITATIONS: str = get_thinking_and_citations_script()
