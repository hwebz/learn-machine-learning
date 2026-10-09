# Deep Research Local

A locally run research orchestrator. It provides an authenticated HTTP API, persistent SQLite job state, a single in-process worker, SSE progress, and cooperative cancellation. Research providers can be driven two ways:

- **`official_api`** — Perplexity's official Agent API (no browser).
- **`ui`** — Playwright-driven **signed-in browser automation** for the Perplexity and Gemini web UIs, using a dedicated persistent browser profile (Edge by default; Brave supported).

The full planning and synthesis pipeline is still to come; V1 returns provider answers + sources.

## Requirements

- Python 3.10–3.12
- Microsoft Edge installed (Playwright `channel="msedge"`) — Brave also supported via `executable_path` override
- 9router running locally for `scripts/check_router.py` (the fake pipeline does not require it)

## Setup

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m playwright install msedge
Copy-Item .env.example .env
```

Edit `.env`. Key settings:

| Variable | Purpose |
|---|---|
| `RESEARCH_ADAPTER_MODE` | `fake` \| `official_api` \| `ui` |
| `API_KEY` | Required on every route except `/health` (`X-API-Key`) |
| `PERPLEXITY_API_KEY` | Only needed for `official_api` mode |
| `BROWSER_PROFILE_DIR` | Dedicated automation profile (`./data/profiles/main`) |
| `BROWSER_HEADLESS` | `false` in V1 (headed, so you can watch/intervene) |
| `BROWSER_CHANNEL` | `msedge` (system Edge; `chrome`/`chrome-beta` also supported) |
| `ADAPTER_STABLE_SECONDS` | Answer-text stability window before declaring completion |
| `MAX_QUESTIONS_PER_HOUR` | Per-provider rate cap |

The defaults bind the API to loopback, use `./data/app.db`, and keep browser profiles and artifacts under the gitignored `data/` directory.

## Browser UI mode (Playwright, signed-in chatbots)

This mode drives the real **Perplexity** and **Gemini** web UIs in a headed Chrome window that reuses a persistent, dedicated profile — so the sites stay signed in between runs.

### First-time login

```powershell
python scripts/login_profile.py
```

A headed Chrome window opens at each chatbot site. Sign in where prompted, then press Enter in the terminal. Login state is saved into `BROWSER_PROFILE_DIR`. Re-run anytime to re-check; already-signed-in sites load without a login prompt.

> Use a **dedicated automation profile only** — never your daily Chrome profile. Cookies and keys are never logged; `data/` is gitignored.

### Validate selectors

```powershell
python scripts/smoke_test.py              # static checks (selectors.yaml + profile dir)
python scripts/smoke_test.py --live       # open the browser and probe each site's DOM
python scripts/smoke_test.py --live --ask # ... then send one probe question per provider
```

All site selectors live in [app/adapters/selectors.yaml](app/adapters/selectors.yaml) as ordered fallback chains (ARIA role / `data-testid` / placeholder / CSS). When a site ships a UI change and selectors break:

1. Run `python scripts/smoke_test.py --live` — it reports which rung matched (or failed) per chain.
2. Edit `selectors.yaml` (never hardcode selectors in Python).
3. Failed runs save raw HTML + screenshot under `data/artifacts/` for inspection.

### Run research through the UI

```powershell
# .env → RESEARCH_ADAPTER_MODE=ui
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
$headers = @{ "X-API-Key" = "changeme" }
$job = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/research -Headers $headers -ContentType "application/json" -Body '{"query":"Explain how solar panels work","depth":"standard","providers":["perplexity","gemini"]}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/research/$($job.job_id)" -Headers $headers
```

You will see the headed browser type the prompt, submit it, wait for generation, and return the answer + citation sources. `GET /health` reports per-adapter UI health (`logged_in`, `selectors_ok`) without launching a browser.

### Constraints (by design)

- **No CAPTCHA solving, no bot-detection evasion, no rate-limit evasion, no token extraction, no private API calls.** If a login page, CAPTCHA, or verification dialog appears, the adapter stops, screenshots the page, and returns `needs_user_action`. Complete the check manually in the browser window, then retry.
- Only one browser interaction at a time (global lock).
- DOM locators only — no screen-coordinate automation.
- Per-provider hourly cap (`MAX_QUESTIONS_PER_HOUR`) plus random delay between questions.

### Provider terms

Before enabling UI automation in earnest, review each provider's terms and record the decision in [docs/tos-check.md](docs/tos-check.md). Use an official-API adapter wherever UI automation is not permitted.

## Run (all modes)

### 1. Khởi động Server nhanh bằng script (Khuyên dùng)

```powershell
.\scripts\StartServer.ps1
```
*(Script tự động kích hoạt `.venv`, kiểm tra cổng `8000` và khởi chạy Uvicorn tại `http://127.0.0.1:8000`)*

Hoặc khởi động trực tiếp:
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`GET /health` is public. Every other route requires header `X-API-Key: changeme` (hoặc cấu hình trong `.env`). Use `GET /research/{job_id}/events` for SSE status/progress, `POST /research/{job_id}/cancel` for cooperative cancellation.

Job outcomes:
- `completed` — all providers returned answers.
- `partial` — some providers succeeded; see `provider_runs` and the report's "Provider issues" section.
- `needs_user_action` — providers are blocked on login/CAPTCHA; check `data/artifacts/`.

## Postman Documentation

Dự án cung cấp sẵn file Postman Collection v2.1 đầy đủ: [Deep_Research_Local.postman_collection.json](Deep_Research_Local.postman_collection.json).

### Cách 1: Import file Collection vào Postman (1-Click)
1. Trong Postman, bấm **Import** (hoặc `Ctrl + O`) $\rightarrow$ chọn file `Deep_Research_Local.postman_collection.json`.
2. Mở rộng (nhấp dấu mũi tên `>`) collection **Deep Research Local (pc_chatbots)** ở thanh bên trái để thấy 5 requests:
   - `1. Health Check` (`GET http://127.0.0.1:8000/health`)
   - `2. Create Research Job` (`POST http://127.0.0.1:8000/research`) — *Tự động lưu `job_id` vào biến collection!*
   - `3. Get Research Job Status & Result` (`GET http://127.0.0.1:8000/research/{{job_id}}`) — *Tự động dùng `job_id` vừa lưu.*
   - `4. Cancel Research Job` (`POST http://127.0.0.1:8000/research/{{job_id}}/cancel`)
   - `5. Research Events Stream (SSE)` (`GET http://127.0.0.1:8000/research/{{job_id}}/events`)

### Cách 2: Import nhanh qua cURL
Bấm **Import** trong Postman $\rightarrow$ chọn tab **Raw text** $\rightarrow$ dán lệnh cURL:

```bash
curl --location 'http://127.0.0.1:8000/research' \
--header 'X-API-Key: changeme' \
--header 'Content-Type: application/json' \
--data '{
  "query": "Explained in detailed about Gradient Decent for Vietnamese",
  "depth": "standard",
  "providers": [
    "copilot",
    "gemini",
    "qwen"
  ],
  "max_minutes": 20
}'
```

### Chi tiết các Endpoint chính

| Endpoint | Method | Header | Mô tả |
|---|---|---|---|
| `/health` | `GET` | Không cần | Kiểm tra trạng thái server, router LLM và danh sách các adapter UI đã login. |
| `/research` | `POST` | `X-API-Key: changeme`<br>`Content-Type: application/json` | Tạo job nghiên cứu mới. Trả về `202 Accepted` với `{ "job_id": "uuid" }`. |
| `/research/{job_id}` | `GET` | `X-API-Key: changeme` | Lấy tiến độ xử lý và toàn bộ nội dung báo cáo Markdown (`report_markdown`) khi hoàn tất. |
| `/research/{job_id}/cancel` | `POST` | `X-API-Key: changeme` | Hủy an toàn job đang thực hiện. |
| `/research/{job_id}/events` | `GET` | `X-API-Key: changeme`<br>`Accept: text/event-stream` | Theo dõi thời gian thực sự thay đổi trạng thái qua Server-Sent Events (SSE). |

#### Cấu trúc Body mẫu (`POST /research`)

```json
{
  "query": "Explained in detailed about Gradient Decent for Vietnamese",
  "depth": "standard",
  "providers": ["copilot", "gemini", "qwen"],
  "max_minutes": 20
}
```
Các providers khả dụng: `copilot`, `gemini`, `qwen`, `chatgpt`, `claude`, `deepseek`, `perplexity`, `kimi`, `grok`, `meta`, `mistral`, `pi`, `zhipu`, `minimax`.


## Tests

```powershell
pytest                 # unit + contract + lifecycle (no browser required)
pytest -m live         # optional: one real question per UI adapter (signed-in profile required)
```

Live tests are skipped by default. Unit tests cover selectors loading, completion-detection logic (fake page objects), and HTML→Markdown / source extraction against fixture files under `tests/fixtures/html/`.

## Router check

Once 9router is available, configure its URL, key, and model names in `.env`, then run:

```powershell
python scripts/check_router.py
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `needs_user_action` with a login error | Run `python scripts/login_profile.py` and sign in |
| Selector not found in smoke test | Edit `app/adapters/selectors.yaml`; inspect `data/artifacts/` HTML |
| Browser fails to launch | `python -m playwright install msedge`; check `BROWSER_CHANNEL` (msedge / chrome-brave / chrome) |
| Browser reuses the wrong profile | Ensure `BROWSER_PROFILE_DIR` points at a dedicated directory |
| Gemini returns nothing | Confirm you're signed in at gemini.google.com; check `--live` output |

