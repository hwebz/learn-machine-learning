# Phase 6: Dynamic Agent Scaling (Adaptive Count)

> **Effort**: ~2 days | **Risk**: Low | **Branch**: `v2`
> **Depends on**: Phase 1 (Role Groups)
> **Required before**: None (independent feature)

---

## Goal

Instead of the orchestrator always choosing 2–5 agents, add a **complexity analysis micro-step** that assesses the research topic and recommends the number of agents and which role groups are needed. This makes the system efficient for simple queries (2 agents) and thorough for complex ones (up to 10).

### This Phase Is Independent
This can be implemented **right after Phase 1** since it only modifies the orchestration step. It doesn't interact with Fact-Check, Debate, or Consensus.

---

## Acceptance Criteria

- [x] New `auto_scale_agents` flag (default `true`)
- [x] `min_agents` and `max_agents` config fields
- [x] Complexity analysis returns `recommended_agent_count` and `recommended_groups`
- [x] The orchestrator prompt uses the dynamic agent count
- [x] Complexity result is visible in SSE events and dispatch banner
- [x] When disabled, orchestrator uses the current fixed 2–5 range
- [x] Frontend shows complexity assessment and has slider for min/max

---

## Backend Changes

### 1. Add config fields to `AgentResearchRequest`

**File**: `app/api/schemas.py`

```diff
 class AgentResearchRequest(BaseModel):
     # ... existing fields ...
     tone: str = Field(default="professional")
+    auto_scale_agents: bool = Field(default=True)
+    min_agents: int = Field(default=2, ge=1, le=10)
+    max_agents: int = Field(default=5, ge=2, le=10)
```

### 2. No new DB columns needed

The complexity analysis result is ephemeral — it's used to configure the orchestrator prompt during the current job run. We store the resulting `recommended_agent_count` inside the `orchestrator_dispatch_json` or as a `JobEvent` for visibility.

### 3. Implement complexity analysis prompt

**File**: `app/orchestrator/agent_pipeline.py`

```python
def build_complexity_analysis_prompt(
    research_topic: str,
    available_providers: list[str],
    min_agents: int,
    max_agents: int,
) -> str:
    """Quick LLM call to assess topic complexity and recommend agent count."""
    return f"""You are a Research Planning Analyst. Assess the complexity of the following research topic and recommend how many specialized AI agents should investigate it.

## Research Topic:
"{research_topic}"

## Available Provider Count: {len(available_providers)}
## Allowed Range: {min_agents} to {max_agents} agents

## Assessment Criteria:
1. **Breadth**: How many distinct domains/angles does this topic span?
2. **Depth**: Does it require deep technical expertise or is it surface-level?
3. **Data Sensitivity**: Does it involve numbers, statistics, or claims that need verification?
4. **Controversy**: Are there competing viewpoints that should be explored?

## Output Format (strict JSON):
{{
  "complexity_level": "low" | "medium" | "high",
  "recommended_agent_count": <{min_agents}-{max_agents}>,
  "recommended_groups": ["researcher", "infra", "fact_checker", "red_team"],
  "reasoning": "<1-2 sentence justification>"
}}

Rules:
- "low" complexity → {min_agents} agents, just "researcher"
- "medium" → {min_agents + 1}-{max_agents - 1} agents, "researcher" + "infra"
- "high" → {max_agents} agents, all groups
- Output ONLY the JSON. No markdown fences."""
```

### 4. Implement `analyze_complexity()`

```python
async def analyze_complexity(
    job_id: str,
    research_topic: str,
    orchestrator_prov: str,
    orch_config: dict[str, Any],
    available_providers: list[str],
    min_agents: int,
    max_agents: int,
    cancel_event: asyncio.Event,
) -> dict[str, Any]:
    """Quick complexity assessment before orchestration."""
    default_result = {
        "complexity_level": "medium",
        "recommended_agent_count": min(max(3, min_agents), max_agents),
        "recommended_groups": ["researcher", "infra"],
        "reasoning": "Default assessment (complexity analysis skipped or failed).",
    }

    try:
        adapter = create_adapter(orchestrator_prov)
        prompt = build_complexity_analysis_prompt(research_topic, available_providers, min_agents, max_agents)

        result = await adapter.ask(
            prompt,
            timeout_s=60,  # Quick call — 60s max
            mode=json.dumps(orch_config) if orch_config else "default",
        )
        cleaned = _clean_json_str(result.answer_markdown)
        parsed = json.loads(cleaned)

        # Validate and clamp
        rec_count = parsed.get("recommended_agent_count", 3)
        rec_count = min(max(min_agents, int(rec_count)), max_agents)
        parsed["recommended_agent_count"] = rec_count

        rec_groups = parsed.get("recommended_groups", ["researcher"])
        valid_groups = {"researcher", "infra", "fact_checker", "red_team"}
        parsed["recommended_groups"] = [g for g in rec_groups if g in valid_groups] or ["researcher"]

        return parsed

    except Exception as exc:
        logger.warning("complexity_analysis_failed", error=str(exc))
        return default_result
    finally:
        await BrowserSessionManager.close_session(orchestrator_prov)
```

### 5. Wire into `run_agent_pipeline()` before orchestration

Insert right before the PHASE 1: ORCHESTRATING section:

```python
        # ---------------------------------------------------------
        # PRE-PHASE: COMPLEXITY ANALYSIS (Optional auto-scaling)
        # ---------------------------------------------------------
        auto_scale = True
        min_ag = 2
        max_ag = 5
        complexity_info: dict[str, Any] | None = None

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                try:
                    cfg_obj = json.loads(db_j.config_json) if db_j.config_json else {}
                    auto_scale = cfg_obj.get("auto_scale_agents", True)
                    min_ag = cfg_obj.get("min_agents", 2)
                    max_ag = cfg_obj.get("max_agents", 5)
                except Exception:
                    pass

        if auto_scale:
            complexity_info = await analyze_complexity(
                job_id=job_id,
                research_topic=research_topic,
                orchestrator_prov=orchestrator_prov,
                orch_config=orch_config,
                available_providers=delegated_providers or list(PROVIDER_CATALOG.keys()),
                min_agents=min_ag,
                max_agents=max_ag,
                cancel_event=cancel_event,
            )

            # Emit complexity event
            async with SessionLocal() as session:
                session.add(JobEvent(
                    job_id=job_id,
                    status="orchestrating",
                    event_type="complexity_analyzed",
                    step="complexity_analyzed",
                    message=f"Đánh giá độ phức tạp: {complexity_info.get('complexity_level', '?')} — "
                            f"Khuyến nghị {complexity_info.get('recommended_agent_count', '?')} tác nhân.",
                    data_json=json.dumps(complexity_info, ensure_ascii=False),
                ))
                await session.commit()
            notify_job_event(job_id)

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return
```

### 6. Update `build_orchestrator_prompt()` to use dynamic count

```diff
 def build_orchestrator_prompt(
     research_topic: str,
     allowed_providers: list[str] | None = None,
     provider_configs: dict[str, Any] | None = None,
     provider_capabilities: dict[str, Any] | None = None,
     context_summary: str | None = None,
+    complexity_info: dict[str, Any] | None = None,
 ) -> str:
+    # Determine agent count range
+    if complexity_info:
+        rec_count = complexity_info.get("recommended_agent_count", 3)
+        rec_groups = complexity_info.get("recommended_groups", ["researcher"])
+        count_instruction = f"Decompose the topic into exactly {rec_count} distinct sub-tasks."
+        group_instruction = f"Prioritize assigning agents to these role groups: {', '.join(rec_groups)}."
+    else:
+        count_instruction = "Decompose the topic into 2 to 5 distinct, non-overlapping specialized sub-topics."
+        group_instruction = ""

     # ... rest of prompt ...
     ## Rules:
-    - Decompose the topic into 2 to 5 distinct, non-overlapping specialized sub-topics.
+    - {count_instruction}
+    {f"- {group_instruction}" if group_instruction else ""}
```

Then update the call site in `run_agent_pipeline()`:

```diff
         orch_prompt = build_orchestrator_prompt(
             research_topic,
             allowed_providers=delegated_providers,
             provider_configs=provider_configs,
             provider_capabilities=provider_capabilities,
             context_summary=context_summary,
+            complexity_info=complexity_info,
         )
```

---

## Frontend Changes

### 1. Add auto-scale config to `AgentConfigScreen.tsx`

Add a section before the Sub-Providers Delegation:

```tsx
{/* Auto-Scale Agents */}
<div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 8, border: "1px solid #e2e8f0" }}>
  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
    <input
      type="checkbox"
      checked={autoScaleAgents}
      onChange={(e) => setAutoScaleAgents(e.target.checked)}
    />
    <span style={{ fontWeight: 600, fontSize: 13 }}>🧠 Auto-Scale Agent Count</span>
  </label>
  <p style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
    Automatically assess topic complexity and adjust agent count.
  </p>
  {autoScaleAgents && (
    <div style={{ marginTop: 10, display: "flex", gap: 16, alignItems: "center" }}>
      <label style={{ fontSize: 12 }}>
        Min:
        <input
          type="number"
          min={1} max={maxAgents}
          value={minAgents}
          onChange={(e) => setMinAgents(Number(e.target.value))}
          style={{ width: 50, marginLeft: 4, padding: "2px 6px", borderRadius: 4, border: "1px solid #cbd5e1" }}
        />
      </label>
      <label style={{ fontSize: 12 }}>
        Max:
        <input
          type="number"
          min={minAgents} max={10}
          value={maxAgents}
          onChange={(e) => setMaxAgents(Number(e.target.value))}
          style={{ width: 50, marginLeft: 4, padding: "2px 6px", borderRadius: 4, border: "1px solid #cbd5e1" }}
        />
      </label>
    </div>
  )}
</div>
```

### 2. Pass config in API request

```typescript
onStartAgentResearch({
  ...config,
  auto_scale_agents: autoScaleAgents,
  min_agents: minAgents,
  max_agents: maxAgents,
});
```

Store these in `config_json` on the backend (they'll be picked up from `cfg_obj` in the pipeline).

### 3. Show complexity badge in dispatch banner

**File**: `chatbot/src/components/agent/AgentDispatchBanner.tsx`

When `complexity_analyzed` event data is present, show a badge:

```tsx
const COMPLEXITY_STYLES: Record<string, { bg: string; text: string; icon: string }> = {
  low: { bg: "#d1fae5", text: "#065f46", icon: "🟢" },
  medium: { bg: "#fef3c7", text: "#92400e", icon: "🟡" },
  high: { bg: "#fee2e2", text: "#991b1b", icon: "🔴" },
};

// In the dispatch banner header:
{complexityLevel && (
  <span style={{
    fontSize: 10,
    padding: "2px 8px",
    borderRadius: 12,
    backgroundColor: COMPLEXITY_STYLES[complexityLevel]?.bg,
    color: COMPLEXITY_STYLES[complexityLevel]?.text,
    fontWeight: 600,
  }}>
    {COMPLEXITY_STYLES[complexityLevel]?.icon} {complexityLevel.toUpperCase()} complexity
  </span>
)}
```

### 4. Timeline events

The `complexity_analyzed` event will automatically appear in the ChronologicalTimeline.

---

## Testing Checklist

1. **Auto-scale enabled (default)** — verify complexity analysis runs and agent count adapts
2. **Auto-scale disabled** — verify orchestrator uses default 2–5 range
3. **Simple topic** — "What is Python?" → should recommend 2 agents
4. **Complex topic** — long multi-domain topic → should recommend 4-5+ agents
5. **Min/Max clamping** — verify recommended count stays within configured range
6. **Complexity analysis failure** — falls back to default count, pipeline continues
7. **SSE event** — verify `complexity_analyzed` event fires with assessment data
8. **Frontend badge** — verify complexity badge shows in dispatch banner
9. **Frontend slider** — verify min/max inputs work

---

## Files Modified (Summary)

| File | Change |
|---|---|
| `pc_chatbots/app/api/schemas.py` | Add `auto_scale_agents`, `min_agents`, `max_agents` to request |
| `pc_chatbots/app/orchestrator/agent_pipeline.py` | Add `build_complexity_analysis_prompt()`, `analyze_complexity()`, update `build_orchestrator_prompt()` signature, wire pre-phase |
| `chatbot/src/components/agent/AgentConfigScreen.tsx` | Add auto-scale toggle + min/max inputs |
| `chatbot/src/components/agent/AgentDispatchBanner.tsx` | Add complexity badge |

---

## Design Notes

### Why this is a "quick win"
- Only 1 extra LLM call (with a short 60s timeout)
- No new DB columns needed (complexity data stored in events)
- No new pipeline phases — just modifies the existing orchestration step
- Falls back gracefully on failure

### Latency trade-off
The complexity analysis adds ~5-15 seconds before orchestration. This is acceptable because:
- The orchestrator call itself takes 15-60s
- The time saved by using fewer agents for simple topics far outweighs the analysis cost
- For complex topics, the user gets a better result with more agents
