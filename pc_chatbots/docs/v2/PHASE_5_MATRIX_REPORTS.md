# Phase 5: Structured Report Output (Comparative Matrix)

> **Effort**: ~2–3 days | **Risk**: Low | **Branch**: `v2`
> **Depends on**: Phase 2 (Fact-Check — for verdict data) — works without it too
> **Required before**: None (independent feature)

---

## Goal

Add a **structured report format option** alongside the existing free-form Markdown report. When `report_format = "matrix"` or `"hybrid"`, the lead synthesizer produces a **Comparative Matrix** (solutions compared across dimensions like Cost/Performance/Complexity) plus explicit Pros/Cons per option.

### This Phase Is Independent
Unlike Phases 3/4, this phase doesn't add a new pipeline stage. It changes the **output format** of the existing Lead Synthesis phase. It can be implemented in parallel with or before Phases 3/4.

---

## Acceptance Criteria

- [x] New `report_format` field in `AgentResearchRequest`: `"narrative"` (default/current), `"matrix"`, or `"hybrid"`
- [x] `"matrix"` format produces a JSON-structured report with comparison table + Pros/Cons
- [x] `"hybrid"` format produces both narrative Markdown AND a matrix section
- [x] `"narrative"` behaves exactly as current (no regression)
- [x] Backend converts matrix JSON to well-formatted Markdown for storage
- [x] Frontend can render the matrix as a sortable table
- [x] Frontend can toggle between narrative and matrix view for `"hybrid"` reports

---

## Backend Changes

### 1. Add `report_format` to `AgentResearchRequest`

**File**: `app/api/schemas.py`

```diff
+ReportFormat = Literal["narrative", "matrix", "hybrid"]

 class AgentResearchRequest(BaseModel):
     query: str = Field(min_length=1, max_length=20_000)
     # ... existing fields ...
     tone: str = Field(default="professional")
+    report_format: ReportFormat = Field(default="narrative")
```

### 2. Add DB column to `Job`

**File**: `app/core/models.py`

```diff
 class Job(SQLModel, table=True):
     # ... existing fields ...
     tone: str | None = None
+    report_format: str = "narrative"
+    report_matrix_json: str | None = None
```

### 3. Store report_format when creating job

**File**: `app/api/routes.py`

```diff
     job = Job(
         id=job_id,
         query=req.query,
         # ... existing fields ...
+        report_format=req.report_format,
     )
```

### 4. Build matrix report prompt

**File**: `app/orchestrator/agent_pipeline.py`

```python
def build_matrix_report_prompt(
    research_topic: str,
    findings: list[dict[str, Any]],
    tone: str,
    context_summary: str | None = None,
    fact_check_claims: list[dict[str, Any]] | None = None,
    debate_transcript: list[dict[str, Any]] | None = None,
    consensus_result: dict[str, Any] | None = None,
) -> str:
    """Build a prompt that produces a structured Comparative Matrix report."""
    tone_directive = TONE_INSTRUCTIONS.get(tone.lower(), TONE_INSTRUCTIONS["professional"])

    sections: list[str] = []
    for item in findings:
        prov = item.get("provider", "AI")
        branch = item.get("branch", "Research")
        ans = item.get("answer_md", "").strip()
        sections.append(f"### Branch: {branch} (by {prov})\n\n{ans}")
    findings_text = "\n\n---\n\n".join(sections) if sections else "No detailed data."

    context_section = ""
    if context_summary and context_summary.strip():
        context_section = f"\n## Previous Research Context:\n{context_summary.strip()}\n"

    fc_section = ""
    if fact_check_claims:
        disputed = [c for c in fact_check_claims if c.get("verdict") in ("unsupported", "conflict")]
        if disputed:
            fc_section = "\n## Disputed Claims:\n" + "\n".join(
                f"- ⚠️ \"{c.get('claim', '')}\" [{c.get('verdict', '')}]" for c in disputed[:10]
            ) + "\n"

    consensus_section = ""
    if consensus_result and consensus_result.get("final_scores"):
        scores_lines = []
        for sc in consensus_result["final_scores"]:
            thesis = next((t for t in consensus_result.get("theses", []) if t.get("id") == sc.get("id")), {})
            scores_lines.append(f"- {sc.get('id')}: \"{thesis.get('thesis', '')}\" — {sc.get('mean', '?')}/5")
        consensus_section = "\n## Consensus Scores:\n" + "\n".join(scores_lines) + "\n"

    return f"""You are the Lead Research Synthesizer producing a STRUCTURED COMPARATIVE REPORT.

## Research Topic: {research_topic}
{context_section}
## Research Findings:
{findings_text}
{fc_section}
{consensus_section}
## Your Task:
Produce a structured report in the following JSON format:

```json
{{
  "title": "<Report title>",
  "executive_summary": "<2-3 sentence overview>",
  "alternatives": [
    {{
      "name": "<Solution/Approach name>",
      "description": "<Brief description>",
      "scores": {{
        "cost": <1-5>,
        "performance": <1-5>,
        "complexity": <1-5>,
        "maturity": <1-5>,
        "scalability": <1-5>
      }},
      "pros": ["<pro 1>", "<pro 2>", "..."],
      "cons": ["<con 1>", "<con 2>", "..."]
    }}
  ],
  "recommendation": "<Which alternative is recommended and why>",
  "caveats": ["<caveat 1>", "<caveat 2>"],
  "disagreements": ["<area of disagreement 1>"]
}}
```

## Rules:
- Compare 2-6 alternatives/approaches found in the research.
- Score each on the 5 dimensions (1=worst, 5=best).
- List 2-5 specific pros and cons per alternative.
- Be objective — don't oversell any option.
- If the research doesn't support a comparison format, adapt the alternatives to represent different perspectives or approaches.

## Tone: {tone_directive}

Output ONLY the JSON. No markdown fences around it, no explanations."""


def render_matrix_to_markdown(matrix_data: dict[str, Any]) -> str:
    """Convert a structured matrix JSON into formatted Markdown."""
    md = f"# {matrix_data.get('title', 'Research Report')}\n\n"
    md += f"## Executive Summary\n{matrix_data.get('executive_summary', '')}\n\n"

    alternatives = matrix_data.get("alternatives", [])
    if alternatives:
        # Build comparison table
        dimensions = ["cost", "performance", "complexity", "maturity", "scalability"]
        dim_labels = {"cost": "💰 Cost", "performance": "⚡ Performance", "complexity": "🔧 Complexity", "maturity": "📊 Maturity", "scalability": "📈 Scalability"}

        md += "## Comparative Matrix\n\n"
        header = "| Dimension | " + " | ".join(a.get("name", f"Option {i+1}") for i, a in enumerate(alternatives)) + " |\n"
        separator = "|---|" + "|".join("---" for _ in alternatives) + "|\n"
        md += header + separator

        for dim in dimensions:
            row = f"| {dim_labels.get(dim, dim)} | "
            row += " | ".join(
                "⭐" * a.get("scores", {}).get(dim, 0) + f" ({a.get('scores', {}).get(dim, '?')}/5)"
                for a in alternatives
            )
            row += " |\n"
            md += row

        md += "\n"

        # Pros/Cons per alternative
        for alt in alternatives:
            md += f"### {alt.get('name', 'Option')}\n"
            md += f"{alt.get('description', '')}\n\n"
            if alt.get("pros"):
                md += "**✅ Pros:**\n" + "\n".join(f"- {p}" for p in alt["pros"]) + "\n\n"
            if alt.get("cons"):
                md += "**❌ Cons:**\n" + "\n".join(f"- {c}" for c in alt["cons"]) + "\n\n"

    if matrix_data.get("recommendation"):
        md += f"## 🎯 Recommendation\n{matrix_data['recommendation']}\n\n"

    if matrix_data.get("caveats"):
        md += "## ⚠️ Caveats\n" + "\n".join(f"- {c}" for c in matrix_data["caveats"]) + "\n\n"

    if matrix_data.get("disagreements"):
        md += "## 🔀 Disagreements & Open Questions\n" + "\n".join(f"- {d}" for d in matrix_data["disagreements"]) + "\n"

    return md
```

### 5. Wire matrix format into the Lead Synthesis phase

In `run_agent_pipeline()`, replace the lead prompt selection based on `report_format`:

```python
        # Determine report format
        report_format = "narrative"
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                report_format = getattr(db_j, "report_format", "narrative")

        # Build the appropriate prompt
        if report_format == "matrix":
            lead_prompt = build_matrix_report_prompt(
                research_topic, runs, tone,
                context_summary=context_summary,
                fact_check_claims=fact_check_claims if 'fact_check_claims' in dir() else None,
                debate_transcript=debate_transcript if 'debate_transcript' in dir() else None,
                consensus_result=consensus_result if 'consensus_result' in dir() else None,
            )
        elif report_format == "hybrid":
            # For hybrid: generate BOTH narrative and matrix
            lead_prompt = build_lead_prompt(research_topic, runs, tone, context_summary=context_summary, ...)
            # Matrix will be generated in a second call (see below)
        else:
            lead_prompt = build_lead_prompt(research_topic, runs, tone, context_summary=context_summary, ...)
```

For `"matrix"` format, post-process the lead response:

```python
        if report_format in ("matrix", "hybrid"):
            try:
                matrix_json = _clean_json_str(lead_res.answer_markdown) if report_format == "matrix" else None
                if matrix_json:
                    matrix_data = json.loads(matrix_json)
                    final_report = render_matrix_to_markdown(matrix_data)
                    # Also store raw JSON for frontend rendering
                    async with SessionLocal() as session:
                        db_j = await session.get(Job, job_id)
                        if db_j is not None:
                            db_j.report_matrix_json = json.dumps(matrix_data, ensure_ascii=False)
                            await session.commit()
            except Exception as mx_err:
                logger.warning("matrix_parse_failed", error=str(mx_err))
                # Fallback: use raw text as-is
                final_report = lead_res.answer_markdown
```

### 6. Expose matrix data in API response

**File**: `app/api/schemas.py`

```diff
 class ResearchResponse(BaseModel):
     # ... existing fields ...
     report_markdown: str | None
+    report_format: str | None = None
+    report_matrix: dict[str, Any] | None = None
```

**File**: `app/api/routes.py` — in `_job_response()`:

```diff
     return ResearchResponse(
         # ... existing fields ...
+        report_format=getattr(job, "report_format", "narrative"),
+        report_matrix=_safe_json_loads(getattr(job, "report_matrix_json", None), None),
     )
```

---

## Frontend Changes

### 1. Add types

**File**: `chatbot/src/types/chat.ts`

```typescript
export interface MatrixAlternative {
  name: string;
  description: string;
  scores: {
    cost: number;
    performance: number;
    complexity: number;
    maturity: number;
    scalability: number;
  };
  pros: string[];
  cons: string[];
}

export interface MatrixReport {
  title: string;
  executive_summary: string;
  alternatives: MatrixAlternative[];
  recommendation: string;
  caveats: string[];
  disagreements: string[];
}
```

Add to `Message`:
```diff
 export interface Message {
   // ... existing fields ...
+  report_format?: string;
+  report_matrix?: MatrixReport;
 }
```

### 2. Add report format toggle to `AgentConfigScreen.tsx`

```tsx
{/* Report Format */}
<div style={{ marginTop: 16 }}>
  <label style={{ fontWeight: 600, fontSize: 13, display: "block", marginBottom: 6 }}>
    📋 Report Format
  </label>
  <div style={{ display: "flex", gap: 8 }}>
    {[
      { value: "narrative", label: "📝 Narrative", desc: "Free-form Markdown report" },
      { value: "matrix", label: "📊 Matrix", desc: "Structured comparison table" },
      { value: "hybrid", label: "📝📊 Hybrid", desc: "Both narrative + matrix" },
    ].map((opt) => (
      <button
        key={opt.value}
        onClick={() => setReportFormat(opt.value)}
        style={{
          padding: "8px 14px",
          borderRadius: 8,
          border: reportFormat === opt.value ? "2px solid #3b82f6" : "1px solid #e2e8f0",
          background: reportFormat === opt.value ? "#eff6ff" : "#fff",
          cursor: "pointer",
          fontSize: 12,
        }}
      >
        <div style={{ fontWeight: 600 }}>{opt.label}</div>
        <div style={{ fontSize: 10, color: "#64748b" }}>{opt.desc}</div>
      </button>
    ))}
  </div>
</div>
```

### 3. Create `MatrixReportView.tsx` component

**File**: `chatbot/src/components/chat/MatrixReportView.tsx`

```tsx
import React, { useState } from "react";
import { MatrixReport } from "../../types/chat";

const DIMENSION_LABELS: Record<string, { icon: string; label: string }> = {
  cost: { icon: "💰", label: "Cost" },
  performance: { icon: "⚡", label: "Performance" },
  complexity: { icon: "🔧", label: "Complexity" },
  maturity: { icon: "📊", label: "Maturity" },
  scalability: { icon: "📈", label: "Scalability" },
};

function ScoreBar({ score, max = 5 }: { score: number; max?: number }) {
  const pct = (score / max) * 100;
  const color = score >= 4 ? "#059669" : score >= 3 ? "#d97706" : "#dc2626";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 60, height: 6, borderRadius: 3, background: "#e2e8f0" }}>
        <div style={{ width: `${pct}%`, height: "100%", borderRadius: 3, background: color, transition: "width 0.3s" }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 600, color }}>{score}/{max}</span>
    </div>
  );
}

export function MatrixReportView({ matrix }: { matrix: MatrixReport }) {
  const [sortDim, setSortDim] = useState<string | null>(null);

  const alternatives = sortDim
    ? [...matrix.alternatives].sort((a, b) => (b.scores[sortDim as keyof typeof b.scores] || 0) - (a.scores[sortDim as keyof typeof a.scores] || 0))
    : matrix.alternatives;

  return (
    <div>
      <h2>{matrix.title}</h2>
      <p>{matrix.executive_summary}</p>

      {/* Comparison Table */}
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 16 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 8, borderBottom: "2px solid #e2e8f0" }}>Dimension</th>
            {alternatives.map((alt) => (
              <th key={alt.name} style={{ padding: 8, borderBottom: "2px solid #e2e8f0" }}>{alt.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(DIMENSION_LABELS).map(([dim, { icon, label }]) => (
            <tr key={dim} onClick={() => setSortDim(dim)} style={{ cursor: "pointer" }}>
              <td style={{ padding: 8, fontWeight: 600 }}>{icon} {label}</td>
              {alternatives.map((alt) => (
                <td key={alt.name} style={{ padding: 8, textAlign: "center" }}>
                  <ScoreBar score={alt.scores[dim as keyof typeof alt.scores] || 0} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Pros/Cons Cards */}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(alternatives.length, 3)}, 1fr)`, gap: 16, marginTop: 24 }}>
        {alternatives.map((alt) => (
          <div key={alt.name} style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 16 }}>
            <h3>{alt.name}</h3>
            <p style={{ fontSize: 13, color: "#64748b" }}>{alt.description}</p>
            <div style={{ marginTop: 12 }}>
              <h4 style={{ color: "#059669" }}>✅ Pros</h4>
              <ul>{alt.pros.map((p, i) => <li key={i} style={{ fontSize: 13 }}>{p}</li>)}</ul>
            </div>
            <div style={{ marginTop: 8 }}>
              <h4 style={{ color: "#dc2626" }}>❌ Cons</h4>
              <ul>{alt.cons.map((c, i) => <li key={i} style={{ fontSize: 13 }}>{c}</li>)}</ul>
            </div>
          </div>
        ))}
      </div>

      {matrix.recommendation && (
        <div style={{ marginTop: 24, padding: 16, background: "#f0fdf4", borderRadius: 12, border: "1px solid #a7f3d0" }}>
          <h3>🎯 Recommendation</h3>
          <p>{matrix.recommendation}</p>
        </div>
      )}
    </div>
  );
}
```

### 4. Integrate into ChatArea/report display

In the message rendering logic, check for `report_matrix` and render `MatrixReportView`:

```tsx
{message.report_matrix ? (
  <MatrixReportView matrix={message.report_matrix} />
) : (
  <MarkdownContent content={message.content} />
)}
```

For `"hybrid"` format, show both with a tab switcher.

---

## Testing Checklist

1. **`"narrative"` format (default)** — no change from current behavior
2. **`"matrix"` format** — verify JSON is parsed and rendered as Markdown table + Pros/Cons
3. **Matrix JSON fallback** — if LLM returns invalid JSON, report falls back to raw text
4. **`"hybrid"` format** — both narrative and matrix are generated
5. **Frontend table** — verify sortable comparison table renders
6. **Frontend Pros/Cons cards** — verify cards display correctly
7. **API response** — verify `report_format` and `report_matrix` appear in response

---

## Files Modified (Summary)

| File | Change |
|---|---|
| `pc_chatbots/app/api/schemas.py` | Add `report_format` to request + response |
| `pc_chatbots/app/core/models.py` | Add `report_format`, `report_matrix_json` to `Job` |
| `pc_chatbots/app/api/routes.py` | Store format, expose matrix in response |
| `pc_chatbots/app/orchestrator/agent_pipeline.py` | Add `build_matrix_report_prompt()`, `render_matrix_to_markdown()`, wire into lead phase |
| `chatbot/src/types/chat.ts` | Add `MatrixReport` type, `report_format`, `report_matrix` to `Message` |
| `chatbot/src/components/agent/AgentConfigScreen.tsx` | Add format picker |
| `chatbot/src/components/chat/MatrixReportView.tsx` | **New file** — matrix visualization |
| `chatbot/src/components/chat/ChatArea.tsx` | Integrate matrix view in message rendering |
