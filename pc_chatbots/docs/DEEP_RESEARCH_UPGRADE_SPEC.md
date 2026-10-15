# Deep Research Orchestrator — Multi-Phase Architecture & Implementation Specification

## 1. System Overview & Target Architecture

This specification upgrades a linear 3-step research pipeline (`User Input` -> `Orchestrator` -> `Sub-Agents` -> `Lead Provider`) into a **Topology-Aware, Reflective Deep Research System**.

### High-Level Execution Graph
```text
[User Request (Topic + 3-Axis Config)]
          │
          ▼
[Node 1: Orchestrator (Planner & Router)]
          │
          ├──► (Phase 4 Optional) [Pre-Flight Plan Approval Gate (HITL)]
          │
          ▼
[Node 2: Parallel Sub-Agents (Persona & Stance-Driven Search)] ◄───┐
          │    (Shared State: visited_urls deduplication)          │
          ▼                                                        │
[Node 3: Critic / Evaluator (Coverage & Contradiction Check)] ─────┘
          │    (Loop if is_sufficient == false & iter < max_iter)
          ▼
[Node 4: Lead Provider (Evidence-Bound Synthesis & Tone Formatting)]
          │
          ▼
[Final Cited Report]
```

---

## 2. Global State & Data Contracts

All nodes read from and write to a unified `ResearchState` object.

### 2.1 Core Enumerations
```json
{
  "ResearchMethodology": [
    "360_overview",
    "adversarial_debate",
    "pros_and_cons",
    "comparative_matrix",
    "fact_check"
  ],
  "DepthProfile": [
    "fast",
    "deep"
  ],
  "OutputTone": [
    "professional",
    "academic",
    "executive_brief",
    "technical_rfc",
    "investigative"
  ],
  "Stance": [
    "pro",
    "con",
    "neutral",
    "rebuttal"
  ],
  "SourceTier": [
    "primary_data_or_paper",
    "official_documentation",
    "industry_analysis",
    "community_or_opinion"
  ]
}
```

### 2.2 Unified Global State (`ResearchState`)
```typescript
interface ResearchState {
  // 1. User Inputs & Configuration (3-Axis Control)
  topic: string;
  methodology: "360_overview" | "adversarial_debate" | "pros_and_cons" | "comparative_matrix" | "fact_check";
  depth_profile: "fast" | "deep";
  output_tone: "professional" | "academic" | "executive_brief" | "technical_rfc" | "investigative";

  // 2. Execution Budget & Loop Counters
  iteration_count: number;
  max_iterations: number;         // Derived from depth_profile (fast=1, deep=3)
  max_parallel_agents: number;    // Derived from depth_profile (fast=3, deep=6)

  // 3. Orchestrator Planning State
  plan_approved: boolean;
  core_thesis_or_scope: string;
  evaluation_dimensions: string[];
  active_tasks: DirectedTask[];   // Tasks dispatched to Sub-Agents in current iteration

  // 4. Shared Memory & Evidence Bank (Append/Union Reducers)
  visited_urls: string[];         // Set-union reducer across all sub-agent runs
  evidence_bank: EvidenceBlock[]; // Append reducer storing all verified atomic findings

  // 5. Critic State
  latest_critique?: CriticEvaluation;

  // 6. Final Deliverable
  final_report?: string;
}
```

---

## Phase 1: Data Contract Foundation & URL Deduplication

### Objective
Eliminate information loss ("telephone game" summarization) between Sub-Agents and the Lead Provider by replacing free-form prose outputs with structured `EvidenceBlock` JSON arrays, and prevent parallel Sub-Agents from scraping duplicate URLs.

### 1.1 Input / Output Specifications

#### Sub-Agent Input (`SubAgentInput`)
```json
{
  "task_id": "task_01",
  "sub_topic": "Serverless cold start latency in high-throughput APIs",
  "search_queries": [
    "AWS Lambda cold start latency benchmarks 2025 2026",
    "serverless vs containers p99 latency production"
  ],
  "excluded_urls": [
    "[https://example.com/already-scraped-url-1](https://example.com/already-scraped-url-1)"
  ]
}
```

#### Sub-Agent Output (`SubAgentOutput`)
Sub-Agents **must not** return prose essays. They must return strict JSON matching this contract:
```json
{
  "task_id": "task_01",
  "newly_visited_urls": [
    "[https://benchmark-site.org/serverless-2026](https://benchmark-site.org/serverless-2026)"
  ],
  "evidence_blocks": [
    {
      "evidence_id": "ev_01_a",
      "sub_topic": "Serverless cold start latency in high-throughput APIs",
      "evaluation_dimension": "Latency & Performance",
      "claim": "SnapStart and预warmed microVMs reduce Java/Python cold starts by up to 85%, but p99 spikes remain 3x higher than dedicated containers under burst traffic.",
      "verbatim_metric_or_quote": "P99 latency reached 420ms during 10x traffic bursts compared to 135ms on Kubernetes pods.",
      "source_url": "[https://benchmark-site.org/serverless-2026](https://benchmark-site.org/serverless-2026)",
      "source_title": "Cloud Compute Latency Report 2026",
      "source_tier": "primary_data_or_paper",
      "stance": "neutral",
      "confidence_score": 0.92
    }
  ]
}
```

### 1.2 Implementation Tasks
1. **Refactor Sub-Agent Output Parser:** Enforce structured JSON output (`SubAgentOutput`) using structured outputs / JSON schema validation.
2. **Implement Shared URL Deduplication Filter:**
   - Before any Sub-Agent invokes its web scraper/reader tool on a search result URL, check if `url in state.visited_urls`.
   - If present, skip the URL and select the next ranked search result.
   - Immediately register newly scraped URLs into `state.visited_urls`.
3. **Update Lead Provider Prompt to Consume `evidence_bank`:**
   - Feed the aggregated `state.evidence_bank` JSON directly into the Lead Provider.
   - Enforce strict inline citation binding: every quantitative claim in the final report must cite `[evidence_id]` mapped to its `source_url`.

### 1.3 Phase 1 Evaluation & Definition of Done (DoD)
- [ ] **Zero Prose Hand-offs:** Sub-Agents output 100% valid `SubAgentOutput` JSON objects.
- [ ] **Zero URL Duplication:** Across parallel sub-agents in a single run, no URL is scraped more than once (`duplicate_scrape_count == 0`).
- [ ] **100% Citation Grounding:** Every metric or factual claim in the Lead Provider's output links to a valid `source_url` from `evidence_bank`.

---

## Phase 2: Dynamic Research Topologies (Research Types)

### Objective
Upgrade `methodology` from a cosmetic formatting instruction into a structural routing mechanism that changes how the **Orchestrator** decomposes the topic, how **Sub-Agents** formulate search queries, and how the **Lead Provider** synthesizes the conclusion.

### 2.1 Orchestrator Task Schema (`DirectedTask`)
```json
{
  "task_id": "bull_cost_01",
  "assigned_persona": "Bull Proponent — Cost Efficiency Advocate",
  "evaluation_dimension": "Total Cost of Ownership (TCO)",
  "target_angle": "Prove that solution X reduces operational and infrastructure costs at scale.",
  "required_stance": "pro",
  "search_queries": [
    "solution X cost reduction case study ROI",
    "migrating to X saved engineering hours"
  ],
  "negative_search_terms": []
}
```

### 2.2 Methodology Routing Rules

Implement a strategy router inside the **Orchestrator** and **Lead Provider** based on `state.methodology`:

| Methodology | Orchestrator Decomposition Strategy | Sub-Agent Persona & Query Polarity | Lead Provider Synthesis Structure |
| :--- | :--- | :--- | :--- |
| **`360_overview`** | Splits topic into MECE (Mutually Exclusive, Collectively Exhaustive) thematic pillars. | **Domain Researcher** (`stance: neutral`). Queries for comprehensive facts, architecture, market data, and timelines. | **Thematic Synthesizer:** Organizes report by domain pillars with an executive summary. |
| **`adversarial_debate`** | Formulates 2–3 controversial **Core Theses** (`core_thesis_or_scope`). For *each* thesis, spawns paired agents. | **Bull Agent (`stance: pro`)** vs. **Bear Agent (`stance: con`)**. Bull queries success stories/benchmarks; Bear explicitly queries `"failure"`, `"post-mortem"`, `"drawbacks"`, `"why we left"`. | **Arbiter / Judge:** Structures report as: 1. Core Thesis, 2. Case for the Affirmative, 3. Case for the Negative, 4. Evidence Quality Audit & Final Verdict. |
| **`pros_and_cons`** | Defines 3–5 **Evaluation Dimensions** (e.g., Cost, Scalability, DX, Security). | **Dimension Stress-Tester:** For each dimension, explicitly extracts both best-case advantages (`pro`) and worst-case bottlenecks/edge cases (`con`). | **Decision Architect:** Builds a Dimension-by-Dimension Trade-off Matrix followed by *"When to Adopt vs. When to Avoid"* decision rules. |
| **`comparative_matrix`** | Extracts entities `[Entity A, Entity B, ...]` and standardized `evaluation_dimensions`. | **Head-to-Head Benchmark Agent:** Runs direct comparative queries (`"Entity A vs Entity B [dimension] benchmark"`) rather than researching entities in isolation. | **Comparative Analyst:** Generates a normalized side-by-side Markdown comparison table across all dimensions + scenario-based winner recommendations. |
| **`fact_check`** | Extracts specific claims, marketing promises, or common assumptions from the prompt. | **Forensic Verifier:** Hunts strictly for `primary_data_or_paper` and `official_documentation` to prove or refute each claim. | **Investigative Editor:** Categorizes claims into *Verified*, *Partially True / Context-Dependent*, and *Unverified / Hype*. |

### 2.3 System Prompt Templates (Phase 2)

#### Orchestrator System Prompt Snippet
```text
You are the Master Research Orchestrator.
Analyze the user's `topic` using the requested `methodology`: {{methodology}}.

RULES BY METHODOLOGY:
- If `adversarial_debate`: Identify the central controversy. Define 2-3 evaluation dimensions. For EACH dimension, generate TWO DirectedTasks: one with `assigned_persona: "Bull Proponent"` (`required_stance: "pro"`) and one with `assigned_persona: "Bear Skeptic"` (`required_stance: "con"`). Bear agents MUST include failure-oriented keywords in their `search_queries` (e.g., "issues", "limitations", "post-mortem", "criticism").
- If `pros_and_cons`: Decompose the topic into {{max_parallel_agents}} orthogonal Evaluation Dimensions (e.g., Performance, Cost, Maintainability, Ecosystem). Assign each Sub-Agent to stress-test one dimension for both advantages and hidden pitfalls.
- If `comparative_matrix`: Identify the subjects being compared and define standardized benchmark criteria. Generate tasks that query head-to-head comparisons per criterion.
```

#### Sub-Agent System Prompt Snippet
```text
You are a Specialized Research Sub-Agent operating under the persona: {{assigned_persona}}.
Your target evaluation dimension is: {{evaluation_dimension}}.
Your required analytical stance is: {{required_stance}}.

INSTRUCTIONS:
1. Execute searches focused on `target_angle`. Skip any URL present in `excluded_urls`.
2. Extract concrete facts, numbers, benchmarks, and real-world post-mortems into `evidence_blocks`.
3. Tag every `EvidenceBlock` accurately with its `stance` ("pro", "con", "neutral", "rebuttal") and `evaluation_dimension`.
4. Do NOT fabricate metrics. If evidence for your assigned stance is weak or non-existent, record what the primary sources actually state and lower the `confidence_score`.
```

### 2.4 Phase 2 Evaluation & Definition of Done (DoD)
- [ ] **Stance Distribution Check:** In `adversarial_debate` and `pros_and_cons` modes, `evidence_bank` contains at least **30% `pro`** and **30% `con`** evidence blocks.
- [ ] **Dimensional Alignment:** Every `pro` and `con` evidence block maps to a shared `evaluation_dimension` defined by the Orchestrator (ensuring direct clash of arguments rather than unrelated points).
- [ ] **Structural Adaptation:** The Lead Provider output dynamically renders Verdict sections for `adversarial_debate`, Trade-off Matrices for `pros_and_cons`, and Side-by-Side Tables for `comparative_matrix`.

---

## Phase 3: Iterative Reflection & Critic Loop

### Objective
Insert a **Critic / Gap-Analyzer Node** between the Sub-Agents and the Lead Provider to detect unanswered dimensions, thin evidence, or contradicting metrics across Sub-Agents, triggering targeted follow-up searches before final synthesis.

### 3.1 Input / Output Specifications

#### Critic Input
- `topic`, `methodology`, `evaluation_dimensions`
- `evidence_bank` (all `EvidenceBlock[]` collected so far)
- `iteration_count` and `max_iterations`

#### Critic Output (`CriticEvaluation`)
```json
{
  "is_sufficient": false,
  "coverage_score": 0.68,
  "dimension_coverage": {
    "Latency & Performance": "complete",
    "Total Cost of Ownership (TCO)": "insufficient_con_evidence",
    "Security & Compliance": "missing"
  },
  "detected_contradictions": [
    {
      "dimension": "Total Cost of Ownership (TCO)",
      "description": "ev_01_a claims 40% cost reduction, while ev_02_c claims 2x higher bill at scale without specifying traffic thresholds.",
      "resolution_query": "serverless vs kubernetes cost breakeven traffic threshold requests per second"
    }
  ],
  "follow_up_tasks": [
    {
      "task_id": "patch_iter2_01",
      "assigned_persona": "Forensic Verifier",
      "evaluation_dimension": "Total Cost of Ownership (TCO)",
      "target_angle": "Identify exact traffic volume or RPS where serverless becomes more expensive than containers.",
      "required_stance": "con",
      "search_queries": [
        "serverless vs containers cost breakeven point RPS",
        "high traffic AWS Lambda bill shock case study"
      ]
    }
  ]
}
```

### 3.2 Deterministic Loop Routing Logic
Implement the conditional edge after the Critic Node:

```python
def route_after_critic(state: ResearchState) -> str:
    critique = state.latest_critique
    
    # Hard stop condition to prevent infinite loops
    if state.iteration_count >= state.max_iterations:
        return "lead_provider"
        
    # Quality threshold met
    if critique.is_sufficient or critique.coverage_score >= 0.85:
        return "lead_provider"
        
    # If gaps or contradictions exist and budget remains, dispatch follow-up tasks
    if len(critique.follow_up_tasks) > 0:
        state.active_tasks = critique.follow_up_tasks
        state.iteration_count += 1
        return "sub_agents"
        
    return "lead_provider"
```

### 3.3 Lead Provider Contradiction Handling
When the Critic detects contradictions that remain unresolved or nuance-dependent after `max_iterations`, pass `detected_contradictions` to the **Lead Provider** so it explicitly addresses the discrepancy in the final report (e.g., *"Sources diverge on X due to differing workload assumptions: [1] vs [2]"*) rather than silently picking one number.

### 3.4 Phase 3 Evaluation & Definition of Done (DoD)
- [ ] **Guaranteed Termination:** 100% of runs terminate at or before `state.max_iterations`.
- [ ] **Coverage Lift:** On complex topics where Iteration 1 yields `coverage_score < 0.75`, Iteration 2 increases `coverage_score` to `>= 0.85`.
- [ ] **Contradiction Transparency:** Conflicting metrics in `evidence_bank` are either resolved via a follow-up query or explicitly contrasted with citations in the final report.

---

## Phase 4: Pre-Flight Scope Alignment & 3-Axis API Controls

### Objective
Decouple user configuration into three orthogonal axes (`methodology`, `depth_profile`, `output_tone`) and introduce a fast **Pre-Flight Plan Preview** step so users can approve or adjust the research dimensions before heavy token execution begins.

### 4.1 3-Axis Configuration Mapping

#### API Request Payload (`CreateResearchJobRequest`)
```json
{
  "topic": "Adopting Rust vs Go for high-frequency trading microservices",
  "methodology": "comparative_matrix",
  "depth_profile": "deep",
  "output_tone": "technical_rfc",
  "require_plan_approval": true
}
```

#### Depth Profile Presets
| Parameter | `fast` Profile | `deep` Profile |
| :--- | :--- | :--- |
| `max_parallel_agents` (Initial Pass) | `3` | `6` |
| `max_iterations` (Critic Loops) | `1` (Bypass Critic re-search) | `3` (Initial + up to 2 Critic patch loops) |
| `max_urls_per_agent` | `3` | `6` |
| Target Latency | `< 30 seconds` | `60 – 180 seconds` |

### 4.2 Pre-Flight Plan Blueprint (`ResearchPlanBlueprint`)
When `require_plan_approval == true`, the Orchestrator executes a lightweight planning call (< 2 seconds) and pauses graph execution (Human-in-the-Loop interrupt), returning:

```json
{
  "job_id": "res_99281",
  "status": "awaiting_plan_approval",
  "proposed_blueprint": {
    "interpreted_thesis": "Head-to-head architectural evaluation of Rust vs. Go for low-latency HFT microservices.",
    "methodology": "comparative_matrix",
    "evaluation_dimensions": [
      "Tail Latency (p99/p99.9) & Garbage Collection Impact",
      "Memory Safety & Concurrency Primitives",
      "Ecosystem Maturity (FIX protocol, kernel bypass/DPDK)",
      "Developer Velocity & Onboarding Cost"
    ],
    "planned_sub_agents": 4,
    "estimated_depth": "deep (up to 3 iterations)"
  }
}
```

### 4.3 Resume / Override Endpoint (`ApproveResearchPlanRequest`)
The user can approve the blueprint as-is or modify `evaluation_dimensions` before triggering the Sub-Agents:
```json
{
  "job_id": "res_99281",
  "approved": true,
  "modified_evaluation_dimensions": [
    "Tail Latency (p99/p99.9) & Garbage Collection Impact",
    "Kernel Bypass (DPDK / io_uring) Support",
    "Hiring & Team Ramp-up Cost"
  ]
}
```

### 4.4 Phase 4 Evaluation & Definition of Done (DoD)
- [ ] **Orthogonal Control Verification:** Any combination of `methodology` (5 options) $\times$ `depth_profile` (2 options) $\times$ `output_tone` (5 options) executes cleanly without prompt conflicts.
- [ ] **Pre-Flight Latency:** The `ResearchPlanBlueprint` generates in `< 2.5 seconds`.
- [ ] **State Resumption:** Modifying `evaluation_dimensions` in the approval payload dynamically updates the `DirectedTask[]` list dispatched to Sub-Agents.

---

## 5. Recommended Implementation Checklist for Antigravity

Execute the implementation in the following strict sequence:

- [ ] **Step 1 (Schemas & State):** Create `types/research_state.ts` (or `schemas/research_state.py`) containing `ResearchState`, `EvidenceBlock`, `DirectedTask`, and `CriticEvaluation`.
- [ ] **Step 2 (Phase 1 - Sub-Agent Refactor):** Update the Sub-Agent runner to accept `excluded_urls` and return validated `SubAgentOutput` JSON with `EvidenceBlock[]`.
- [ ] **Step 3 (Phase 1 - Lead Provider Citation Binding):** Update the Lead Provider prompt to synthesize strictly from `state.evidence_bank` with inline `[evidence_id]` citations.
- [ ] **Step 4 (Phase 2 - Orchestrator Methodology Router):** Implement the prompt and schema routing for `360_overview`, `adversarial_debate`, `pros_and_cons`, `comparative_matrix`, and `fact_check`.
- [ ] **Step 5 (Phase 3 - Critic Node & Loop Edge):** Implement the `Critic` node and wire the conditional edge `route_after_critic` back to the Sub-Agent dispatcher with `max_iterations` enforcement.
- [ ] **Step 6 (Phase 4 - 3-Axis Config & Plan Preview Gate):** Expose `methodology`, `depth_profile`, and `output_tone` at the API boundary and add the optional `awaiting_plan_approval` interrupt state.