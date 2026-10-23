# Phase 2: Fact-Check Phase (Post-Research Verification)

> **Effort**: ~3–4 days | **Risk**: Medium | **Branch**: `v2`
> **Depends on**: Phase 1 (Role Groups — for `fact_checker` role awareness)
> **Required before**: Phase 3 (Adversarial Debate)

---

## Goal

Insert a new **Fact-Check phase** between Research and Lead Synthesis. After all research subtasks complete, extract claims from each result and verify them using a designated fact-check provider (e.g., Perplexity for web search, or 9router for reasoning). Annotate each claim with a verification verdict.

### Pipeline After This Phase
```
Summarize (existing) → Orchestrate → Research → **Fact-Check (NEW)** → Lead Synthesize
```

---

## Acceptance Criteria

- [x] New `"fact_checking"` status appears in pipeline flow
- [x] `enable_fact_check` flag in `AgentResearchRequest` (default `false`)
- [x] When enabled, claims are extracted from research results
- [x] Each claim is verified by the fact-check provider and gets a verdict
- [x] Verdicts are stored in `Claim` model and visible in the final report
- [x] When disabled, pipeline behaves exactly as before (no regression)
- [x] Frontend shows fact-check status in timeline
- [x] Frontend shows verdict badges on claims in the report

---

## Backend Changes

### 1. Add config fields to `AgentResearchRequest`

**File**: `app/api/schemas.py`

```diff
 class AgentResearchRequest(BaseModel):
     query: str = Field(min_length=1, max_length=20_000)
     orchestrator_provider: ProviderName
     orchestrator_config: dict[str, Any] | None = Field(default_factory=dict)
     lead_provider: ProviderName
     lead_config: dict[str, Any] | None = Field(default_factory=dict)
     tone: str = Field(default="professional")
     max_minutes: int = Field(default=30, ge=1, le=180)
+    enable_fact_check: bool = Field(default=False)
+    fact_check_provider: ProviderName | None = Field(default="perplexity")
+    fact_check_config: dict[str, Any] | None = Field(default_factory=dict)
     # ... rest unchanged
```

### 2. Add `"fact_checking"` to `JobStatus`

**File**: `app/api/schemas.py`

```diff
 JobStatus = Literal[
-    "queued", "summarizing", "orchestrating", "planning", "researching", "extracting", "verifying", "synthesizing", "leading",
+    "queued", "summarizing", "orchestrating", "planning", "researching", "fact_checking", "extracting", "verifying", "synthesizing", "leading",
     "completed", "partial", "failed", "needs_user_action", "cancelled",
 ]
```

### 3. Add DB columns to `Job` model

**File**: `app/core/models.py`

```diff
 class Job(SQLModel, table=True):
     # ... existing fields ...
     context_summary: str | None = None
     parent_job_id: str | None = Field(default=None, index=True)
     conversation_id: str | None = Field(default=None, index=True)
+    enable_fact_check: bool = False
+    fact_check_provider: str | None = None
+    fact_check_config_json: str | None = None
+    fact_check_results_json: str | None = None
```

> [!IMPORTANT]
> After adding these columns, **delete your local `data/app.db`** to let SQLModel recreate the schema, or use `alembic` if you've set it up.

### 4. Store fact-check config when creating the job

**File**: `app/api/routes.py` — in the `POST /agent-research` handler, when creating the `Job` object:

```diff
     job = Job(
         id=job_id,
         query=req.query,
         # ... existing fields ...
+        enable_fact_check=req.enable_fact_check,
+        fact_check_provider=req.fact_check_provider,
+        fact_check_config_json=json.dumps(req.fact_check_config) if req.fact_check_config else None,
     )
```

### 5. Implement the Fact-Check phase in `agent_pipeline.py`

Insert between Phase 2 (Research) and Phase 3 (Lead Synthesis).

**File**: `app/orchestrator/agent_pipeline.py`

Add the following function (place it before `run_agent_pipeline`):

```python
def build_fact_check_prompt(research_branch: str, answer_text: str) -> str:
    """Build a prompt that asks the fact-checker to verify claims from a research result."""
    return f"""You are a rigorous Fact-Checker. You are given a research finding on a specific sub-topic.
Your job is to:
1. Extract the top 5-10 most important factual claims from the text.
2. For each claim, assess its verifiability and assign a verdict.

## Research Sub-topic: {research_branch}

## Research Text to Verify:
{answer_text[:4000]}

## Output Format (strict JSON array):
[
  {{
    "claim": "<exact factual statement>",
    "verdict": "supported" | "single_source" | "unsupported" | "conflict",
    "confidence": <float 0.0-1.0>,
    "reasoning": "<brief explanation of why this verdict>"
  }}
]

Rules:
- "supported": claim can be verified from multiple reliable sources
- "single_source": claim appears true but only from one source
- "unsupported": cannot find evidence to support this claim
- "conflict": different sources give contradictory information
- Output ONLY the JSON array. No markdown fences, no explanations."""


async def run_fact_check_phase(
    job_id: str,
    runs: list[dict[str, Any]],
    fact_check_provider: str,
    fact_check_config: dict[str, Any],
    cancel_event: asyncio.Event,
    initial_conv_urls: dict[str, str],
) -> list[dict[str, Any]]:
    """Phase 2.5: Fact-check each research result's claims."""
    all_claims: list[dict[str, Any]] = []
    fc_start = time.monotonic()

    await _set_agent_status(
        job_id,
        "fact_checking",
        message=f"Fact-Check Provider ({fact_check_provider}) đang kiểm chứng các luận điểm...",
        data={
            "fact_check_provider": fact_check_provider,
            "config": fact_check_config,
            "role": "fact_checker",
            "provider_role_key": "fact_checker",
            "total_branches": len(runs),
            "elapsed_s": 0.0,
        },
    )

    for idx, run_item in enumerate(runs):
        if cancel_event.is_set():
            break

        branch = run_item.get("branch", f"Branch {idx + 1}")
        answer = run_item.get("answer_md", "")
        if not answer or len(answer.strip()) < 50:
            continue  # Skip empty/trivial results

        fc_adapter = create_adapter(fact_check_provider)
        fc_prompt = build_fact_check_prompt(branch, answer)

        fc_kwargs: dict[str, Any] = {
            "timeout_s": 180,
            "mode": json.dumps(fact_check_config) if fact_check_config else "default",
        }
        if "on_step" in inspect.signature(fc_adapter.ask).parameters:
            fc_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=fact_check_provider,
                status="fact_checking",
                role="fact_checker",
                cancel_event=cancel_event,
                start_time=fc_start,
                extra_payload={
                    "branch": branch,
                    "branch_index": idx + 1,
                    "provider_role_key": "fact_checker",
                },
            )

        try:
            fc_result = await fc_adapter.ask(fc_prompt, **fc_kwargs)
            # Parse claims from response
            cleaned = _clean_json_str(fc_result.answer_markdown)
            parsed_claims = json.loads(cleaned)
            if isinstance(parsed_claims, list):
                for claim in parsed_claims:
                    claim["branch"] = branch
                    claim["provider"] = run_item.get("provider", "")
                all_claims.extend(parsed_claims)
        except Exception as fc_exc:
            logger.warning("fact_check_failed_for_branch", branch=branch, error=str(fc_exc))
        finally:
            await BrowserSessionManager.close_session(fact_check_provider)

    # Store claims in DB
    fc_duration = round(time.monotonic() - fc_start, 1)
    async with SessionLocal() as session:
        db_j = await session.get(Job, job_id)
        if db_j is not None:
            db_j.fact_check_results_json = json.dumps(all_claims, ensure_ascii=False)
            db_j.claims_json = json.dumps(all_claims, ensure_ascii=False)
            db_j.updated_at = utc_now()

            # Also persist individual Claim records
            for ci, c in enumerate(all_claims):
                session.add(Claim(
                    id=f"{job_id}:FC{ci + 1}",
                    job_id=job_id,
                    text=c.get("claim", ""),
                    branch=c.get("branch", ""),
                    verdict=c.get("verdict", "unsupported"),
                ))

            session.add(JobEvent(
                job_id=job_id,
                status="fact_checking",
                event_type="fact_check_complete",
                provider=fact_check_provider,
                step="fact_check_complete",
                message=f"Đã kiểm chứng {len(all_claims)} luận điểm từ {len(runs)} nhánh nghiên cứu ({fc_duration}s).",
                data_json=json.dumps({
                    "claims_count": len(all_claims),
                    "elapsed_s": fc_duration,
                    "role": "fact_checker",
                    "provider_role_key": "fact_checker",
                }, ensure_ascii=False),
            ))
            await session.commit()
        notify_job_event(job_id)

    return all_claims
```

### 6. Wire it into `run_agent_pipeline()`

**File**: `app/orchestrator/agent_pipeline.py` — inside `run_agent_pipeline()`, after Phase 2 (Research) completes and before Phase 3 (Lead), add:

```python
        # ---------------------------------------------------------
        # PHASE 2.5: FACT-CHECK (Optional, post-research verification)
        # ---------------------------------------------------------
        fact_check_claims: list[dict[str, Any]] = []
        enable_fc = False
        fc_provider = "perplexity"
        fc_config: dict[str, Any] = {}

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                enable_fc = getattr(db_j, "enable_fact_check", False)
                fc_provider = getattr(db_j, "fact_check_provider", None) or "perplexity"
                try:
                    fc_config = json.loads(db_j.fact_check_config_json) if db_j.fact_check_config_json else {}
                except Exception:
                    fc_config = {}

        if enable_fc and runs:
            fact_check_claims = await run_fact_check_phase(
                job_id=job_id,
                runs=runs,
                fact_check_provider=fc_provider,
                fact_check_config=fc_config,
                cancel_event=cancel_event,
                initial_conv_urls=initial_conv_urls,
            )

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return
```

### 7. Pass fact-check results to Lead Synthesis prompt

Update `build_lead_prompt()` to include fact-check claims if available:

```diff
 def build_lead_prompt(
     research_topic: str,
     findings: list[dict[str, Any]],
     tone: str,
     context_summary: str | None = None,
+    fact_check_claims: list[dict[str, Any]] | None = None,
 ) -> str:
     # ... existing code ...

+    fact_check_section = ""
+    if fact_check_claims:
+        verified = [c for c in fact_check_claims if c.get("verdict") == "supported"]
+        disputed = [c for c in fact_check_claims if c.get("verdict") in ("unsupported", "conflict")]
+        fact_check_section = f"""
+## Fact-Check Results:
+- {len(verified)} claims verified as supported
+- {len(disputed)} claims flagged as unsupported or conflicting
+
+### Disputed/Unsupported Claims (MUST address in report):
+{chr(10).join(f'- ⚠️ "{c.get("claim", "")}" — Verdict: {c.get("verdict", "")} — {c.get("reasoning", "")}' for c in disputed[:10])}
+
+IMPORTANT: Clearly mark any disputed claims in the report. Do not present unsupported claims as established facts.
+"""

     return f"""You are the Lead Research Synthesizer.
 ...
 {context_section}
+{fact_check_section}
 ## Findings from Autonomous AI Providers:
 ...
```

Then update the call site:

```diff
-        lead_prompt = build_lead_prompt(research_topic, runs, tone, context_summary=context_summary)
+        lead_prompt = build_lead_prompt(research_topic, runs, tone, context_summary=context_summary, fact_check_claims=fact_check_claims)
```

---

## Frontend Changes

### 1. Add `"fact_checking"` status

**File**: `chatbot/src/types/chat.ts`

```diff
 export interface ChatSession {
   // ...
-  status?: "queued" | "summarizing" | "running" | "completed" | "partial" | "failed" | "cancelled" | "orchestrating" | "researching" | "leading";
+  status?: "queued" | "summarizing" | "running" | "completed" | "partial" | "failed" | "cancelled" | "orchestrating" | "researching" | "fact_checking" | "leading";
   // ...
 }
```

### 2. Add fact-check config toggle to `AgentConfigScreen.tsx`

Add a toggle section below the Tone section:

```tsx
{/* Fact-Check Toggle */}
<div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 8, border: "1px solid #e2e8f0" }}>
  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
    <input
      type="checkbox"
      checked={enableFactCheck}
      onChange={(e) => setEnableFactCheck(e.target.checked)}
    />
    <span style={{ fontWeight: 600, fontSize: 13 }}>🔍 Enable Fact-Check Phase</span>
  </label>
  <p style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
    After research, verify key claims using a fact-check provider. Adds ~2-5 min.
  </p>
  {enableFactCheck && (
    <div style={{ marginTop: 8 }}>
      {/* Provider picker for fact-check - reuse existing ProviderGridPicker */}
    </div>
  )}
</div>
```

Add `enableFactCheck` state and pass it in `onStartAgentResearch`:
```typescript
const [enableFactCheck, setEnableFactCheck] = useState(false);
// In the submit handler:
onStartAgentResearch({
  ...config,
  enable_fact_check: enableFactCheck,
  fact_check_provider: factCheckProvider,
  fact_check_config: factCheckConfig,
});
```

### 3. Update `AgentConfigScreenProps` and the API call

The `onStartAgentResearch` callback config should include:
```typescript
enable_fact_check?: boolean;
fact_check_provider?: string;
fact_check_config?: Record<string, any>;
```

### 4. Show fact-check status in timeline

The `ChronologicalTimeline` already renders steps from `JobEvent`s. The fact-check events will automatically appear because they use the same `StepEmitter` / `JobEvent` system. No changes needed here.

### 5. Show verdict badges on claims (optional enhancement)

In the report/claims view, add verdict badges:
```tsx
function VerdictBadge({ verdict }: { verdict: string }) {
  const styles: Record<string, { bg: string; text: string; icon: string }> = {
    supported: { bg: "#d1fae5", text: "#065f46", icon: "✅" },
    single_source: { bg: "#fef3c7", text: "#92400e", icon: "⚠️" },
    unsupported: { bg: "#fee2e2", text: "#991b1b", icon: "❌" },
    conflict: { bg: "#fce7f3", text: "#9d174d", icon: "⚡" },
  };
  const s = styles[verdict] || styles.unsupported;
  return (
    <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, backgroundColor: s.bg, color: s.text, fontWeight: 600 }}>
      {s.icon} {verdict}
    </span>
  );
}
```

---

## Testing Checklist

1. **Fact-check disabled (default)** — pipeline skips directly from Research → Lead. No regression.
2. **Fact-check enabled** — pipeline shows `fact_checking` status between Research and Lead.
3. **Claims extracted** — verify `fact_check_results_json` on the Job has actual claims
4. **Claims in DB** — verify `Claim` records are created with proper verdicts
5. **Lead prompt** — verify the lead synthesis prompt includes the fact-check section
6. **SSE events** — verify `fact_check_complete` event fires with claims count
7. **Error handling** — if fact-check provider fails, pipeline continues to Lead with a warning (not a hard failure)
8. **Frontend toggle** — verify enable/disable fact-check in AgentConfigScreen works
9. **Cancel mid-fact-check** — cancel button works during fact-check phase

---

## Files Modified (Summary)

| File | Change |
|---|---|
| `pc_chatbots/app/api/schemas.py` | Add `enable_fact_check`, `fact_check_provider`, `fact_check_config` to request; add `"fact_checking"` status |
| `pc_chatbots/app/core/models.py` | Add `enable_fact_check`, `fact_check_provider`, `fact_check_config_json`, `fact_check_results_json` to `Job` |
| `pc_chatbots/app/api/routes.py` | Store fact-check config when creating Job |
| `pc_chatbots/app/orchestrator/agent_pipeline.py` | Add `build_fact_check_prompt()`, `run_fact_check_phase()`, wire into pipeline, update `build_lead_prompt()` |
| `chatbot/src/types/chat.ts` | Add `"fact_checking"` status |
| `chatbot/src/components/agent/AgentConfigScreen.tsx` | Add fact-check toggle UI |
