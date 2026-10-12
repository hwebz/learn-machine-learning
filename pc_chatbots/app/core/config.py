from __future__ import annotations

import json
import os
import winreg
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _read_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip("\"'")


SETTINGS_FILE = Path("./data/settings.json")


def detect_available_browsers() -> list[dict[str, Any]]:
    """Inspect the local machine (Windows) to find installed web browsers.

    Default browser rule:
    Edge if installed; otherwise the machine's default browser.
    """
    detected: list[dict[str, Any]] = []

    # 1. Determine machine default browser ProgId via Windows Registry
    prog_id = ""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice",
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
    except Exception:
        pass
    prog_id_lower = prog_id.lower()

    candidates = [
        {
            "id": "msedge",
            "name": "Microsoft Edge",
            "channel": "msedge",
            "paths": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            ],
            "executable_path": None,
        },
        {
            "id": "chrome",
            "name": "Google Chrome",
            "channel": "chrome",
            "paths": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ],
            "executable_path": None,
        },
        {
            "id": "brave",
            "name": "Brave Browser",
            "channel": "brave",
            "paths": [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ],
            "executable_path": None,
        },
    ]

    for item in candidates:
        found_path = None
        for p in item["paths"]:
            if Path(p).is_file():
                found_path = p
                break
        if found_path:
            is_machine_def = (
                ("edge" in prog_id_lower and item["id"] == "msedge")
                or ("chrome" in prog_id_lower and item["id"] == "chrome")
                or ("brave" in prog_id_lower and item["id"] == "brave")
            )
            detected.append({
                "id": item["id"],
                "name": item["name"],
                "channel": item["channel"],
                "path": found_path,
                "executable_path": found_path if item["id"] == "brave" else None,
                "is_machine_default": is_machine_def,
            })

    # Always provide Playwright bundled Chromium option
    detected.append({
        "id": "chromium",
        "name": "Playwright Chromium (Bundled)",
        "channel": "chromium",
        "path": "Playwright Bundled Chromium",
        "executable_path": None,
        "is_machine_default": False,
    })

    # Rule: Default is Edge if installed, otherwise machine default browser
    edge_installed = any(b["id"] == "msedge" for b in detected)
    for b in detected:
        if edge_installed:
            b["is_default"] = (b["id"] == "msedge")
        else:
            b["is_default"] = b["is_machine_default"]

    return detected


def _load_settings_file() -> dict[str, Any]:
    if not SETTINGS_FILE.is_file():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_settings_file(data: dict[str, Any]) -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"Failed to persist settings.json: {exc}")


@dataclass
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
    thinking_interval_check: float
    browser_executable: str | None = None
    headless_providers: dict[str, bool] = field(default_factory=dict)

    @property
    def adapter_default_timeout_s(self) -> int:
        """Derived default per-provider question timeout in seconds."""
        return self.default_timeout_min * 60

    @classmethod
    def from_env(cls) -> Settings:
        _read_dotenv()
        profile_dir = Path(os.getenv("BROWSER_PROFILE_DIR", "./data/profiles/main"))

        # Detect browsers for default selection
        browsers = detect_available_browsers()
        default_browser = "msedge"
        for b in browsers:
            if b.get("is_default"):
                default_browser = b["id"]
                break

        # Load file overrides if present
        saved = _load_settings_file()

        browser_channel = saved.get("browser", os.getenv("BROWSER_CHANNEL", default_browser))
        browser_executable = saved.get("browser_executable")
        if not browser_executable and browser_channel == "brave":
            # auto-resolve brave executable path if detected
            for b in browsers:
                if b["id"] == "brave":
                    browser_executable = b.get("executable_path")
                    break

        work_mode = saved.get("work_mode", os.getenv("WORK_MODE", "async")).strip().lower()
        max_concurrent = int(saved.get("max_concurrent_browsers", os.getenv("MAX_CONCURRENT_BROWSERS", "3")))
        headless_providers = saved.get("headless_providers", {})

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
            browser_channel=browser_channel,
            artifact_dir=Path(os.getenv("ARTIFACT_DIR", "./data/artifacts")),
            db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///./data/app.db"),
            max_questions_per_hour=int(os.getenv("MAX_QUESTIONS_PER_HOUR", "20")),
            default_timeout_min=int(os.getenv("DEFAULT_TIMEOUT_MIN", "20")),
            adapter_stable_seconds=float(os.getenv("ADAPTER_STABLE_SECONDS", "8")),
            adapter_poll_interval_s=float(os.getenv("ADAPTER_POLL_INTERVAL_S", "3")),
            min_delay_between_questions_s=int(os.getenv("MIN_DELAY_BETWEEN_QUESTIONS_S", "5")),
            max_delay_between_questions_s=int(os.getenv("MAX_DELAY_BETWEEN_QUESTIONS_S", "15")),
            work_mode=work_mode,
            max_concurrent_browsers=max_concurrent,
            browser_profiles_base_dir=profile_dir.parent if profile_dir.parent.name == "profiles" else Path("./data/profiles"),
            thinking_interval_check=_parse_interval(os.getenv("THINKING_INTERVAL_CHECK", "1s"), default=1.0),
            browser_executable=browser_executable,
            headless_providers=headless_providers,
        )


def _parse_interval(val: str | None, default: float = 1.0) -> float:
    if not val:
        return default
    v = val.strip().lower()
    if v.endswith("ms"):
        try:
            return float(v[:-2]) / 1000.0
        except ValueError:
            return default
    if v.endswith("s"):
        try:
            return float(v[:-1])
        except ValueError:
            return default
    try:
        return float(v)
    except ValueError:
        return default


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


def get_provider_headless(provider: str) -> bool:
    """Return whether a provider should run in headless mode.

    If configured in settings.headless_providers, returns that value;
    otherwise falls back to settings.browser_headless.
    """
    p = provider.lower()
    if p in settings.headless_providers:
        return bool(settings.headless_providers[p])
    return settings.browser_headless


def update_runtime_settings(
    *,
    browser: str | None = None,
    browser_executable: str | None = None,
    work_mode: str | None = None,
    max_concurrent_browsers: int | None = None,
    headless_providers: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Dynamically update runtime settings and persist to data/settings.json."""
    browsers = detect_available_browsers()

    if browser is not None:
        settings.browser_channel = browser
        if browser == "brave" and not browser_executable:
            for b in browsers:
                if b["id"] == "brave":
                    browser_executable = b.get("executable_path")
                    break
        settings.browser_executable = browser_executable

    if work_mode is not None:
        settings.work_mode = work_mode.strip().lower()

    if max_concurrent_browsers is not None:
        settings.max_concurrent_browsers = max(1, min(10, int(max_concurrent_browsers)))

    if headless_providers is not None:
        settings.headless_providers.update(headless_providers)

    # Persist
    payload = {
        "browser": settings.browser_channel,
        "browser_executable": settings.browser_executable,
        "work_mode": settings.work_mode,
        "max_concurrent_browsers": settings.max_concurrent_browsers,
        "headless_providers": settings.headless_providers,
    }
    _save_settings_file(payload)
    return payload

