# Phase 4: Delphi Consensus (Convergence Scoring)

> **Effort**: ~3–4 days | **Risk**: High | **Branch**: `v2`
> **Depends on**: Phase 3 (Adversarial Debate — consensus scores debate-refined theses)
> **Required before**: None (terminal feature)

---

## Goal

After the debate phase (or after research if debate is disabled), run a **Delphi Consensus** process. Extract key theses from the findings, have multiple agents score each thesis on confidence/feasibility (1–5), iterate until scores converge (low standard deviation), then pass the consensus data to the lead synthesizer.

### Pipeline After This Phase
```
Summarize → Orchestrate → Research → [Fact-Check] → [Debate] → **Consensus (NEW)** → Lead Synthesize
```

---

## Acceptance Criteria

- [x] New `"consensus"` status appears in pipeline flow
- [x] `enable_consensus` flag in `AgentResearchRequest` (default `false`)
- [x] Key theses are extracted from findings + debate
- [x] Multiple providers score each thesis (1–5)
- [x] Scoring iterates until std dev < threshold or max rounds reached
- [x] Consensus scores are stored and passed to lead synthesis
- [x] When disabled, pipeline behaves exactly as before
- [x] Frontend shows consensus progress in timeline
- [x] Frontend visualizes consensus scores

---

## Backend Changes

### 1. Add config fields to `AgentResearchRequest`

**File**: `app/api/schemas.py`

```diff
 class AgentResearchRequest(BaseModel):
     # ... existing fields ...
     max_debate_rounds: int = Field(default=2, ge=1, le=5)
+    enable_consensus: bool = Field(default=False)
+    consensus_providers: list[ProviderName] | None = Field(default=None)
+    consensus_threshold: float = Field(default=0.8, ge=0.1, le=2.0)
+    max_consensus_rounds: int = Field(default=3, ge=1, le=5)
```

### 2. Add `"consensus"` to `JobStatus`

**File**: `app/api/schemas.py`

```diff
 JobStatus = Literal[
-    "queued", "summarizing", "orchestrating", "planning", "researching", "fact_checking", "debating", "extracting", "verifying", "synthesizing", "leading",
+    "queued", "summarizing", "orchestrating", "planning", "researching", "fact_checking", "debating", "consensus", "extracting", "verifying", "synthesizing", "leading",
     "completed", "partial", "failed", "needs_user_action", "cancelled",
 ]
```

### 3. Add DB columns to `Job` model

**File**: `app/core/models.py`

```diff
 class Job(SQLModel, table=True):
     # ... existing fields ...
     debate_transcript_json: str | None = None
+    enable_consensus: bool = False
+    consensus_providers_json: str | None = None
+    consensus_threshold: float = 0.8
+    max_consensus_rounds: int = 3
+    consensus_scores_json: str | None = None
```

### 4. Implement thesis extraction prompt

**File**: `app/orchestrator/agent_pipeline.py`

```python
def build_thesis_extraction_prompt(
    research_topic: str,
    findings_summary: str,
    debate_summary: str | None = None,
) -> str:
    """Extract key theses from research findings for consensus scoring."""
    debate_section = ""
    if debate_summary:
        debate_section = f"""
## Debate Outcomes:
{debate_summary[:3000]}
"""

    return f"""You are a Research Analyst. Extract the TOP 5-8 most important theses (key conclusions or recommendations) from the following research findings.

## Research Topic: {research_topic}

## Research Findings:
{findings_summary[:5000]}
{debate_section}
## Output Format (strict JSON array):
[
  {{
    "id": "T1",
    "thesis": "<concise thesis statement>",
    "category": "<technical|economic|strategic|risk>",
    "supporting_evidence": "<brief summary of evidence>"
  }}
]

Rules:
- Each thesis must be a specific, scorable statement (not vague).
- Include both well-supported AND contested theses.
- Output ONLY the JSON array. No markdown fences."""
```

### 5. Implement scoring prompt

```python
def build_consensus_scoring_prompt(
    theses: list[dict[str, Any]],
    round_number: int,
    previous_aggregate: list[dict[str, Any]] | None = None,
) -> str:
    """Prompt an agent to score each thesis on confidence (1-5)."""
    theses_text = "\n".join(
        f"- **{t.get('id', f'T{i}')}**: {t.get('thesis', '')}"
        for i, t in enumerate(theses, 1)
    )

    prev_section = ""
    if previous_aggregate and round_number > 1:
        prev_section = f"""
## Aggregate Scores from Previous Round:
{json.dumps(previous_aggregate, indent=2, ensure_ascii=False)[:2000]}

Consider the group tendency but make your own independent judgment.
"""

    return f"""You are an Independent Research Evaluator (Scoring Round {round_number}).
Score each thesis below on a scale of 1-5 for CONFIDENCE (how likely this is correct and actionable).

1 = Very low confidence (likely wrong or impractical)
2 = Low confidence (significant doubts)
3 = Moderate confidence (plausible but uncertain)
4 = High confidence (well-supported, likely correct)
5 = Very high confidence (strongly supported, highly actionable)

## Theses to Score:
{theses_text}
{prev_section}
## Output Format (strict JSON array):
[
  {{"id": "T1", "score": <1-5>, "reasoning": "<brief justification>"}},
  ...
]

Rules:
- Score EVERY thesis. Don't skip any.
- Be honest — don't default to middle scores.
- Output ONLY the JSON array."""
```

### 6. Implement `run_delphi_consensus()`

```python
import statistics

async def run_delphi_consensus(
    job_id: str,
    research_topic: str,
    runs: list[dict[str, Any]],
    debate_transcript: list[dict[str, Any]],
    consensus_providers: list[str],
    threshold: float,
    max_rounds: int,
    cancel_event: asyncio.Event,
) -> dict[str, Any]:
    """Phase 4: Delphi Consensus — iterative scoring until convergence."""
    consensus_start = time.monotonic()

    await _set_agent_status(
        job_id,
        "consensus",
        message=f"Bắt đầu quy trình Delphi Consensus với {len(consensus_providers)} nhà đánh giá...",
        data={
            "consensus_providers": consensus_providers,
            "threshold": threshold,
            "max_rounds": max_rounds,
            "role": "consensus",
            "provider_role_key": "consensus",
            "elapsed_s": 0.0,
        },
    )

    # Step 1: Extract theses
    findings_summary = "\n---\n".join(
        f"### {r.get('branch', 'Branch')}\n{r.get('answer_md', '')[:1500]}"
        for r in runs if r.get("status") == "ok"
    )
    debate_summary = None
    if debate_transcript:
        debate_summary = "\n".join(
            f"[{t.get('side', '')} R{t.get('round', '')}]: {t.get('content', '')[:500]}"
            for t in debate_transcript if t.get("content")
        )

    # Use first consensus provider to extract theses
    thesis_adapter = create_adapter(consensus_providers[0])
    thesis_prompt = build_thesis_extraction_prompt(research_topic, findings_summary, debate_summary)
    try:
        thesis_result = await thesis_adapter.ask(thesis_prompt, timeout_s=180, mode="default")
        cleaned = _clean_json_str(thesis_result.answer_markdown)
        theses = json.loads(cleaned)
        if not isinstance(theses, list) or len(theses) == 0:
            raise ValueError("No theses extracted")
    except Exception as te:
        logger.warning("thesis_extraction_failed", error=str(te))
        return {"theses": [], "rounds": [], "converged": False, "error": str(te)}
    finally:
        await BrowserSessionManager.close_session(consensus_providers[0])

    # Step 2: Iterative scoring rounds
    all_rounds: list[dict[str, Any]] = []
    previous_aggregate: list[dict[str, Any]] | None = None

    for round_num in range(1, max_rounds + 1):
        if cancel_event.is_set():
            break

        round_scores: dict[str, list[int]] = {t.get("id", f"T{i}"): [] for i, t in enumerate(theses, 1)}

        # Each provider scores
        for prov_id in consensus_providers:
            if cancel_event.is_set():
                break

            scorer_adapter = create_adapter(prov_id)
            score_prompt = build_consensus_scoring_prompt(theses, round_num, previous_aggregate)

            try:
                score_result = await scorer_adapter.ask(score_prompt, timeout_s=180, mode="default")
                cleaned_scores = _clean_json_str(score_result.answer_markdown)
                parsed_scores = json.loads(cleaned_scores)
                if isinstance(parsed_scores, list):
                    for sc in parsed_scores:
                        tid = sc.get("id", "")
                        score = sc.get("score", 3)
                        if tid in round_scores and isinstance(score, (int, float)):
                            round_scores[tid].append(int(min(5, max(1, score))))
            except Exception as sc_exc:
                logger.warning("consensus_scoring_failed", provider=prov_id, round=round_num, error=str(sc_exc))
            finally:
                await BrowserSessionManager.close_session(prov_id)

        # Calculate aggregate stats
        aggregate: list[dict[str, Any]] = []
        std_devs: list[float] = []
        for tid, scores in round_scores.items():
            if scores:
                mean = statistics.mean(scores)
                stdev = statistics.stdev(scores) if len(scores) > 1 else 0.0
                aggregate.append({"id": tid, "mean": round(mean, 2), "stdev": round(stdev, 2), "scores": scores, "n": len(scores)})
                std_devs.append(stdev)
            else:
                aggregate.append({"id": tid, "mean": 0, "stdev": 0, "scores": [], "n": 0})

        round_data = {"round": round_num, "aggregate": aggregate}
        all_rounds.append(round_data)
        previous_aggregate = aggregate

        # Emit progress
        avg_stdev = statistics.mean(std_devs) if std_devs else 0.0
        async with SessionLocal() as session:
            session.add(JobEvent(
                job_id=job_id,
                status="consensus",
                event_type="consensus_round",
                step=f"round_{round_num}",
                message=f"Vòng Delphi {round_num}/{max_rounds}: Avg StdDev = {avg_stdev:.2f} (ngưỡng: {threshold})",
                data_json=json.dumps({
                    "round": round_num,
                    "avg_stdev": round(avg_stdev, 3),
                    "threshold": threshold,
                    "aggregate": aggregate,
                    "role": "consensus",
                    "provider_role_key": "consensus",
                    "elapsed_s": round(time.monotonic() - consensus_start, 1),
                }, ensure_ascii=False),
            ))
            await session.commit()
        notify_job_event(job_id)

        # Check convergence
        if avg_stdev <= threshold:
            break

    # Build final result
    converged = bool(all_rounds and statistics.mean(
        [a.get("stdev", 0) for a in all_rounds[-1].get("aggregate", [])]
    ) <= threshold) if all_rounds else False

    consensus_result = {
        "theses": theses,
        "rounds": all_rounds,
        "converged": converged,
        "final_scores": all_rounds[-1].get("aggregate", []) if all_rounds else [],
    }

    # Persist
    consensus_duration = round(time.monotonic() - consensus_start, 1)
    async with SessionLocal() as session:
        db_j = await session.get(Job, job_id)
        if db_j is not None:
            db_j.consensus_scores_json = json.dumps(consensus_result, ensure_ascii=False)
            db_j.updated_at = utc_now()
            session.add(JobEvent(
                job_id=job_id,
                status="consensus",
                event_type="consensus_complete",
                step="consensus_complete",
                message=f"Delphi Consensus hoàn tất ({len(all_rounds)} vòng, {'đã hội tụ' if converged else 'chưa hội tụ'}, {consensus_duration}s).",
                data_json=json.dumps({
                    "converged": converged,
                    "rounds_completed": len(all_rounds),
                    "elapsed_s": consensus_duration,
                    "role": "consensus",
                    "provider_role_key": "consensus",
                }, ensure_ascii=False),
            ))
            await session.commit()
        notify_job_event(job_id)

    return consensus_result
```

### 7. Wire into `run_agent_pipeline()`

After debate phase, before lead synthesis:

```python
        # ---------------------------------------------------------
        # PHASE 4: DELPHI CONSENSUS (Optional)
        # ---------------------------------------------------------
        consensus_result: dict[str, Any] = {}
        enable_consensus = False
        consensus_provs: list[str] = []

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                enable_consensus = getattr(db_j, "enable_consensus", False)
                try:
                    consensus_provs = json.loads(db_j.consensus_providers_json) if db_j.consensus_providers_json else []
                except Exception:
                    consensus_provs = []
                if not consensus_provs:
                    # Default to using the delegated providers
                    consensus_provs = delegated_providers[:3] if delegated_providers else ["9router"]

        if enable_consensus and runs:
            consensus_result = await run_delphi_consensus(
                job_id=job_id,
                research_topic=research_topic,
                runs=runs,
                debate_transcript=debate_transcript if 'debate_transcript' in dir() else [],
                consensus_providers=consensus_provs,
                threshold=getattr(db_j, "consensus_threshold", 0.8),
                max_rounds=getattr(db_j, "max_consensus_rounds", 3),
                cancel_event=cancel_event,
            )

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return
```

### 8. Update `build_lead_prompt()` to include consensus

```diff
 def build_lead_prompt(
     research_topic: str,
     findings: list[dict[str, Any]],
     tone: str,
     context_summary: str | None = None,
     fact_check_claims: list[dict[str, Any]] | None = None,
     debate_transcript: list[dict[str, Any]] | None = None,
+    consensus_result: dict[str, Any] | None = None,
 ) -> str:
     # ... existing code ...

+    consensus_section = ""
+    if consensus_result and consensus_result.get("final_scores"):
+        scores_lines = []
+        for sc in consensus_result["final_scores"]:
+            thesis = next((t for t in consensus_result.get("theses", []) if t.get("id") == sc.get("id")), {})
+            scores_lines.append(f"- {sc.get('id', '')}: \"{thesis.get('thesis', '')}\" — Score: {sc.get('mean', '?')}/5 (StdDev: {sc.get('stdev', '?')})")
+        consensus_section = f"""
+## Consensus Scores (Delphi Method):
+Converged: {"✅ Yes" if consensus_result.get("converged") else "❌ No"}
+
+{chr(10).join(scores_lines)}
+
+IMPORTANT: Incorporate these consensus scores into your analysis. High-scoring theses should be emphasized. Low-scoring ones should be presented with appropriate caveats.
+"""
```

---

## Frontend Changes

### 1. Add `"consensus"` status to types

**File**: `chatbot/src/types/chat.ts`

Add `"consensus"` to the status union type.

### 2. Consensus toggle in `AgentConfigScreen.tsx`

```tsx
{/* Consensus Toggle */}
<div style={{ marginTop: 12, padding: "12px 16px", borderRadius: 8, border: "1px solid #e2e8f0" }}>
  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
    <input type="checkbox" checked={enableConsensus} onChange={(e) => setEnableConsensus(e.target.checked)} />
    <span style={{ fontWeight: 600, fontSize: 13 }}>📊 Enable Delphi Consensus</span>
  </label>
  <p style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
    All agents score key theses until consensus. Adds ~5-15 min. Best with 3+ providers.
  </p>
</div>
```

### 3. (Optional) Consensus Score Visualization

Create a component that shows:
- Thesis list with mean score bars
- Convergence indicator (converged vs. not)
- StdDev chart per round

---

## Testing Checklist

1. **Consensus disabled** — pipeline skips to Lead. No regression.
2. **Consensus with 2 providers, 2 rounds** — verify scoring data in `consensus_scores_json`
3. **Convergence detection** — with threshold 2.0 (easy), verify it converges in round 1
4. **Max rounds cap** — with threshold 0.01 (hard), verify it stops at max rounds
5. **Provider failure** — if one scoring provider fails, others still score
6. **Lead prompt** — verify consensus scores appear in synthesis prompt
7. **SSE events** — verify `consensus_round` and `consensus_complete` events

---

## Files Modified (Summary)

| File | Change |
|---|---|
| `pc_chatbots/app/api/schemas.py` | Add consensus config fields; add `"consensus"` status |
| `pc_chatbots/app/core/models.py` | Add consensus columns to `Job` |
| `pc_chatbots/app/api/routes.py` | Store consensus config when creating Job |
| `pc_chatbots/app/orchestrator/agent_pipeline.py` | Add thesis extraction, scoring, `run_delphi_consensus()`, wire into pipeline, update lead prompt |
| `chatbot/src/types/chat.ts` | Add `"consensus"` status |
| `chatbot/src/components/agent/AgentConfigScreen.tsx` | Add consensus toggle UI |
