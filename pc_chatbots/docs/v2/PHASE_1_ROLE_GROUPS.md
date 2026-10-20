# Phase 1: Agent Role Groups & Structured Dispatch

> **Effort**: ~1–2 days | **Risk**: Low | **Branch**: `v2`
> **Depends on**: Nothing (first step)
> **Required before**: Phase 2 (Fact-Check), Phase 6 (Dynamic Scaling)

---

## Goal

Evolve the flat `agents_dispatch` list into **4 logical role groups** so the orchestrator can assign semantic roles to each sub-agent. This lays the foundation for later phases (fact-checking uses `fact_checker` role, debate uses `red_team` role).

### Role Groups
| Role Group | Purpose | Example providers |
|---|---|---|
| `researcher` | Core topic investigation | ChatGPT, Gemini, DeepSeek |
| `infra` | Data/cost/benchmark research | Perplexity, Copilot |
| `fact_checker` | Verify claims with web search | Perplexity, 9router |
| `red_team` | Adversarial critique | Claude, ChatGPT |

---

## Acceptance Criteria

- [x] `AgentDispatchItem` schema includes `role_group` field with default `"researcher"`
- [x] `build_orchestrator_prompt()` instructs the LLM to assign `role_group` to each subtask
- [x] Old jobs without `role_group` still parse correctly (backward-compat)
- [x] Frontend `AgentDispatchPlanItem` type includes `role_group`
- [x] Dispatch banner shows color-coded role badges
- [x] All existing tests still pass

---

## Backend Changes

### 1. Update `AgentDispatchItem` schema

**File**: `app/api/schemas.py` (line ~25)

```diff
 class AgentDispatchItem(BaseModel):
     id: str
     name: str
     config: dict[str, Any] = Field(default_factory=dict)
     sub_topic: str
     question: str
+    role_group: str = Field(default="researcher")
```

### 2. Update `OrchestratorOutput` — no changes needed
The `OrchestratorOutput` uses `AgentDispatchItem`, so it inherits the new field automatically. The default value ensures backward-compat.

### 3. Update `build_orchestrator_prompt()` in `agent_pipeline.py`

**File**: `app/orchestrator/agent_pipeline.py` (function starting ~line 126)

Add role group instructions to the prompt. Modify the `## Rules:` section and `## Output JSON Schema:` section:

```diff
 ## Rules:
 - Decompose the topic into 2 to 5 distinct, non-overlapping specialized sub-topics.
 - Assign each sub-topic to the provider best suited for that angle among the allowed providers, matching their active capabilities and strengths described above.
+- Assign each sub-task a "role_group" from: "researcher" (core investigation), "infra" (data/benchmark/cost), "fact_checker" (verification), "red_team" (critique/counterargument).
+- Most sub-tasks should be "researcher" or "infra". Only assign "fact_checker" or "red_team" if the topic specifically benefits from verification or critical analysis.
 - In each "agents_dispatch" item, provide a valid "config" object that matches the provider's active DOM setting and expected schema.
```

Update the JSON Schema section:

```diff
 ## Output JSON Schema:
 {{
   "research_topic": "{research_topic}",
   "agents_dispatch": [
     {{
       "id": "<provider_id>",
       "name": "<provider_name>",
       "config": {{ ... }},
+      "role_group": "<researcher|infra|fact_checker|red_team>",
       "sub_topic": "<Brief specialized sub-topic title>",
       "question": "<Detailed research prompt tailored for this provider's capabilities>"
     }}
   ]
 }}
```

### 4. Update fallback dispatch plan

**File**: `app/orchestrator/agent_pipeline.py` (~line 537-552)

Add `role_group` to the fallback dispatch items:

```diff
             dispatch_items = [
                 {
                     "id": p1,
                     "name": p1_info["name"],
                     "config": p1_info["default_config"],
+                    "role_group": "researcher",
                     "sub_topic": "Nền tảng lý thuyết & Giải thuật",
                     "question": f"Phân tích chuyên sâu...",
                 },
                 {
                     "id": p2,
                     "name": p2_info["name"],
                     "config": p2_info["default_config"],
+                    "role_group": "infra",
                     "sub_topic": "Dữ liệu ứng dụng thực tế...",
                     "question": f"Tìm kiếm các số liệu...",
                 },
             ]
```

### 5. No DB changes needed
`role_group` is stored inside `orchestrator_dispatch_json` (which is already a JSON text column on `Job`). No migration required.

---

## Frontend Changes

### 1. Update TypeScript types

**File**: `chatbot/src/types/chat.ts` (~line 78)

```diff
 export interface AgentDispatchPlanItem {
   id: string;
   name: string;
   config?: Record<string, any>;
   sub_topic: string;
   question: string;
   branch_index?: number;
   provider_role_key?: string;
   conversation_url?: string;
+  role_group?: string;
 }
```

### 2. Update `AgentDispatchBanner.tsx`

Add color-coded role badges next to each agent in the dispatch plan display.

Suggested role badge colors:
```typescript
const ROLE_GROUP_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  researcher: { bg: "#dbeafe", text: "#1d4ed8", label: "Researcher" },
  infra:      { bg: "#fef3c7", text: "#92400e", label: "Infra/Data" },
  fact_checker: { bg: "#d1fae5", text: "#065f46", label: "Fact-Check" },
  red_team:   { bg: "#fee2e2", text: "#991b1b", label: "Red Team" },
};
```

Add a small badge next to each dispatched agent:
```tsx
{item.role_group && ROLE_GROUP_STYLES[item.role_group] && (
  <span style={{
    fontSize: 10,
    padding: "1px 6px",
    borderRadius: 4,
    backgroundColor: ROLE_GROUP_STYLES[item.role_group].bg,
    color: ROLE_GROUP_STYLES[item.role_group].text,
    fontWeight: 600,
  }}>
    {ROLE_GROUP_STYLES[item.role_group].label}
  </span>
)}
```

---

## Testing Checklist

1. **Start an agent research job** — verify the orchestrator output now includes `role_group` in each dispatched item
2. **Check fallback path** — force an invalid JSON response from the orchestrator and verify fallback items have `role_group`
3. **Check backward-compat** — load an old job from the DB that was created before this change. It should still render correctly with `role_group` defaulting to `"researcher"`
4. **Frontend badge** — verify the dispatch banner shows colored role badges
5. **SSE events** — verify `role_group` appears in the `orchestrator_result` event data

---

## Files Modified (Summary)

| File | Change |
|---|---|
| `pc_chatbots/app/api/schemas.py` | Add `role_group` field to `AgentDispatchItem` |
| `pc_chatbots/app/orchestrator/agent_pipeline.py` | Update prompt + fallback dispatch |
| `chatbot/src/types/chat.ts` | Add `role_group` to `AgentDispatchPlanItem` |
| `chatbot/src/components/agent/AgentDispatchBanner.tsx` | Add role badge rendering |
