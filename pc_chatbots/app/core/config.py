from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    router_base_url: str
    router_api_key: str
    router_model_planner: str
    router_model_extractor: str
    router_model_lead: str
    perplexity_api_key: str | None
    perplexity_api_base_url: str
    perplexity_api_preset: str
    research_adapter_mode: str
    browser_profile_dir: Path
    browser_headless: bool
    browser_channel: str
    artifact_dir: Path
    db_url: str
    max_questions_per_hour: int
    default_timeout_min: int
    adapter_stable_seconds: float
    adapter_poll_interval_s: float
    min_delay_between_questions_s: int
    max_delay_between_questions_s: int
    work_mode: str
    max_concurrent_browsers: int
    browser_profiles_base_dir: Path

    @property
    def adapter_default_timeout_s(self) -> int:
        """Derived default per-provider question timeout in seconds."""
        return self.default_timeout_min * 60

    @classmethod
    def from_env(cls) -> Settings:
        _read_dotenv()
        profile_dir = Path(os.getenv("BROWSER_PROFILE_DIR", "./data/profiles/main"))
        return cls(
            api_key=os.getenv("API_KEY", "changeme"),
            router_base_url=os.getenv("ROUTER_BASE_URL", "http://localhost:20128/v1"),
            router_api_key=os.getenv("ROUTER_API_KEY", "changeme"),
            router_model_planner=os.getenv("ROUTER_MODEL_PLANNER", "planner"),
            router_model_extractor=os.getenv("ROUTER_MODEL_EXTRACTOR", "extractor"),
            router_model_lead=os.getenv("ROUTER_MODEL_LEAD", "lead"),
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY") or None,
            perplexity_api_base_url=os.getenv("PERPLEXITY_API_BASE_URL", "https://api.perplexity.ai"),
            perplexity_api_preset=os.getenv("PERPLEXITY_API_PRESET", "fast"),
            research_adapter_mode=os.getenv("RESEARCH_ADAPTER_MODE", "official_api"),
            browser_profile_dir=profile_dir,
            browser_headless=_env_bool("BROWSER_HEADLESS", default=False),
            browser_channel=os.getenv("BROWSER_CHANNEL", "chrome"),
            artifact_dir=Path(os.getenv("ARTIFACT_DIR", "./data/artifacts")),
            db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///./data/app.db"),
            max_questions_per_hour=int(os.getenv("MAX_QUESTIONS_PER_HOUR", "20")),
            default_timeout_min=int(os.getenv("DEFAULT_TIMEOUT_MIN", "20")),
            adapter_stable_seconds=float(os.getenv("ADAPTER_STABLE_SECONDS", "8")),
            adapter_poll_interval_s=float(os.getenv("ADAPTER_POLL_INTERVAL_S", "3")),
            min_delay_between_questions_s=int(os.getenv("MIN_DELAY_BETWEEN_QUESTIONS_S", "5")),
            max_delay_between_questions_s=int(os.getenv("MAX_DELAY_BETWEEN_QUESTIONS_S", "15")),
            work_mode=os.getenv("WORK_MODE", "sync").strip().lower(),
            max_concurrent_browsers=int(os.getenv("MAX_CONCURRENT_BROWSERS", "3")),
            browser_profiles_base_dir=profile_dir.parent if profile_dir.parent.name == "profiles" else Path("./data/profiles"),
        )


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


settings = Settings.from_env()


def get_provider_profile_dir(provider: str, mode: str | None = None) -> Path:
    """Resolve the profile path based on WORK_MODE.

    - sync: ./data/profiles/main (retains existing single profile)
    - async: ./data/profiles/<provider> (e.g. ./data/profiles/gemini)
    """
    effective_mode = (mode or settings.work_mode).strip().lower()
    if effective_mode == "async":
        return settings.browser_profiles_base_dir / provider
    return settings.browser_profile_dir
