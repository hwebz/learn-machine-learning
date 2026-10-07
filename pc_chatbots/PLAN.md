# PLAN.md — Local Multi-Chatbot Deep Research Orchestrator (V1)

## 0. Goal

Build a locally-run application that:

1. Exposes a local HTTP API (`POST /research`).
2. Uses an LLM router (**9router**, OpenAI-compatible, already running locally) to plan, extract, verify, and synthesize.
3. Uses browser automation (Playwright) to ask questions on **perplexity.ai** and **gemini.google.com** using an already logged-in, dedicated browser profile.
4. Returns a cited Markdown research report.

V1 scope: exactly two providers (Perplexity, Gemini). Nothing else.

## 1. Hard Constraints (Codex must follow)

- Python 3.12. Type hints everywhere. Async-first.
- Stack: FastAPI, Uvicorn, Playwright (Python), SQLModel/SQLAlchemy + SQLite, Pydantic v2, `openai` SDK (pointed at 9router), `tenacity`, `structlog`, `pytest`, `pytest-asyncio`, `pyyaml`.
- API binds to `127.0.0.1` only. All routes except `/health` require header `X-API-Key`.
- Do NOT implement: CAPTCHA solving, bot-detection evasion, rate-limit evasion, session-token extraction, or calling providers' private/internal endpoints.
- Do NOT use screen-coordinate automation. Use DOM locators only (`get_by_role`, aria-label, data-testid, text fallback).
- Never log cookies, API keys, or full prompts at INFO level.
- `data/` (profiles, artifacts, DB) must be in `.gitignore`.
- Every provider adapter must sit behind the same interface so it can be swapped for an official-API implementation without touching the orchestrator.
- All CSS/ARIA selectors live in `app/adapters/selectors.yaml`, never hardcoded in Python.
- When login page, CAPTCHA, or verification dialog appears: stop, screenshot, set status `needs_user_action`. Never try to bypass.
- Browser runs headed in V1. Only one browser session at a time (global async lock). Jobs are processed by a single worker.

## 2. Phase 0 — Preconditions (manual, human-owned)

Not for Codex to automate. Create `docs/tos-check.md` template with sections per provider:
- Terms URL, date reviewed, is UI automation permitted (yes/no/unclear), decision (UI adapter / official API adapter).

Codex tasks:
- Create the template file.
- Create `scripts/check_router.py` that calls the 9router endpoint with each of three model names (`planner`, `extractor`, `lead`) and prints latency + first 50 chars of reply.

Acceptance: `python scripts/check_router.py` succeeds for all three.

## 3. Architecture

```text
Client -> FastAPI (127.0.0.1:8000)
            -> SQLite job store + in-process asyncio queue
            -> Orchestrator worker
                 1. Planner        (9router, model=planner)
                 2. Dispatcher     -> PerplexityAdapter / GeminiAdapter (Playwright)
                 3. Extractor      (9router, model=extractor)
                 4. Verifier       (rule-based + 9router)
                 5. Synthesizer    (9router, model=lead)
            -> artifacts/ (raw HTML, screenshots)
```

### Repo layout

```text
deepresearch-local/
  PLAN.md
  README.md
  pyproject.toml
  .env.example
  .gitignore
  docs/tos-check.md
  app/
    main.py
    api/            routes.py, schemas.py, auth.py, sse.py
    core/           config.py, logging.py, db.py, models.py, queue.py
    llm/            router_client.py, prompts/*.md
    orchestrator/   pipeline.py, planner.py, dispatcher.py,
                    extractor.py, verifier.py, synthesizer.py
    adapters/       base.py, perplexity.py, gemini.py, fake.py, selectors.yaml
    browser/        session.py, waits.py, artifacts.py
  scripts/          login_profile.py, smoke_test.py, check_router.py
  tests/
    unit/ contract/ e2e/ fixtures/html/
  data/             (gitignored) profiles/, artifacts/, app.db
```

### Configuration (`.env.example`)

```env
ROUTER_BASE_URL=http://localhost:20128/v1
ROUTER_API_KEY=changeme
ROUTER_MODEL_PLANNER=planner
ROUTER_MODEL_EXTRACTOR=extractor
ROUTER_MODEL_LEAD=lead
API_KEY=changeme
BROWSER_PROFILE_DIR=./data/profiles/main
ARTIFACT_DIR=./data/artifacts
DB_URL=sqlite+aiosqlite:///./data/app.db
MAX_QUESTIONS_PER_HOUR=20
DEFAULT_TIMEOUT_MIN=20
MIN_DELAY_BETWEEN_QUESTIONS_S=5
MAX_DELAY_BETWEEN_QUESTIONS_S=15
```

## 4. API Contract

### `POST /research`
Request:
```json
{
  "query": "string",
  "depth": "standard | deep",
  "providers": ["perplexity", "gemini"],
  "max_minutes": 20
}
```
Response `202`: `{ "job_id": "uuid" }`

### `GET /research/{job_id}`
Returns:
```json
{
  "job_id": "uuid",
  "status": "queued|planning|researching|extracting|verifying|synthesizing|completed|partial|failed|needs_user_action|cancelled",
  "progress": {"subtasks_total": 0, "subtasks_done": 0},
  "report_markdown": "string|null",
  "sources": [{"id": "S1", "url": "...", "title": "..."}],
  "claims": [{"id": "C1", "text": "...", "source_ids": ["S1"], "verdict": "supported|single_source|unsupported|conflict"}],
  "disagreements": [{"topic": "...", "positions": []}],
  "provider_runs": [{"provider": "...", "status": "...", "elapsed_ms": 0}],
  "error": "string|null"
}
```

### Other routes
- `GET /research/{job_id}/events` — SSE stream of status/progress events.
- `POST /research/{job_id}/cancel` — cooperative cancel.
- `GET /health` — no auth; returns per-adapter health (`logged_in`, `selectors_ok`) and router reachability.

## 5. Data Model (SQLModel)

- `Job`: id, query, status, config_json, created_at, finished_at, error
- `Subtask`: id, job_id, branch, provider, prompt, status, attempt
- `ProviderRun`: id, subtask_id, answer_md, conversation_url, started_at, finished_at, artifact_paths_json, status
- `Source`: id, run_id, url, title, snippet
- `Claim`: id, job_id, text, branch, source_ids_json, verdict
- `Report`: id, job_id, markdown, model_used, tokens_in, tokens_out

## 6. Adapter Interface

```python
class Source(BaseModel):
    url: str
    title: str | None = None
    snippet: str | None = None

class ProviderResult(BaseModel):
    provider: str
    prompt: str
    answer_markdown: str
    sources: list[Source]
    conversation_url: str | None
    status: Literal["ok", "partial", "timeout", "needs_user_action", "error"]
    started_at: datetime
    finished_at: datetime
    artifact_paths: list[str]
    error: str | None = None

class HealthStatus(BaseModel):
    logged_in: bool
    selectors_ok: bool
    detail: str | None = None

class ProviderAdapter(Protocol):
    name: str
    async def health(self) -> HealthStatus: ...
    async def ask(self, prompt: str, *, timeout_s: int, mode: str = "default") -> ProviderResult: ...
```

`adapters/fake.py` implements the interface with canned responses for tests.

### Adapter behavior (each real adapter)
1. Open a new chat page.
2. Select mode if configured (Perplexity research/pro mode, Gemini deep research) — optional, controlled by `mode`.
3. Insert prompt into the input box, submit.
4. Wait for completion (see below).
5. Extract answer as Markdown from DOM, extract source links/citations.
6. Save raw HTML + screenshot to artifacts dir.
7. Return `ProviderResult`.

### Completion detection (`browser/waits.py`)
Combine signals; complete when (1) AND (2) hold, or (3) holds:
1. "Stop/generating" indicator is gone AND input box is enabled.
2. Answer text unchanged for `stable_seconds` (default 8) while polling every 2–5 s.
3. A "done" element (e.g. copy/feedback button) is visible.
On `timeout_s` reached: save what exists, return `status="partial"` (or `timeout` if empty).

### Browser session (`browser/session.py`)
- Singleton with `asyncio.Lock`.
- `launch_persistent_context(user_data_dir=BROWSER_PROFILE_DIR, channel="chrome", headless=False)`.
- Dedicated automation profile only — never the user's daily profile.
- Do not rely on `--remote-debugging-port` against the default Chrome profile (Chrome 136+ ignores it for the default data dir).
- `scripts/login_profile.py`: opens the profile headed at both sites so the human logs in manually once, then waits for Enter and closes cleanly.

### Rate limiting
- Global token-bucket: `MAX_QUESTIONS_PER_HOUR` per provider.
- Random delay between questions in `[MIN_DELAY, MAX_DELAY]`.
- On any rate-limit/verification message from the site: stop that provider, mark subtask `needs_user_action`, continue others.

## 7. Orchestrator Pipeline

1. **Planner** (`model=planner`, JSON-schema output): split the query into 4–6 research branches; each has `branch`, `prompt`, `preferred_provider`. Heuristic: Perplexity for source-heavy/factual branches, Gemini for explanatory/structural branches. Validate output with Pydantic; retry once on invalid JSON.
2. **Dispatcher**: run subtasks sequentially through the shared browser session (max 1 concurrent), retry a failed subtask once, then mark failed and continue. Respect `max_minutes` for the entire job → remaining subtasks skipped, job ends `partial`.
3. **Extractor** (`model=extractor`, JSON output): per `ProviderRun` produce claims `{text, source_urls, confidence, branch}`. Persist as `Claim`/`Source`.
4. **Verifier**:
   - Rule-based: dedupe similar claims, flag claims with zero URLs (`unsupported`), one source (`single_source`).
   - LLM-assisted: detect cross-provider contradictions, especially numeric facts → `conflict` + `disagreements`.
   - Optional one follow-up question (max 1 round) for the top-N important weak claims, only if time budget remains.
5. **Synthesizer** (`model=lead`): input is per-branch summaries + verified claims + source list (not raw full text if too long). Output Markdown report where:
   - Every important factual statement carries `[S#]` markers.
   - A section "Disagreements and unverified points" is mandatory.
   - No facts outside the provided claims.
   - Post-check: every `[S#]` in the report exists in the sources table; otherwise re-prompt once, then fail to `partial` with a warning.

Prompts live in `app/llm/prompts/*.md` (planner.md, extractor.md, verifier.md, synthesizer.md). All 9router calls go through `llm/router_client.py` (OpenAI SDK, `base_url=ROUTER_BASE_URL`), with `tenacity` retries and token accounting.

## 8. Implementation Phases (execute in order; stop after each and run tests)

### Phase 1 — Skeleton and job lifecycle
Tasks:
- Project scaffolding, config, logging, DB models, migrations (or `create_all`).
- Routes, auth, SSE, in-process queue and single worker.
- `FakeAdapter` and a stub pipeline that walks through all statuses.
Acceptance:
- `POST /research` → `GET` reaches `completed` using FakeAdapter.
- SSE emits status transitions. Cancel works. `pytest` green.

### Phase 2 — Browser session
Tasks:
- `BrowserSession`, `login_profile.py`, artifact saving, `smoke_test.py` skeleton.
Acceptance:
- Profile persists login after full process restart (manual verification documented in README).
- Artifacts saved under `data/artifacts/{job_id}/`.

### Phase 3 — PerplexityAdapter
Tasks:
- Implement `health()` and `ask()`, selectors in YAML with fallbacks, completion detection, source extraction.
- Save HTML fixtures to `tests/fixtures/html/perplexity_*.html`; unit-test extraction logic against them offline.
Acceptance:
- 20 sample questions in `tests/e2e/questions.yaml`: ≥90% return `ok` with ≥1 source (run manually, results written to `docs/eval/perplexity.md`).

### Phase 4 — GeminiAdapter
Same tasks and acceptance as Phase 3 for Gemini.

### Phase 5 — Full pipeline
Tasks:
- Implement planner, dispatcher, extractor, verifier, synthesizer and prompts.
- Contract tests with mocked router (`respx` or a fake client) covering: invalid JSON retry, missing `[S#]` re-prompt, partial results.
Acceptance:
- End-to-end run of "Research the Airbus A320 in great detail" produces a report with all branches, every key number cited, and a disagreements section.

### Phase 6 — Robustness
Tasks:
- Timeouts, `partial` handling, `needs_user_action` flow, cancel, restart recovery (jobs in-flight at startup are marked `failed` or resumed from the last completed subtask).
- Health endpoint reports selector breakage.
Acceptance:
- Simulated logout or network drop mid-job does not crash the worker; job ends `partial` or `needs_user_action` with artifacts saved.

### Phase 7 — Evaluation
Tasks:
- `scripts/eval.py`: run 10 topics through (a) single-provider baseline and (b) full pipeline; write CSV with: claims total, % claims with openable source, manual-error count column (blank for human), coverage vs. reference outline, elapsed time, tokens.
Acceptance:
- CSV generated; README summarizes how to fill the manual columns.

## 9. Testing Strategy

- Unit: planner/extractor/verifier/synthesizer with a fake router client; selector loader; completion-detection logic with simulated DOM states.
- Contract: one shared test suite parametrized over `FakeAdapter`, `PerplexityAdapter`, `GeminiAdapter` (real adapters marked `@pytest.mark.live`, skipped by default).
- Fixtures: saved HTML for offline extraction tests.
- Smoke: `scripts/smoke_test.py` asks one trivial question per adapter and reports selector health; suitable for daily run.

## 10. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| UI changes break selectors | YAML selectors with fallbacks, smoke test, artifacts for debugging |
| Provider terms disallow UI automation | Phase 0 gate; official-API adapter behind same interface |
| Account rate limits or flags | Sequential execution, hourly cap, stop on warnings, no evasion |
| Bad extraction (UI noise in answer) | Fixture tests, DOM-based extraction only |
| Hallucinated report facts | Claims-only synthesis, `[S#]` post-validation, disagreements section |
| Credential leakage | Dedicated profile, gitignored `data/`, no cookie/key logging, loopback bind |
| Machine sleeps mid-job | Persist state in SQLite; document disabling sleep during runs |

## 11. Definition of Done (V1)

- All Phase 1–6 acceptance criteria met; Phase 7 evaluation produced.
- README covers setup, first-time login, running, config, and troubleshooting.
- `pytest` passes (live tests excluded by default).
- Adapters can be disabled via config without breaking the pipeline.