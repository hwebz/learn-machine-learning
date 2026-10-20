# Phase 3: Adversarial Debate (Red Team vs. Research)

> **Effort**: ~4–5 days | **Risk**: High | **Branch**: `v2`
> **Depends on**: Phase 2 (Fact-Check — debate reviews fact-checked findings)
> **Required before**: Phase 4 (Delphi Consensus)

---

## Goal

After fact-checking (or after research if fact-check is disabled), insert an **Adversarial Debate phase** where a Red Team agent reviews the research findings and produces counterarguments. The original research findings are then "defended" in a multi-turn debate. This produces a richer, more balanced analysis.

### Pipeline After This Phase
```
Summarize → Orchestrate → Research → [Fact-Check] → **Debate (NEW)** → Lead Synthesize
```

---

## Acceptance Criteria

- [ ] New `"debating"` status appears in pipeline flow
- [ ] `enable_debate` flag in `AgentResearchRequest` (default `false`)
- [ ] Configurable `debate_provider`, `max_debate_rounds` (default 2)
- [ ] Red Team critique is generated and stored
- [ ] Rebuttal from a defender provider is generated and stored
- [ ] Full debate transcript is persisted in `debate_transcript_json`
- [ ] Lead synthesis prompt includes debate outcomes
- [ ] When disabled, pipeline behaves exactly as before
- [ ] Frontend shows debate status in timeline
- [ ] Frontend shows debate transcript in a viewable component

---

## Backend Changes

### 1. Add config fields to `AgentResearchRequest`

**File**: `app/api/schemas.py`

```diff
 class AgentResearchRequest(BaseModel):
     # ... existing fields ...
     enable_fact_check: bool = Field(default=False)
     fact_check_provider: ProviderName | None = Field(default="perplexity")
     fact_check_config: dict[str, Any] | None = Field(default_factory=dict)
+    enable_debate: bool = Field(default=False)
+    debate_provider: ProviderName | None = Field(default=None)
+    debate_defender_provider: ProviderName | None = Field(default=None)
+    debate_config: dict[str, Any] | None = Field(default_factory=dict)
+    max_debate_rounds: int = Field(default=2, ge=1, le=5)
```

### 2. Add `"debating"` to `JobStatus`

**File**: `app/api/schemas.py`

```diff
 JobStatus = Literal[
-    "queued", "summarizing", "orchestrating", "planning", "researching", "fact_checking", "extracting", "verifying", "synthesizing", "leading",
+    "queued", "summarizing", "orchestrating", "planning", "researching", "fact_checking", "debating", "extracting", "verifying", "synthesizing", "leading",
     "completed", "partial", "failed", "needs_user_action", "cancelled",
 ]
```

### 3. Add DB columns to `Job` model

**File**: `app/core/models.py`

```diff
 class Job(SQLModel, table=True):
     # ... existing fields ...
     fact_check_results_json: str | None = None
+    enable_debate: bool = False
+    debate_provider: str | None = None
+    debate_defender_provider: str | None = None
+    debate_config_json: str | None = None
+    max_debate_rounds: int = 2
+    debate_transcript_json: str | None = None
```

### 4. Store debate config when creating the job

**File**: `app/api/routes.py` — in the agent-research job creation:

```diff
     job = Job(
         id=job_id,
         query=req.query,
         # ... existing fields ...
+        enable_debate=req.enable_debate,
+        debate_provider=req.debate_provider,
+        debate_defender_provider=req.debate_defender_provider,
+        debate_config_json=json.dumps(req.debate_config) if req.debate_config else None,
+        max_debate_rounds=req.max_debate_rounds,
     )
```

### 5. Implement Debate prompts

**File**: `app/orchestrator/agent_pipeline.py`

```python
def build_red_team_prompt(
    research_topic: str,
    findings_summary: str,
    fact_check_summary: str | None = None,
) -> str:
    """Prompt for the Red Team agent to critique the research findings."""
    fc_section = ""
    if fact_check_summary:
        fc_section = f"""
## Fact-Check Results Already Available:
{fact_check_summary}
"""

    return f"""You are a Red Team Critical Analyst. Your role is adversarial — your job is to find weaknesses, gaps, biases, and logical flaws in the following research findings.

## Research Topic: {research_topic}

## Research Findings to Critique:
{findings_summary[:6000]}
{fc_section}
## Your Task:
1. Identify the TOP 5 most critical weaknesses, biases, or logical flaws in these findings.
2. For each, explain WHY it's a problem and what the IMPACT would be if left unaddressed.
3. Suggest what evidence or perspective is MISSING.
4. Challenge any claims that seem over-confident or under-supported.

## Rules:
- Be specific and constructive. Don't just say "this is wrong" — explain what's missing.
- Focus on factual accuracy, logical consistency, completeness, and potential biases.
- If findings are strong, acknowledge that but still push for deeper analysis.

Produce your critique now:"""


def build_rebuttal_prompt(
    research_topic: str,
    original_findings: str,
    critique: str,
    round_number: int,
) -> str:
    """Prompt for the defender agent to rebut the Red Team critique."""
    return f"""You are the Research Defense Analyst (Round {round_number}). The Red Team has critiqued the research findings. Your role is to:

1. Address each critique point directly.
2. Provide additional evidence or reasoning to support or refine the original findings.
3. Concede points where the critique is valid — acknowledge gaps honestly.
4. Strengthen the overall analysis based on the critique.

## Research Topic: {research_topic}

## Original Research Findings:
{original_findings[:4000]}

## Red Team Critique:
{critique[:4000]}

## Your Task:
For each critique point:
- If valid: CONCEDE and note what should be changed in the final report
- If partially valid: REFINE with additional context
- If invalid: REBUT with specific evidence

Produce your defense now:"""
```

### 6. Implement `run_adversarial_debate()`

**File**: `app/orchestrator/agent_pipeline.py`

```python
async def run_adversarial_debate(
    job_id: str,
    research_topic: str,
    runs: list[dict[str, Any]],
    fact_check_claims: list[dict[str, Any]],
    debate_provider: str,
    debate_defender_provider: str | None,
    debate_config: dict[str, Any],
    max_rounds: int,
    cancel_event: asyncio.Event,
    initial_conv_urls: dict[str, str],
) -> list[dict[str, Any]]:
    """Phase 3: Adversarial Debate — Red Team vs. Research Defenders."""
    transcript: list[dict[str, Any]] = []
    debate_start = time.monotonic()

    # Build findings summary for the Red Team
    findings_summary = "\n\n---\n\n".join(
        f"### {r.get('branch', 'Branch')} (by {r.get('provider', 'AI')})\n{r.get('answer_md', '')[:2000]}"
        for r in runs if r.get("status") == "ok"
    )

    # Build fact-check summary if available
    fc_summary = None
    if fact_check_claims:
        disputed = [c for c in fact_check_claims if c.get("verdict") in ("unsupported", "conflict")]
        if disputed:
            fc_summary = "\n".join(f"- ⚠️ {c.get('claim', '')} [{c.get('verdict', '')}]" for c in disputed[:10])

    # Use a different provider for defense if specified, otherwise use the orchestrator
    defender_prov = debate_defender_provider or debate_provider

    await _set_agent_status(
        job_id,
        "debating",
        message=f"Red Team ({debate_provider}) đang phản biện các kết quả nghiên cứu...",
        data={
            "debate_provider": debate_provider,
            "defender_provider": defender_prov,
            "max_rounds": max_rounds,
            "role": "red_team",
            "provider_role_key": "red_team",
            "elapsed_s": 0.0,
        },
    )

    last_critique = ""
    last_defense = ""

    for round_num in range(1, max_rounds + 1):
        if cancel_event.is_set():
            break

        # --- RED TEAM CRITIQUE ---
        rt_adapter = create_adapter(debate_provider)
        if round_num == 1:
            rt_prompt = build_red_team_prompt(research_topic, findings_summary, fc_summary)
        else:
            # In subsequent rounds, critique the defense
            rt_prompt = f"""You are the Red Team (Round {round_num}). The defender responded to your previous critique.
Review their defense and identify any remaining weaknesses or new concerns.

## Previous Critique:
{last_critique[:3000]}

## Defender's Response:
{last_defense[:3000]}

Continue your adversarial analysis. Focus on points NOT adequately addressed:"""

        rt_kwargs: dict[str, Any] = {
            "timeout_s": 300,
            "mode": json.dumps(debate_config) if debate_config else "default",
        }
        if "on_step" in inspect.signature(rt_adapter.ask).parameters:
            rt_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=debate_provider,
                status="debating",
                role="red_team",
                cancel_event=cancel_event,
                start_time=debate_start,
                extra_payload={"round": round_num, "side": "red_team", "provider_role_key": f"red_team_round_{round_num}"},
            )

        try:
            rt_result = await rt_adapter.ask(rt_prompt, **rt_kwargs)
            last_critique = rt_result.answer_markdown
            transcript.append({
                "round": round_num,
                "side": "red_team",
                "provider": debate_provider,
                "content": last_critique,
                "elapsed_s": round(time.monotonic() - debate_start, 1),
            })
        except Exception as rt_exc:
            logger.warning("red_team_round_failed", round=round_num, error=str(rt_exc))
            transcript.append({"round": round_num, "side": "red_team", "error": str(rt_exc)})
            break
        finally:
            await BrowserSessionManager.close_session(debate_provider)

        if cancel_event.is_set():
            break

        # --- DEFENDER REBUTTAL ---
        def_adapter = create_adapter(defender_prov)
        def_prompt = build_rebuttal_prompt(research_topic, findings_summary, last_critique, round_num)

        def_kwargs: dict[str, Any] = {
            "timeout_s": 300,
            "mode": json.dumps(debate_config) if debate_config else "default",
        }
        if "on_step" in inspect.signature(def_adapter.ask).parameters:
            def_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=defender_prov,
                status="debating",
                role="defender",
                cancel_event=cancel_event,
                start_time=debate_start,
                extra_payload={"round": round_num, "side": "defender", "provider_role_key": f"defender_round_{round_num}"},
            )

        try:
            def_result = await def_adapter.ask(def_prompt, **def_kwargs)
            last_defense = def_result.answer_markdown
            transcript.append({
                "round": round_num,
                "side": "defender",
                "provider": defender_prov,
                "content": last_defense,
                "elapsed_s": round(time.monotonic() - debate_start, 1),
            })
        except Exception as def_exc:
            logger.warning("defender_round_failed", round=round_num, error=str(def_exc))
            transcript.append({"round": round_num, "side": "defender", "error": str(def_exc)})
            break
        finally:
            await BrowserSessionManager.close_session(defender_prov)

    # Persist transcript
    debate_duration = round(time.monotonic() - debate_start, 1)
    async with SessionLocal() as session:
        db_j = await session.get(Job, job_id)
        if db_j is not None:
            db_j.debate_transcript_json = json.dumps(transcript, ensure_ascii=False)
            db_j.updated_at = utc_now()
            session.add(JobEvent(
                job_id=job_id,
                status="debating",
                event_type="debate_complete",
                provider=debate_provider,
                step="debate_complete",
                message=f"Vòng tranh luận hoàn tất ({len(transcript)} lượt, {debate_duration}s).",
                data_json=json.dumps({
                    "rounds_completed": max(t.get("round", 0) for t in transcript) if transcript else 0,
                    "total_exchanges": len(transcript),
                    "elapsed_s": debate_duration,
                    "role": "red_team",
                    "provider_role_key": "red_team",
                }, ensure_ascii=False),
            ))
            await session.commit()
        notify_job_event(job_id)

    return transcript
```

### 7. Wire into `run_agent_pipeline()`

After fact-check (or after research if fact-check disabled), before lead synthesis:

```python
        # ---------------------------------------------------------
        # PHASE 3: ADVERSARIAL DEBATE (Optional)
        # ---------------------------------------------------------
        debate_transcript: list[dict[str, Any]] = []
        enable_debate = False
        debate_prov = ""
        debate_defender_prov: str | None = None
        debate_cfg: dict[str, Any] = {}
        max_debate_rnds = 2

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                enable_debate = getattr(db_j, "enable_debate", False)
                debate_prov = getattr(db_j, "debate_provider", None) or orchestrator_prov
                debate_defender_prov = getattr(db_j, "debate_defender_provider", None)
                max_debate_rnds = getattr(db_j, "max_debate_rounds", 2)
                try:
                    debate_cfg = json.loads(db_j.debate_config_json) if db_j.debate_config_json else {}
                except Exception:
                    debate_cfg = {}

        if enable_debate and runs:
            debate_transcript = await run_adversarial_debate(
                job_id=job_id,
                research_topic=research_topic,
                runs=runs,
                fact_check_claims=fact_check_claims if 'fact_check_claims' in dir() else [],
                debate_provider=debate_prov,
                debate_defender_provider=debate_defender_prov,
                debate_config=debate_cfg,
                max_rounds=max_debate_rnds,
                cancel_event=cancel_event,
                initial_conv_urls=initial_conv_urls,
            )

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return
```

### 8. Update `build_lead_prompt()` to include debate outcomes

```diff
 def build_lead_prompt(
     research_topic: str,
     findings: list[dict[str, Any]],
     tone: str,
     context_summary: str | None = None,
     fact_check_claims: list[dict[str, Any]] | None = None,
+    debate_transcript: list[dict[str, Any]] | None = None,
 ) -> str:
     # ... existing code ...

+    debate_section = ""
+    if debate_transcript:
+        critiques = [t for t in debate_transcript if t.get("side") == "red_team" and t.get("content")]
+        defenses = [t for t in debate_transcript if t.get("side") == "defender" and t.get("content")]
+        debate_section = f"""
+## Adversarial Debate Results:
+{len(critiques)} critique(s) and {len(defenses)} defense(s) were exchanged.
+
+### Key Red Team Critiques:
+{chr(10).join(f"**Round {c.get('round', '?')}**: {c.get('content', '')[:1000]}" for c in critiques[:3])}
+
+### Defender Responses:
+{chr(10).join(f"**Round {d.get('round', '?')}**: {d.get('content', '')[:1000]}" for d in defenses[:3])}
+
+IMPORTANT: Your synthesis MUST address the critiques raised. Acknowledge valid weaknesses. Do NOT ignore Red Team concerns.
+"""

     return f"""You are the Lead Research Synthesizer.
     ...
     {context_section}
     {fact_check_section}
+    {debate_section}
     ## Findings ...
```

---

## Frontend Changes

### 1. Add `"debating"` status to types

**File**: `chatbot/src/types/chat.ts`

```diff
-  status?: "queued" | "summarizing" | "running" | "completed" | "partial" | "failed" | "cancelled" | "orchestrating" | "researching" | "fact_checking" | "leading";
+  status?: "queued" | "summarizing" | "running" | "completed" | "partial" | "failed" | "cancelled" | "orchestrating" | "researching" | "fact_checking" | "debating" | "leading";
```

### 2. Add debate config to `AgentConfigScreen.tsx`

Add a toggle + config section below the fact-check toggle:

```tsx
{/* Debate Toggle */}
<div style={{ marginTop: 12, padding: "12px 16px", borderRadius: 8, border: "1px solid #e2e8f0" }}>
  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
    <input
      type="checkbox"
      checked={enableDebate}
      onChange={(e) => setEnableDebate(e.target.checked)}
    />
    <span style={{ fontWeight: 600, fontSize: 13 }}>⚔️ Enable Adversarial Debate</span>
  </label>
  <p style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
    Red Team agent will challenge research findings. Adds ~5-10 min.
  </p>
  {enableDebate && (
    <div style={{ marginTop: 8, display: "flex", gap: 12 }}>
      <label style={{ fontSize: 12 }}>
        Rounds:
        <select value={maxDebateRounds} onChange={(e) => setMaxDebateRounds(Number(e.target.value))}>
          <option value={1}>1 round</option>
          <option value={2}>2 rounds</option>
          <option value={3}>3 rounds</option>
        </select>
      </label>
      {/* Provider picker for debate Red Team */}
    </div>
  )}
</div>
```

### 3. Timeline events

Debate events will automatically appear in the ChronologicalTimeline because they emit `JobEvent`s with status `"debating"`. No changes needed.

### 4. (Optional) Debate Transcript Viewer

Create a new component `DebateTranscript.tsx` that displays the back-and-forth:

```tsx
// chatbot/src/components/agent/DebateTranscript.tsx
interface DebateEntry {
  round: number;
  side: "red_team" | "defender";
  provider: string;
  content: string;
  elapsed_s: number;
}

export function DebateTranscript({ transcript }: { transcript: DebateEntry[] }) {
  // Render as alternating Red Team (red) and Defender (blue) cards
  // Group by round number for visual clarity
}
```

---

## Testing Checklist

1. **Debate disabled (default)** — pipeline skips from Fact-Check/Research → Lead. No regression.
2. **Debate enabled, 2 rounds** — verify 4 transcript entries (2 critiques + 2 defenses)
3. **Debate enabled, 1 round** — verify 2 transcript entries
4. **Red Team failure** — if Red Team provider fails, debate ends early and pipeline continues to Lead
5. **Defender failure** — if defender fails, debate ends early and pipeline continues to Lead
6. **Transcript persisted** — verify `debate_transcript_json` on Job is populated
7. **Lead prompt** — verify lead synthesis includes debate outcomes
8. **Cancel mid-debate** — cancel button works during debate phase
9. **SSE events** — verify `debating` status and `debate_complete` event fire

---

## Files Modified (Summary)

| File | Change |
|---|---|
| `pc_chatbots/app/api/schemas.py` | Add `enable_debate`, `debate_provider`, `max_debate_rounds`; add `"debating"` status |
| `pc_chatbots/app/core/models.py` | Add debate columns to `Job` |
| `pc_chatbots/app/api/routes.py` | Store debate config when creating Job |
| `pc_chatbots/app/orchestrator/agent_pipeline.py` | Add `build_red_team_prompt()`, `build_rebuttal_prompt()`, `run_adversarial_debate()`, wire into pipeline, update `build_lead_prompt()` |
| `chatbot/src/types/chat.ts` | Add `"debating"` status |
| `chatbot/src/components/agent/AgentConfigScreen.tsx` | Add debate toggle UI |
| `chatbot/src/components/agent/DebateTranscript.tsx` | **New file** — debate transcript viewer |
