from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SELECTORS_PATH = Path(__file__).resolve().parent / "selectors.yaml"

_REQUIRED_PROVIDER_KEYS = (
    "new_chat_url",
    "question_input",
    "submit",
    "answer_container",
    "source_links",
)


@lru_cache(maxsize=1)
def load_selectors() -> dict[str, Any]:
    """Load and validate selectors.yaml. Cached after first successful load."""
    if not SELECTORS_PATH.is_file():
        raise FileNotFoundError(f"selectors file not found: {SELECTORS_PATH}")
    raw = yaml.safe_load(SELECTORS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("selectors.yaml must parse to a mapping")
    _validate(raw)
    return raw


def _validate(raw: dict[str, Any]) -> None:
    providers = raw.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError("selectors.yaml must contain a non-empty 'providers' mapping")
    for name, cfg in providers.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"providers.{name} must be a mapping")
        missing = [key for key in _REQUIRED_PROVIDER_KEYS if key not in cfg]
        if missing:
            raise ValueError(f"providers.{name} missing required keys: {', '.join(missing)}")
    if "blocking" not in raw:
        raise ValueError("selectors.yaml must contain a 'blocking' section")
    if "completion" not in raw:
        raise ValueError("selectors.yaml must contain a 'completion' section")


def get(raw: dict[str, Any], *path: str, default: Any = None) -> Any:
    """Walk nested dicts by key path; return default when any segment is missing."""
    node: Any = raw
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def provider_selectors(raw: dict[str, Any], provider: str) -> dict[str, Any]:
    """Return the selector config for one provider or raise KeyError."""
    providers = raw.get("providers") or {}
    if provider not in providers:
        raise KeyError(f"no selectors configured for provider: {provider}")
    return providers[provider]
