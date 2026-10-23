from __future__ import annotations

import asyncio
import inspect
import json
import re
import statistics
import time
from typing import Any

import structlog
from sqlmodel import select

from app.adapters.base import ProviderAdapter, Source as AdapterSource
from app.adapters.browser_base import ProviderNeedsUserAction
from app.browser.session import BrowserSessionManager
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.models import Claim, Job, JobEvent, ProviderRun, Report, Source, Subtask, utc_now
from app.orchestrator.pipeline import (
    AdapterNeedsUserAction,
    TERMINAL_STATUSES,
    create_adapter,
)
from app.adapters.capabilities.registry import CapabilitiesRegistry
from app.api.schemas import OrchestratorOutput
from app.orchestrator.step_emitter import StepEmitter, notify_job_event

logger = structlog.get_logger(__name__)

TONE_INSTRUCTIONS: dict[str, str] = {
    "academic": (
        "Write in formal academic style. Use precise terminology, maintain rigorous objectivity, "
        "structure the response with an abstract/overview, methodology & evidence, detailed analysis, and conclusions. "
        "Cite sources and attributing providers with brackets where applicable."
    ),
    "professional": (
        "Write in professional business style. Be concise, results-oriented, and structured. "
        "Use bullet points for key findings, include an executive overview, and highlight practical, actionable takeaways."
    ),
    "analytical": (
        "Write in analytical style. Compare and contrast perspectives from different providers, highlight data patterns, "
        "critique claims, examine trade-offs, and present an evidence-based synthesis."
    ),
    "explanatory": (
        "Write in clear pedagogical style suitable for teaching. Break down complex concepts into digestible parts, "
        "use intuitive analogies, and structure the explanation progressively from fundamentals to advanced applications."
    ),
    "journalistic": (
        "Write in journalistic investigative style. Lead with the core revelation or hook, present balanced multiple viewpoints, "
        "incorporate direct insights from the research, and maintain neutral, objective prose."
    ),
    "creative": (
        "Write in an engaging, narrative-driven style with vivid language. Make the material compelling and memorable "
        "while preserving factual integrity and depth."
    ),
    "executive": (
        "Write as an ultra-concise executive briefing. Start with a 3-sentence TL;DR, followed by key metrics, strategic implications, "
        "and concrete recommendations. Format with tables or quick bullet points suitable for a 2-minute skim."
    ),
    "conversational": (
        "Write in an approachable, conversational tone. Use direct and friendly address, clear natural language, "
        "practical examples, and make complex ideas easily accessible."
    ),
}


from .provider_specs import PROVIDER_CATALOG, resolve_provider_live_prompt_info

__all__ = [
    "AgentPipelineError",
    "AgentPipelineResult",
    "AgentStageStatus",
    "PROVIDER_CATALOG",
    "analyze_complexity",
    "build_complexity_analysis_prompt",
    "build_fact_check_prompt",
    "build_lead_prompt",
    "build_matrix_report_prompt",
    "build_orchestrator_prompt",
    "build_rebuttal_prompt",
    "build_red_team_prompt",
    "build_summarization_prompt",
    "build_synthesis_prompt",
    "parse_orchestrator_plan",
    "render_matrix_to_markdown",
    "resolve_provider_live_prompt_info",
    "run_adversarial_debate",
    "run_agent_pipeline",
    "run_fact_check_phase",
]


def build_summarization_prompt(
    previous_rounds_data: list[dict[str, Any]],
    current_topic: str,
) -> str:
    """Builds a prompt to condense previous rounds of research into an ultra-dense, token-efficient Context Briefing."""
    history_blocks: list[str] = []
    for idx, r in enumerate(previous_rounds_data, start=1):
        q = r.get("query", "").strip()
        rep = r.get("report_markdown", "").strip()
        findings = r.get("findings", [])
        block = f"### Vòng {idx} - Đề tài/Câu hỏi: {q}\n"
        if rep:
            short_rep = rep[:3000] + ("..." if len(rep) > 3000 else "")
            block += f"**Báo cáo tổng hợp trước đó:**\n{short_rep}\n"
        elif findings:
            block += "**Các phát hiện chuyên sâu từ các nhánh:**\n"
            for f in findings[:5]:
                branch_title = f.get("branch", "Nhánh")
                ans = f.get("answer_md", "").strip()[:500]
                block += f"- {branch_title}: {ans}\n"
        history_blocks.append(block)

    history_text = "\n\n---\n\n".join(history_blocks) if history_blocks else "Không có dữ liệu trước đó."

    return f"""You are an Expert Research Context Summarizer.
Your goal is to synthesize and condense the ongoing multi-round research history into a dense, token-efficient Research Context Briefing (under 400 words).
This Briefing will be provided to the Master Orchestrator and specialized AI sub-agents so they have full context without exceeding token limits or losing continuity.

## Ongoing Research History:
{history_text}

## Upcoming Follow-up Research Topic / Question:
"{current_topic}"

## Strict Instructions:
1. Extract the core findings, established facts, conclusions, and key technical decisions already made.
2. Highlight specific details directly relevant or needed to address the follow-up question.
3. Keep the summary dense, structured, and factual (under 400 words). Use clear bullet points.
4. Do NOT output markdown code fences, conversational greetings, or preambles. Output only the structured Context Briefing.

Produce the Context Briefing now:"""


def build_orchestrator_prompt(
    research_topic: str,
    allowed_providers: list[str] | None = None,
    provider_configs: dict[str, Any] | None = None,
    provider_capabilities: dict[str, Any] | None = None,
    context_summary: str | None = None,
    complexity_info: dict[str, Any] | None = None,
) -> str:
    valid_allowed = [p.lower() for p in (allowed_providers or []) if p.lower() in PROVIDER_CATALOG]
    if not valid_allowed:
        valid_allowed = list(PROVIDER_CATALOG.keys())

    pconfigs = provider_configs or {}
    pcaps = provider_capabilities or {}

    provider_lines: list[str] = []
    for idx, pid in enumerate(valid_allowed, start=1):
        info = resolve_provider_live_prompt_info(pid, pconfigs.get(pid), pcaps.get(pid))
        dom_badge = "[REAL DOM SYNCED]" if info.get("is_live_dom") else "[LATEST LIVE CONFIG]"
        provider_lines.append(
            f'{idx}. {info["name"]} (id: "{pid}") {dom_badge}\n'
            f'   - Active DOM Setting: {info["active_summary"]}\n'
            f'   - Expected "config" JSON Schema: {info["config_schema"]}\n'
            f'   - Specialized Sub-topic Role: {info["role"]}'
        )
    providers_text = "\n".join(provider_lines)
    allowed_ids_str = ", ".join(f'"{pid}"' for pid in valid_allowed)

    context_section = ""
    if context_summary and context_summary.strip():
        context_section = f"""
## Research Context & Established Facts from Previous Rounds:
{context_summary.strip()}

NOTE FOR ORCHESTRATION:
Use the established context above to avoid repeating already-researched angles.
Decompose the follow-up topic into next-level, deeper investigations or complementary sub-topics.
"""

    if complexity_info:
        rec_count = complexity_info.get("recommended_agent_count", 3)
        rec_groups = complexity_info.get("recommended_groups", ["researcher"])
        count_instruction = f"Decompose the topic into exactly {rec_count} distinct, non-overlapping specialized sub-topics."
        group_instruction = f"Prioritize assigning agents to these role groups: {', '.join(rec_groups)}."
        goal_count_str = f"exactly {rec_count}"
    else:
        count_instruction = "Decompose the topic into 2 to 5 distinct, non-overlapping specialized sub-topics."
        group_instruction = "Most sub-tasks should be 'researcher' or 'infra'. Only assign 'fact_checker' or 'red_team' if the topic specifically benefits from verification or critical analysis."
        goal_count_str = "2 to 5"

    return f"""You are a Master Research Orchestrator.
Your goal is to analyze the research topic provided by the user and intelligently decompose it into {goal_count_str} specialized sub-tasks.
Each sub-task must be assigned to the most appropriate AI provider from the ALLOWED providers list below.
{context_section}
## Available Allowed Providers and Configurations (Live DOM Synced):
{providers_text}

## STRICT REQUIREMENT: Allowed Delegation Providers
You are STRICTLY RESTRICTED to assigning sub-tasks ONLY to providers in this allowed list: [{allowed_ids_str}].
DO NOT assign any sub-task to any provider outside this list. Every single item in "agents_dispatch" MUST have "id" strictly matching one of [{allowed_ids_str}].

## Rules:
- {count_instruction}
- Assign each sub-topic to the provider best suited for that angle among the allowed providers, matching their active capabilities and strengths described above.
- Assign each sub-task a "role_group" from: "researcher" (core investigation), "infra" (data/benchmark/cost), "fact_checker" (verification), "red_team" (critique/counterargument).
- {group_instruction}
- In each "agents_dispatch" item, provide a valid "config" object that matches the provider's active DOM setting and expected schema.
- Each "question" must be a self-contained, detailed prompt for that provider to investigate.
- The output MUST be strictly valid JSON matching the schema below. Do not wrap in markdown or add explanations.

## Output JSON Schema:
{{
  "research_topic": "{research_topic}",
  "agents_dispatch": [
    {{
      "id": "<provider_id>",
      "name": "<provider_name>",
      "config": {{ ... }},
      "role_group": "<researcher|infra|fact_checker|red_team>",
      "sub_topic": "<Brief specialized sub-topic title>",
      "question": "<Detailed research prompt tailored for this provider's capabilities>"
    }}
  ]
}}

Research Topic to decompose:
{research_topic}"""


def build_lead_prompt(
    research_topic: str,
    findings: list[dict[str, Any]],
    tone: str,
    context_summary: str | None = None,
    fact_check_claims: list[dict[str, Any]] | None = None,
    debate_transcript: list[dict[str, Any]] | None = None,
    consensus_result: dict[str, Any] | None = None,
) -> str:
    tone_directive = TONE_INSTRUCTIONS.get(tone.lower(), TONE_INSTRUCTIONS["professional"])

    sections: list[str] = []
    for item in findings:
        prov = item.get("provider", "AI")
        branch = item.get("branch", "Nghiên cứu")
        ans = item.get("answer_md", "").strip()
        sections.append(f"### Nhánh nghiên cứu: {branch} (Cung cấp bởi: {prov})\n\n{ans}")

    findings_text = "\n\n---\n\n".join(sections) if sections else "Không có dữ liệu chi tiết từ các nhà cung cấp."

    context_section = ""
    if context_summary and context_summary.strip():
        context_section = f"""
## Background Context from Previous Research Rounds:
{context_summary.strip()}

Ensure your synthesis integrates continuity from previous findings while focusing on the new findings.
"""

    fact_check_section = ""
    if fact_check_claims:
        verified = [c for c in fact_check_claims if c.get("verdict") == "supported"]
        disputed = [c for c in fact_check_claims if c.get("verdict") in ("unsupported", "conflict", "single_source", "disputed")]
        disputed_items = "\n".join(
            f'- ⚠️ "{c.get("claim") or c.get("text", "")}" — Verdict: {c.get("verdict", "")} — {c.get("reasoning", "")}'
            for c in disputed[:10]
        )
        fact_check_section = f"""
## Fact-Check Results:
- {len(verified)} claims verified as supported
- {len(disputed)} claims flagged as unsupported or conflicting

### Disputed/Flagged Claims (MUST address in report):
{disputed_items if disputed_items else "- No critical disputes identified."}

IMPORTANT: Clearly mark any disputed claims in the report. Do not present unsupported claims as established facts.
"""

    debate_section = ""
    if debate_transcript:
        critiques = [t for t in debate_transcript if t.get("side") == "red_team" and t.get("content")]
        defenses = [t for t in debate_transcript if t.get("side") == "defender" and t.get("content")]
        critiques_text = "\n".join(
            f"- **Round {c.get('round', '?')} ({c.get('provider', 'Red Team')})**: {c.get('content', '')[:1000]}"
            for c in critiques[:3]
        )
        defenses_text = "\n".join(
            f"- **Round {d.get('round', '?')} ({d.get('provider', 'Defender')})**: {d.get('content', '')[:1000]}"
            for d in defenses[:3]
        )
        debate_section = f"""
## Adversarial Debate Results:
{len(critiques)} critique(s) and {len(defenses)} defense(s) were exchanged.

### Key Red Team Critiques:
{critiques_text if critiques_text else "- No critiques recorded."}

### Defender Responses:
{defenses_text if defenses_text else "- No defenses recorded."}

IMPORTANT: Your synthesis MUST address the critiques raised. Acknowledge valid weaknesses. Do NOT ignore Red Team concerns.
"""

    consensus_section = ""
    if consensus_result and consensus_result.get("final_scores"):
        scores_lines = []
        for sc in consensus_result["final_scores"]:
            thesis = next((t for t in consensus_result.get("theses", []) if t.get("id") == sc.get("id")), {})
            th_text = thesis.get("thesis", "")
            scores_lines.append(f'- {sc.get("id", "T")}: "{th_text}" — Score: {sc.get("mean", "?")}/5 (StdDev: {sc.get("stdev", "?")})')
        consensus_section = f"""
## Delphi Consensus Results:
Convergence Achieved: {"✅ Yes (High Agreement)" if consensus_result.get("converged") else "⚠️ No (Divergent Perspectives)"}

### Thesis Confidence Scores:
{chr(10).join(scores_lines)}

IMPORTANT: Incorporate these consensus scores into your analysis. High-scoring theses (score >= 4.0) should be prioritized as robust core findings. Lower-scoring or high-variance theses should be presented with nuance and appropriate caveats.
"""

    return f"""You are the Lead Research Synthesizer.
You have been provided with comprehensive findings gathered by specialized AI agents investigating different aspects of the topic:
"{research_topic}"
{context_section}
{fact_check_section}
{debate_section}
{consensus_section}
## Findings from Autonomous AI Providers:
{findings_text}

## Your Task:
Synthesize all the above findings into a single, cohesive, high-quality Markdown research report.
- Synthesize facts, cross-compare differing points, and eliminate redundancy.
- Attribute key findings to the respective agents/sources where helpful.
- Organize clearly with headers, bullet points, and analytical conclusions.

## Tone & Style Directive:
{tone_directive}

Produce the final comprehensive Markdown report now:"""


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
        disputed = [c for c in fact_check_claims if c.get("verdict") in ("unsupported", "conflict", "single_source", "disputed")]
        if disputed:
            fc_section = "\n## Disputed Claims:\n" + "\n".join(
                f"- ⚠️ \"{c.get('claim') or c.get('text', '')}\" [{c.get('verdict', '')}]" for c in disputed[:10]
            ) + "\n"

    debate_section = ""
    if debate_transcript:
        critiques = [t for t in debate_transcript if t.get("side") == "red_team" and t.get("content")]
        defenses = [t for t in debate_transcript if t.get("side") == "defender" and t.get("content")]
        critiques_text = "\n".join(
            f"- **Round {c.get('round', '?')} ({c.get('provider', 'Red Team')})**: {c.get('content', '')[:600]}"
            for c in critiques[:3]
        )
        defenses_text = "\n".join(
            f"- **Round {d.get('round', '?')} ({d.get('provider', 'Defender')})**: {d.get('content', '')[:600]}"
            for d in defenses[:3]
        )
        debate_section = f"""
## Adversarial Debate Results:
{critiques_text if critiques_text else "- No critiques recorded."}

### Defense Points:
{defenses_text if defenses_text else "- No defenses recorded."}
"""

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
{debate_section}
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
                "⭐" * int(a.get("scores", {}).get(dim, 0) or 0) + f" ({a.get('scores', {}).get(dim, '?')}/5)"
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


def _clean_json_str(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    array_match = re.search(r"(\[.*\])", text, re.DOTALL)
    obj_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if array_match and obj_match:
        if array_match.start() <= obj_match.start() and array_match.end() >= obj_match.end():
            return array_match.group(1).strip()
        elif obj_match.start() <= array_match.start() and obj_match.end() >= array_match.end():
            return obj_match.group(1).strip()
        elif array_match.start() < obj_match.start():
            return array_match.group(1).strip()
        else:
            return obj_match.group(1).strip()
    if array_match:
        return array_match.group(1).strip()
    if obj_match:
        return obj_match.group(1).strip()
    return text


def build_complexity_analysis_prompt(
    research_topic: str,
    available_providers: list[str],
    min_agents: int = 2,
    max_agents: int = 5,
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
- "low" complexity -> {min_agents} agents, just "researcher"
- "medium" complexity -> {min(min_agents + 1, max_agents)}-{max(min_agents, max_agents - 1)} agents, "researcher" + "infra"
- "high" complexity -> {max_agents} agents, all groups
- Output ONLY the JSON. No markdown fences."""


async def analyze_complexity(
    job_id: str,
    research_topic: str,
    orchestrator_prov: str,
    orch_config: dict[str, Any],
    available_providers: list[str],
    min_agents: int = 2,
    max_agents: int = 5,
    cancel_event: asyncio.Event | None = None,
) -> dict[str, Any]:
    """Quick complexity assessment before orchestration."""
    min_agents = max(1, min(min_agents, 10))
    max_agents = max(min_agents, min(max_agents, 10))
    default_rec = min(max(3, min_agents), max_agents)
    default_result: dict[str, Any] = {
        "complexity_level": "medium",
        "recommended_agent_count": default_rec,
        "recommended_groups": ["researcher", "infra"],
        "reasoning": "Default assessment (complexity analysis skipped or failed).",
    }

    if cancel_event and cancel_event.is_set():
        return default_result

    try:
        adapter = create_adapter(orchestrator_prov)
        prompt = build_complexity_analysis_prompt(
            research_topic, available_providers, min_agents, max_agents
        )

        timeout_s = 60
        ask_kwargs: dict[str, Any] = {}
        try:
            sig = inspect.signature(adapter.ask)
            if "timeout_s" in sig.parameters:
                ask_kwargs["timeout_s"] = timeout_s
            if "mode" in sig.parameters and orch_config:
                ask_kwargs["mode"] = json.dumps(orch_config)
        except (TypeError, ValueError):
            ask_kwargs["timeout_s"] = timeout_s
            if orch_config:
                ask_kwargs["mode"] = json.dumps(orch_config)

        result = await adapter.ask(prompt, **ask_kwargs)
        cleaned = _clean_json_str(result.answer_markdown)
        parsed = json.loads(cleaned)

        if not isinstance(parsed, dict):
            return default_result

        rec_count = parsed.get("recommended_agent_count", default_rec)
        try:
            rec_count = int(rec_count)
        except (ValueError, TypeError):
            rec_count = default_rec
        rec_count = min(max(min_agents, rec_count), max_agents)
        parsed["recommended_agent_count"] = rec_count

        raw_level = str(parsed.get("complexity_level", "medium")).lower()
        if raw_level not in ("low", "medium", "high"):
            raw_level = "medium"
        parsed["complexity_level"] = raw_level

        rec_groups = parsed.get("recommended_groups", ["researcher"])
        if isinstance(rec_groups, list):
            valid_groups = {"researcher", "infra", "fact_checker", "red_team"}
            parsed["recommended_groups"] = [g for g in rec_groups if g in valid_groups] or ["researcher"]
        else:
            parsed["recommended_groups"] = ["researcher"]

        return parsed

    except Exception as exc:
        logger.warning("complexity_analysis_failed", job_id=job_id, error=str(exc))
        return default_result
    finally:
        try:
            await BrowserSessionManager.close_session(orchestrator_prov)
        except Exception:
            pass


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
    fc_conv_url = initial_conv_urls.get("fact_checker") or initial_conv_urls.get(fact_check_provider)

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
        answer = run_item.get("answer_md", "") or run_item.get("answer_markdown", "")
        if not answer or len(answer.strip()) < 50:
            continue

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
        if fc_conv_url and ("conversation_url" in inspect.signature(fc_adapter.ask).parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in inspect.signature(fc_adapter.ask).parameters.values())):
            fc_kwargs["conversation_url"] = fc_conv_url

        try:
            fc_result = await fc_adapter.ask(fc_prompt, **fc_kwargs)
            new_fc_url = str(fc_result.conversation_url) if getattr(fc_result, "conversation_url", None) else None
            fc_conv_url = new_fc_url or fc_conv_url
            cleaned = _clean_json_str(fc_result.answer_markdown)
            parsed_claims = json.loads(cleaned)
            if isinstance(parsed_claims, dict) and "claims" in parsed_claims:
                parsed_claims = parsed_claims["claims"]
            if isinstance(parsed_claims, list):
                for claim in parsed_claims:
                    if isinstance(claim, dict):
                        claim["branch"] = branch
                        claim["provider"] = run_item.get("provider", "")
                        all_claims.append(claim)
        except Exception as fc_exc:
            logger.warning("fact_check_failed_for_branch", branch=branch, error=str(fc_exc))
        finally:
            await BrowserSessionManager.close_session(fact_check_provider)

    fc_duration = round(time.monotonic() - fc_start, 1)
    async with SessionLocal() as session:
        db_j = await session.get(Job, job_id)
        if db_j is not None:
            normalized_claims = []
            for ci, c in enumerate(all_claims):
                c_id = f"{job_id}:FC{ci + 1}"
                c_text = c.get("claim") or c.get("text", "")
                c_verdict = c.get("verdict", "unsupported")
                if c_verdict not in ("supported", "single_source", "unsupported", "conflict", "disputed", "verified"):
                    c_verdict = "unsupported"
                item_dict = {
                    "id": c_id,
                    "claim": c_text,
                    "text": c_text,
                    "branch": c.get("branch", ""),
                    "provider": c.get("provider", ""),
                    "verdict": c_verdict,
                    "confidence": float(c.get("confidence", 1.0)) if c.get("confidence") is not None else 1.0,
                    "reasoning": c.get("reasoning", ""),
                    "source_ids": c.get("source_ids", []),
                }
                normalized_claims.append(item_dict)
                session.add(Claim(
                    id=c_id,
                    job_id=job_id,
                    text=c_text,
                    branch=c.get("branch", ""),
                    source_ids_json=json.dumps(c.get("source_ids", [])),
                    verdict=c_verdict,
                ))

            db_j.fact_check_results_json = json.dumps(normalized_claims, ensure_ascii=False)
            db_j.claims_json = json.dumps(normalized_claims, ensure_ascii=False)
            db_j.updated_at = utc_now()

            session.add(JobEvent(
                job_id=job_id,
                status="fact_checking",
                event_type="fact_check_complete",
                provider=fact_check_provider,
                step="fact_check_complete",
                message=f"Đã kiểm chứng {len(normalized_claims)} luận điểm từ {len(runs)} nhánh nghiên cứu ({fc_duration}s).",
                data_json=json.dumps({
                    "claims_count": len(normalized_claims),
                    "claims": normalized_claims,
                    "elapsed_s": fc_duration,
                    "role": "fact_checker",
                    "provider_role_key": "fact_checker",
                    "conversation_url": fc_conv_url,
                }, ensure_ascii=False),
            ))
            await session.commit()
            all_claims = normalized_claims
        notify_job_event(job_id)

    return all_claims


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
    valid_runs = [r for r in runs if r.get("status") == "ok"] or runs
    findings_summary = "\n\n---\n\n".join(
        f"### {r.get('branch', 'Branch')} (by {r.get('provider', 'AI')})\n{r.get('answer_md', '')[:2000]}"
        for r in valid_runs
    )

    # Build fact-check summary if available
    fc_summary = None
    if fact_check_claims:
        disputed = [c for c in fact_check_claims if c.get("verdict") in ("unsupported", "conflict", "single_source", "disputed")]
        if disputed:
            fc_summary = "\n".join(
                f"- ⚠️ {c.get('claim') or c.get('text', '')} [{c.get('verdict', '')}]" for c in disputed[:10]
            )

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
            rt_prompt = f"""You are the Red Team (Round {round_num}). The defender responded to your previous critique.
Review their defense and identify any remaining weaknesses or new concerns.

## Previous Critique:
{last_critique[:3000]}

## Defender's Response:
{last_defense[:3000]}

Continue your adversarial analysis. Focus on points NOT adequately addressed:"""

        rt_kwargs: dict[str, Any] = {
            "timeout_s": 300,
        }
        if debate_config:
            rt_kwargs["mode"] = json.dumps(debate_config)
        try:
            sig = inspect.signature(rt_adapter.ask)
            if "on_step" in sig.parameters:
                rt_kwargs["on_step"] = StepEmitter(
                    job_id=job_id,
                    provider=debate_provider,
                    status="debating",
                    role="red_team",
                    cancel_event=cancel_event,
                    start_time=debate_start,
                    extra_payload={
                        "round": round_num,
                        "side": "red_team",
                        "provider_role_key": f"red_team_round_{round_num}",
                    },
                )
        except (TypeError, ValueError):
            pass

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
            transcript.append({
                "round": round_num,
                "side": "red_team",
                "provider": debate_provider,
                "error": str(rt_exc),
            })
            break
        finally:
            try:
                await BrowserSessionManager.close_session(debate_provider)
            except Exception:
                pass

        if cancel_event.is_set():
            break

        # --- DEFENDER REBUTTAL ---
        def_adapter = create_adapter(defender_prov)
        def_prompt = build_rebuttal_prompt(research_topic, findings_summary, last_critique, round_num)

        def_kwargs: dict[str, Any] = {
            "timeout_s": 300,
        }
        if debate_config:
            def_kwargs["mode"] = json.dumps(debate_config)
        try:
            sig = inspect.signature(def_adapter.ask)
            if "on_step" in sig.parameters:
                def_kwargs["on_step"] = StepEmitter(
                    job_id=job_id,
                    provider=defender_prov,
                    status="debating",
                    role="defender",
                    cancel_event=cancel_event,
                    start_time=debate_start,
                    extra_payload={
                        "round": round_num,
                        "side": "defender",
                        "provider_role_key": f"defender_round_{round_num}",
                    },
                )
        except (TypeError, ValueError):
            pass

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
            transcript.append({
                "round": round_num,
                "side": "defender",
                "provider": defender_prov,
                "error": str(def_exc),
            })
            break
        finally:
            try:
                await BrowserSessionManager.close_session(defender_prov)
            except Exception:
                pass

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
                    "rounds_completed": max((t.get("round", 0) for t in transcript if isinstance(t, dict)), default=0),
                    "total_exchanges": len(transcript),
                    "elapsed_s": debate_duration,
                    "role": "red_team",
                    "provider_role_key": "red_team",
                }, ensure_ascii=False),
            ))
            await session.commit()
        notify_job_event(job_id)

    return transcript


def build_thesis_extraction_prompt(
    research_topic: str,
    findings_summary: str,
    debate_summary: str | None = None,
) -> str:
    """Extract key theses from research findings for consensus scoring."""
    debate_section = ""
    if debate_summary:
        debate_section = f"""
## Debate Outcomes & Critiques:
{debate_summary[:3000]}
"""

    return f"""You are a Research Analyst. Extract the TOP 5-8 most important theses (key conclusions, disputed assertions, or actionable recommendations) from the following research findings.

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
- Each thesis must be a specific, testable, scorable statement (not vague).
- Include both well-supported AND contested theses so agents can reach consensus.
- Output ONLY the JSON array. Do not wrap in markdown fences or include explanations."""


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
## Aggregate Scores from Previous Round (Delphi Feedback):
{json.dumps(previous_aggregate, indent=2, ensure_ascii=False)[:2000]}

Consider the group consensus tendency but exercise your own rigorous, independent domain judgment. If you disagree with the majority, maintain your score with clear reasoning.
"""

    return f"""You are an Independent Research Evaluator (Delphi Scoring Round {round_number}).
Score each thesis below on a scale of 1 to 5 for CONFIDENCE (how likely this thesis is correct, well-grounded, and actionable).

Scale:
1 = Very low confidence (likely wrong, invalid, or impractical)
2 = Low confidence (significant doubts or lacking evidence)
3 = Moderate confidence (plausible but uncertain or contested)
4 = High confidence (well-supported, likely correct)
5 = Very high confidence (strongly supported, highly actionable, authoritative)

## Theses to Score:
{theses_text}
{prev_section}
## Output Format (strict JSON array):
[
  {{"id": "T1", "score": <1-5>, "reasoning": "<brief justification>"}},
  ...
]

Rules:
- Score EVERY thesis listed. Do not skip any.
- Be honest and calibrated — do not default everything to 3 or 5.
- Output ONLY the JSON array. Do not wrap in markdown fences or add commentary."""


async def run_delphi_consensus(
    job_id: str,
    research_topic: str,
    runs: list[dict[str, Any]],
    debate_transcript: list[dict[str, Any]],
    consensus_providers: list[str],
    threshold: float,
    max_rounds: int,
    cancel_event: asyncio.Event,
    initial_conv_urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Phase 4: Delphi Consensus — iterative scoring until convergence."""
    consensus_start = time.monotonic()

    clean_providers: list[str] = []
    for p in consensus_providers:
        if p and p not in clean_providers:
            clean_providers.append(p)
    if not clean_providers:
        clean_providers = ["9router"]

    await _set_agent_status(
        job_id,
        "consensus",
        message=f"Bắt đầu quy trình Delphi Consensus với {len(clean_providers)} nhà đánh giá...",
        data={
            "consensus_providers": clean_providers,
            "threshold": threshold,
            "max_rounds": max_rounds,
            "role": "consensus",
            "provider_role_key": "consensus",
            "elapsed_s": 0.0,
        },
    )

    if cancel_event.is_set():
        return {"theses": [], "rounds": [], "converged": False, "final_scores": []}

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

    theses: list[dict[str, Any]] = []
    extraction_prov = clean_providers[0]
    thesis_adapter = create_adapter(extraction_prov)
    thesis_prompt = build_thesis_extraction_prompt(research_topic, findings_summary, debate_summary)

    th_kwargs: dict[str, Any] = {"timeout_s": 180, "mode": "default"}
    try:
        sig = inspect.signature(thesis_adapter.ask)
        if "on_step" in sig.parameters:
            th_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=extraction_prov,
                status="consensus",
                role="consensus",
                cancel_event=cancel_event,
                start_time=consensus_start,
                extra_payload={
                    "stage": "thesis_extraction",
                    "provider_role_key": "consensus_thesis_extraction",
                },
            )
    except (TypeError, ValueError):
        pass

    try:
        thesis_result = await thesis_adapter.ask(thesis_prompt, **th_kwargs)
        cleaned = _clean_json_str(thesis_result.answer_markdown)
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and len(parsed) > 0:
            theses = parsed
        elif isinstance(parsed, dict) and "theses" in parsed and isinstance(parsed["theses"], list):
            theses = parsed["theses"]
    except Exception as te:
        logger.warning("thesis_extraction_failed", error=str(te))
    finally:
        try:
            await BrowserSessionManager.close_session(extraction_prov)
        except Exception:
            pass

    if not theses:
        theses = [
            {"id": "T1", "thesis": f"Kết luận trọng tâm về {research_topic}", "category": "strategic", "supporting_evidence": "Tổng hợp từ dữ liệu nghiên cứu ban đầu"}
        ]

    # Step 2: Iterative scoring rounds
    all_rounds: list[dict[str, Any]] = []
    previous_aggregate: list[dict[str, Any]] | None = None
    converged = False

    for round_num in range(1, max_rounds + 1):
        if cancel_event.is_set():
            break

        round_scores: dict[str, list[int]] = {t.get("id", f"T{i}"): [] for i, t in enumerate(theses, 1)}

        # Each provider scores
        for prov_id in clean_providers:
            if cancel_event.is_set():
                break

            scorer_adapter = create_adapter(prov_id)
            score_prompt = build_consensus_scoring_prompt(theses, round_num, previous_aggregate)
            sc_kwargs: dict[str, Any] = {"timeout_s": 180, "mode": "default"}
            try:
                sig = inspect.signature(scorer_adapter.ask)
                if "on_step" in sig.parameters:
                    sc_kwargs["on_step"] = StepEmitter(
                        job_id=job_id,
                        provider=prov_id,
                        status="consensus",
                        role="consensus",
                        cancel_event=cancel_event,
                        start_time=consensus_start,
                        extra_payload={
                            "stage": "scoring",
                            "round": round_num,
                            "provider_role_key": f"consensus_round_{round_num}_{prov_id}",
                        },
                    )
            except (TypeError, ValueError):
                pass

            try:
                score_result = await scorer_adapter.ask(score_prompt, **sc_kwargs)
                cleaned_scores = _clean_json_str(score_result.answer_markdown)
                parsed_scores = json.loads(cleaned_scores)
                if isinstance(parsed_scores, dict) and "scores" in parsed_scores:
                    parsed_scores = parsed_scores["scores"]
                if isinstance(parsed_scores, list):
                    for sc in parsed_scores:
                        tid = sc.get("id", "")
                        score = sc.get("score", 3)
                        if tid in round_scores and isinstance(score, (int, float)):
                            round_scores[tid].append(int(min(5, max(1, score))))
            except Exception as sc_exc:
                logger.warning("consensus_scoring_failed", provider=prov_id, round=round_num, error=str(sc_exc))
            finally:
                try:
                    await BrowserSessionManager.close_session(prov_id)
                except Exception:
                    pass

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
        elapsed_now = round(time.monotonic() - consensus_start, 1)
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
                    "elapsed_s": elapsed_now,
                }, ensure_ascii=False),
            ))
            await session.commit()
        notify_job_event(job_id)

        # Check convergence
        if std_devs and avg_stdev <= threshold:
            converged = True
            break

    # Build final result
    if not converged and all_rounds:
        last_devs = [a.get("stdev", 0.0) for a in all_rounds[-1].get("aggregate", []) if a.get("n", 0) > 0]
        if last_devs and statistics.mean(last_devs) <= threshold:
            converged = True

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
                    "theses_count": len(theses),
                }, ensure_ascii=False),
            ))
            await session.commit()
        notify_job_event(job_id)

    return consensus_result


async def _set_agent_status(
    job_id: str,
    status: str,
    *,
    message: str | None = None,
    event_type: str = "progress",
    data: dict[str, Any] | None = None,
    subtasks_total: int | None = None,
    subtasks_done: int | None = None,
) -> None:
    phase_messages = {
        "queued": "Nhiệm vụ nghiên cứu đa tác nhân đã vào hàng đợi.",
        "summarizing": "Summarization Provider đang cô đọng ngữ cảnh từ các vòng trước...",
        "orchestrating": "Orchestrator đang phân rã nhiệm vụ và lập kế hoạch...",
        "researching": "Các chatbot chuyên biệt đang đồng loạt nghiên cứu...",
        "fact_checking": "Fact-Checker Provider đang kiểm chứng tính xác thực của các luận điểm...",
        "debating": "Red Team và Defender đang tranh luận phản biện các kết quả...",
        "consensus": "Delphi Consensus đang đánh giá độ hội tụ và thẩm định luận điểm...",
        "leading": "Lead Provider đang tổng hợp và tinh chỉnh báo cáo hoàn chỉnh...",
        "completed": "Nghiên cứu đa tác nhân hoàn tất thành công.",
        "partial": "Nghiên cứu hoàn tất một phần.",
        "failed": "Quá trình nghiên cứu đa tác nhân thất bại.",
        "cancelled": "Nhiệm vụ nghiên cứu đã bị hủy.",
        "needs_user_action": "Cần can thiệp người dùng (đăng nhập hoặc giải CAPTCHA).",
    }
    msg = message or phase_messages.get(status, f"Trạng thái: {status}")
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None and job.status not in TERMINAL_STATUSES:
            job.status = status
            if subtasks_total is not None:
                job.subtasks_total = subtasks_total
            if subtasks_done is not None:
                job.subtasks_done = subtasks_done
            job.updated_at = utc_now()
            session.add(JobEvent(
                job_id=job_id,
                status=status,
                event_type=event_type,
                message=msg,
                subtasks_total=job.subtasks_total,
                subtasks_done=job.subtasks_done,
                data_json=json.dumps(data, ensure_ascii=False) if data is not None else None,
            ))
            await session.commit()
        notify_job_event(job_id)


async def run_agent_pipeline(job_id: str, cancel_event: asyncio.Event) -> None:
    """Executes the 3-stage Deep Research Orchestrator pipeline:
    1. Orchestrate: Decompose topic into subtasks with a chosen Orchestrator provider.
    2. Research: Dispatch each subtask to assigned providers in parallel.
    3. Lead Synthesize: Synthesize all responses using chosen Lead provider with selected tone.
    """
    logger.info("run_agent_pipeline_started", job_id=job_id)
    try:
        initial_conv_urls: dict[str, str] = {}
        parent_job_id: str | None = None
        context_summary: str | None = None
        summarization_prov: str = "9router"
        summarization_config: dict[str, Any] = {"model_id": "Daily"}

        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is None or job.status == "cancelled":
                return
            research_topic = job.query
            orchestrator_prov = job.orchestrator_provider or "gemini"
            lead_prov = job.lead_provider or "chatgpt"
            tone = job.tone or "professional"
            summarization_prov = getattr(job, "summarization_provider", None) or "9router"
            parent_job_id = getattr(job, "parent_job_id", None)
            context_summary = getattr(job, "context_summary", None)
            try:
                orch_config = json.loads(job.orchestrator_config_json) if job.orchestrator_config_json else {}
            except Exception:
                orch_config = {}
            try:
                lead_config = json.loads(job.lead_config_json) if job.lead_config_json else {}
            except Exception:
                lead_config = {}
            try:
                summarization_config = json.loads(job.summarization_config_json) if getattr(job, "summarization_config_json", None) else {"model_id": "Daily"}
            except Exception:
                summarization_config = {"model_id": "Daily"}

            delegated_providers: list[str] = []
            provider_configs: dict[str, Any] = {}
            provider_capabilities: dict[str, Any] = {}
            try:
                cfg_obj = json.loads(job.config_json) if job.config_json else {}
                raw_delegated = cfg_obj.get("delegated_providers") or []
                delegated_providers = [str(p).lower() for p in raw_delegated if str(p).lower() in PROVIDER_CATALOG]
                provider_configs = cfg_obj.get("provider_configs") or {}
                provider_capabilities = cfg_obj.get("provider_capabilities") or {}
                if not initial_conv_urls and cfg_obj.get("conversation_urls"):
                    initial_conv_urls = dict(cfg_obj["conversation_urls"])
            except Exception:
                delegated_providers = []

            if getattr(job, "provider_conversations_json", None):
                try:
                    loaded_convs = json.loads(job.provider_conversations_json)
                    if isinstance(loaded_convs, dict):
                        initial_conv_urls.update(loaded_convs)
                except Exception:
                    pass

            if not initial_conv_urls and parent_job_id:
                p_job = await session.get(Job, parent_job_id)
                if p_job and getattr(p_job, "provider_conversations_json", None):
                    try:
                        p_convs = json.loads(p_job.provider_conversations_json)
                        if isinstance(p_convs, dict):
                            initial_conv_urls.update(p_convs)
                    except Exception:
                        pass

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # ---------------------------------------------------------
        # PHASE 0: SUMMARIZATION (Sequential context briefing for Round 2+)
        # ---------------------------------------------------------
        if not context_summary and parent_job_id:
            previous_rounds: list[dict[str, Any]] = []
            curr_pid: str | None = parent_job_id
            async with SessionLocal() as s_hist:
                chain_jobs: list[Job] = []
                while curr_pid:
                    pj = await s_hist.get(Job, curr_pid)
                    if not pj:
                        break
                    chain_jobs.append(pj)
                    curr_pid = getattr(pj, "parent_job_id", None)
                chain_jobs.reverse()
                for pj in chain_jobs:
                    p_findings: list[dict[str, Any]] = []
                    if pj.provider_runs_json:
                        try:
                            parsed_runs = json.loads(pj.provider_runs_json)
                            if isinstance(parsed_runs, list):
                                p_findings = parsed_runs
                        except Exception:
                            pass
                    previous_rounds.append({
                        "query": pj.query,
                        "report_markdown": pj.report_markdown or "",
                        "findings": p_findings,
                    })

            if previous_rounds:
                sum_start = time.monotonic()
                await _set_agent_status(
                    job_id,
                    "summarizing",
                    message=f"Summarization Provider ({summarization_prov}) đang cô đọng ngữ cảnh từ vòng trước...",
                    data={
                        "summarizer": summarization_prov,
                        "config": summarization_config,
                        "role": "summarizer",
                        "provider_role_key": "summarizer",
                        "elapsed_s": 0.0,
                    },
                )
                sum_adapter = create_adapter(summarization_prov)
                sum_prompt = build_summarization_prompt(previous_rounds, research_topic)
                sum_kwargs: dict[str, Any] = {
                    "timeout_s": 120,
                    "mode": json.dumps(summarization_config) if summarization_config else "default",
                }
                if "on_step" in inspect.signature(sum_adapter.ask).parameters:
                    sum_kwargs["on_step"] = StepEmitter(
                        job_id=job_id,
                        provider=summarization_prov,
                        status="summarizing",
                        role="summarizer",
                        cancel_event=cancel_event,
                        start_time=sum_start,
                    )
                try:
                    sum_res = await sum_adapter.ask(sum_prompt, **sum_kwargs)
                    context_summary = sum_res.answer_markdown
                except Exception as sum_exc:
                    logger.warning("summarization_provider_failed", provider=summarization_prov, error=str(sum_exc))
                    context_summary = previous_rounds[-1].get("report_markdown", "")[:1500]
                finally:
                    await BrowserSessionManager.close_session(summarization_prov)

                sum_duration = round(time.monotonic() - sum_start, 1)
                async with SessionLocal() as s_up:
                    db_j = await s_up.get(Job, job_id)
                    if db_j:
                        db_j.context_summary = context_summary
                        db_j.updated_at = utc_now()
                        s_up.add(JobEvent(
                            job_id=job_id,
                            status="summarizing",
                            event_type="context_summarized",
                            provider=summarization_prov,
                            step="context_summarized",
                            message=f"Đã cô đọng ngữ cảnh nghiên cứu thành công ({sum_duration}s).",
                            data_json=json.dumps({
                                "summary_preview": context_summary[:200] if context_summary else "",
                                "role": "summarizer",
                                "provider_role_key": "summarizer",
                                "elapsed_s": sum_duration,
                            }, ensure_ascii=False),
                        ))
                        await s_up.commit()
                notify_job_event(job_id)

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # ---------------------------------------------------------
        # PRE-PHASE: COMPLEXITY ANALYSIS (Optional auto-scaling)
        # ---------------------------------------------------------
        auto_scale = True
        min_ag = 2
        max_ag = 5
        complexity_info: dict[str, Any] | None = None

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None and db_j.config_json:
                try:
                    cfg_obj = json.loads(db_j.config_json)
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

        # ---------------------------------------------------------
        # PHASE 1: ORCHESTRATING (Task decomposition)
        # ---------------------------------------------------------
        orch_start = time.monotonic()
        await _set_agent_status(
            job_id,
            "orchestrating",
            message=f"Orchestrator ({orchestrator_prov}) đang phân tích chủ đề và lập kế hoạch phân rã...",
            data={"orchestrator": orchestrator_prov, "config": orch_config, "role": "orchestrator", "complexity": complexity_info, "elapsed_s": 0.0},
        )

        orch_adapter = create_adapter(orchestrator_prov)
        orch_prompt = build_orchestrator_prompt(
            research_topic,
            allowed_providers=delegated_providers,
            provider_configs=provider_configs,
            provider_capabilities=provider_capabilities,
            context_summary=context_summary,
            complexity_info=complexity_info,
        )

        orch_conv_url = initial_conv_urls.get("orchestrator") or initial_conv_urls.get(orchestrator_prov)
        ask_kwargs: dict[str, Any] = {
            "timeout_s": 300,
            "mode": json.dumps(orch_config) if orch_config else "default",
        }
        if "on_step" in inspect.signature(orch_adapter.ask).parameters:
            ask_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=orchestrator_prov,
                status="orchestrating",
                role="orchestrator",
                cancel_event=cancel_event,
                start_time=orch_start,
            )
        if orch_conv_url and ("conversation_url" in inspect.signature(orch_adapter.ask).parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in inspect.signature(orch_adapter.ask).parameters.values())):
            ask_kwargs["conversation_url"] = orch_conv_url

        try:
            orch_res = await orch_adapter.ask(orch_prompt, **ask_kwargs)
        except Exception as exc:
            logger.error("orchestrator_provider_failed", provider=orchestrator_prov, error=str(exc))
            await _set_agent_status(job_id, "failed", message=f"Orchestrator ({orchestrator_prov}) gặp lỗi: {exc}")
            return
        finally:
            await BrowserSessionManager.close_session(orchestrator_prov)

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        cleaned_json = _clean_json_str(orch_res.answer_markdown)
        dispatch_items: list[dict[str, Any]] = []
        try:
            parsed = json.loads(cleaned_json)
            validated = OrchestratorOutput.model_validate(parsed)
            dispatch_items = [item.model_dump() for item in validated.agents_dispatch]
        except Exception as json_err:
            logger.warning("orchestrator_json_parse_failed", error=str(json_err), raw=orch_res.answer_markdown[:300])
            # Fallback default plan using allowed delegated providers with live DOM configs
            p1 = delegated_providers[0] if delegated_providers else "deepseek"
            p2 = delegated_providers[1 % len(delegated_providers)] if delegated_providers else "perplexity"
            p1_info = resolve_provider_live_prompt_info(p1, provider_configs.get(p1), provider_capabilities.get(p1))
            p2_info = resolve_provider_live_prompt_info(p2, provider_configs.get(p2), provider_capabilities.get(p2))
            dispatch_items = [
                {
                    "id": p1,
                    "name": p1_info["name"],
                    "config": p1_info["default_config"],
                    "role_group": "researcher",
                    "sub_topic": "Nền tảng lý thuyết & Giải thuật",
                    "question": f"Phân tích chuyên sâu về kiến trúc và thuật toán liên quan đến: {research_topic}",
                },
                {
                    "id": p2,
                    "name": p2_info["name"],
                    "config": p2_info["default_config"],
                    "role_group": "infra",
                    "sub_topic": "Dữ liệu ứng dụng thực tế & Nguồn dẫn chứng",
                    "question": f"Tìm kiếm các số liệu, tài liệu học thuật và trường hợp ứng dụng thực tế mới nhất của: {research_topic}",
                },
            ]

        # Enforce that only allowed delegated providers are used and role_group is set
        sanitized_dispatch: list[dict[str, Any]] = []
        for item in dispatch_items:
            if not item.get("role_group"):
                item["role_group"] = "researcher"
            if delegated_providers:
                pid = str(item.get("id", "")).lower()
                if pid not in delegated_providers:
                    fallback_id = delegated_providers[len(sanitized_dispatch) % len(delegated_providers)]
                    fallback_info = resolve_provider_live_prompt_info(fallback_id, provider_configs.get(fallback_id), provider_capabilities.get(fallback_id))
                    item["id"] = fallback_id
                    item["name"] = fallback_info["name"]
                    if not item.get("config"):
                        item["config"] = fallback_info["default_config"]
            sanitized_dispatch.append(item)
        dispatch_items = sanitized_dispatch

        new_orch_conv_url = str(orch_res.conversation_url) if getattr(orch_res, "conversation_url", None) else None
        orch_conv_url = new_orch_conv_url or orch_conv_url
        orch_duration = round(time.monotonic() - orch_start, 1)
        for idx, item in enumerate(dispatch_items, start=1):
            item["branch_index"] = idx
            item["provider_role_key"] = f"subtask:{item['id']}_{idx}"

        # Update Job with dispatch plan
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                db_j.orchestrator_dispatch_json = json.dumps(dispatch_items, ensure_ascii=False)
                db_j.orchestrator_conversation_url = orch_conv_url
                db_j.subtasks_total = len(dispatch_items)
                db_j.subtasks_done = 0
                db_j.updated_at = utc_now()
                session.add(ProviderRun(
                    id=f"{job_id}:orchestrator:run",
                    subtask_id=f"{job_id}:orchestrator",
                    provider=orchestrator_prov,
                    answer_md=orch_res.answer_markdown,
                    conversation_url=orch_conv_url,
                    status="ok",
                ))
                session.add(JobEvent(
                    job_id=job_id,
                    status="orchestrating",
                    event_type="orchestrator_result",
                    provider=orchestrator_prov,
                    step="orchestrator_result",
                    message=f"Orchestrator ({orchestrator_prov}) đã phân rã thành {len(dispatch_items)} nhiệm vụ nghiên cứu chuyên sâu.",
                    subtasks_total=len(dispatch_items),
                    subtasks_done=0,
                    data_json=json.dumps({
                        "dispatch": dispatch_items,
                        "complexity": complexity_info,
                        "role": "orchestrator",
                        "provider_role_key": "orchestrator",
                        "elapsed_s": orch_duration,
                        "conversation_url": orch_conv_url,
                    }, ensure_ascii=False),
                ))
                await session.commit()

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # ---------------------------------------------------------
        # PHASE 2: RESEARCHING (Parallel dispatch of subtasks)
        # ---------------------------------------------------------
        await _set_agent_status(
            job_id,
            "researching",
            message=f"Bắt đầu điều phối {len(dispatch_items)} tác nhân nghiên cứu đồng thời...",
            subtasks_total=len(dispatch_items),
            subtasks_done=0,
        )

        subtasks: list[Subtask] = []
        async with SessionLocal() as session:
            for idx, item in enumerate(dispatch_items, start=1):
                raw_q = item["question"]
                full_prompt = raw_q
                if context_summary and context_summary.strip():
                    full_prompt = f"""[BỐI CẢNH NGHIÊN CỨU TỪ CÁC VÒNG TRƯỚC]
{context_summary.strip()}

[NHIỆM VỤ NGHIÊN CỨU CHUYÊN SÂU]
{raw_q}"""
                st = Subtask(
                    id=f"{job_id}:{item['id']}_{idx}",
                    job_id=job_id,
                    branch=item.get("sub_topic", f"Nhánh {idx}"),
                    provider=item["id"],
                    prompt=full_prompt,
                )
                subtasks.append(st)
                session.add(st)
            await session.commit()

        sources: list[dict[str, str]] = []
        runs: list[dict[str, Any]] = []
        results_lock = asyncio.Lock()
        total_subtasks = len(subtasks)

        async def _run_subtask(st: Subtask, item_cfg: dict[str, Any], idx: int) -> None:
            if cancel_event.is_set():
                return

            prov = st.provider
            subtask_start = time.monotonic()
            role_key = f"subtask:{prov}_{idx}"
            adapter = create_adapter(prov)
            ask_args: dict[str, Any] = {
                "timeout_s": 600,
                "mode": json.dumps(item_cfg) if item_cfg else "default",
            }
            if "on_step" in inspect.signature(adapter.ask).parameters:
                ask_args["on_step"] = StepEmitter(
                    job_id=job_id,
                    provider=prov,
                    status="researching",
                    role="subtask",
                    cancel_event=cancel_event,
                    subtasks_total=total_subtasks,
                    get_subtasks_done=lambda: len(runs),
                    start_time=subtask_start,
                    extra_payload={
                        "subtask_id": st.id,
                        "branch": st.branch,
                        "branch_index": idx,
                        "provider_role_key": role_key,
                    },
                )
            sub_conv_url = initial_conv_urls.get(role_key) or initial_conv_urls.get(prov)
            if sub_conv_url and ("conversation_url" in inspect.signature(adapter.ask).parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in inspect.signature(adapter.ask).parameters.values())):
                ask_args["conversation_url"] = sub_conv_url

            try:
                result = await adapter.ask(st.prompt, **ask_args)
                status_str = result.status
                ans_text = result.answer_markdown
                res_sources = result.sources
            except Exception as exc:
                logger.error("subtask_execution_failed", provider=prov, error=str(exc))
                status_str = "error"
                ans_text = f"Không thể lấy câu trả lời từ {prov}: {exc}"
                res_sources = []
            finally:
                await BrowserSessionManager.close_session(prov)

            subtask_duration = round(time.monotonic() - subtask_start, 1)
            new_sub_url = str(result.conversation_url) if getattr(result, "conversation_url", None) else None
            sub_conv_url = new_sub_url or sub_conv_url
            async with results_lock:
                run_item = {
                    "provider": prov,
                    "branch": st.branch,
                    "branch_index": idx,
                    "status": status_str,
                    "answer_md": ans_text,
                    "answer_markdown": ans_text,
                    "conversation_url": sub_conv_url,
                    "elapsed_ms": int(subtask_duration * 1000),
                    "elapsed_s": subtask_duration,
                    "subtask_id": st.id,
                    "role": "subtask",
                    "provider_role_key": role_key,
                }
                runs.append(run_item)
                done_cnt = len(runs)

                async with SessionLocal() as s:
                    db_j = await s.get(Job, job_id)
                    db_st = await s.get(Subtask, st.id)
                    if db_st is not None:
                        db_st.status = "completed" if status_str == "ok" else "failed"

                    s.add(ProviderRun(
                        id=f"{job_id}:{prov}_{idx}:run",
                        subtask_id=st.id,
                        provider=prov,
                        answer_md=ans_text,
                        conversation_url=sub_conv_url,
                        status=status_str,
                    ))

                    for src in res_sources:
                        s_id = f"{job_id}:S{len(sources) + 1}"
                        s_dict = {"id": s_id, "url": str(src.url), "title": src.title or "", "provider": prov}
                        sources.append(s_dict)
                        s.add(Source(
                            id=s_id,
                            run_id=f"{job_id}:{prov}_{idx}:run",
                            job_id=job_id,
                            provider=prov,
                            url=str(src.url),
                            title=src.title,
                        ))

                    if db_j is not None:
                        db_j.subtasks_done = done_cnt
                        db_j.provider_runs_json = json.dumps(runs, ensure_ascii=False)
                        db_j.sources_json = json.dumps(sources, ensure_ascii=False)
                        db_j.updated_at = utc_now()
                        s.add(JobEvent(
                            job_id=job_id,
                            status="researching",
                            event_type="progress",
                            provider=prov,
                            step="completed" if status_str == "ok" else "failed",
                            message=f"Đã hoàn thành {done_cnt}/{total_subtasks} tác nhân ({prov}: {status_str}).",
                            subtasks_total=total_subtasks,
                            subtasks_done=done_cnt,
                            data_json=json.dumps({
                                "provider": prov,
                                "branch": st.branch,
                                "branch_index": idx,
                                "status": status_str,
                                "elapsed_s": subtask_duration,
                                "role": "subtask",
                                "subtask_id": st.id,
                                "provider_role_key": role_key,
                                "conversation_url": sub_conv_url,
                            }, ensure_ascii=False),
                        ))
                    await s.commit()

        try:
            if settings.work_mode == "async":
                sem = asyncio.Semaphore(max(1, settings.max_concurrent_browsers))
                async def _throttled_task(st: Subtask, cfg: dict[str, Any], idx: int) -> None:
                    async with sem:
                        if cancel_event.is_set():
                            return
                        await _run_subtask(st, cfg, idx)

                await asyncio.gather(*[
                    _throttled_task(st, dispatch_items[i].get("config", {}), i + 1)
                    for i, st in enumerate(subtasks)
                ])
            else:
                for i, st in enumerate(subtasks):
                    if cancel_event.is_set():
                        break
                    await _run_subtask(st, dispatch_items[i].get("config", {}), i + 1)
        finally:
            await BrowserSessionManager.close_all()

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

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

        # ---------------------------------------------------------
        # PHASE 3: ADVERSARIAL DEBATE (Optional, Red Team vs Defender)
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
                fact_check_claims=fact_check_claims,
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

        # ---------------------------------------------------------
        # PHASE 4: DELPHI CONSENSUS (Optional, Iterative Thesis Scoring)
        # ---------------------------------------------------------
        consensus_result: dict[str, Any] = {}
        enable_consensus = False
        consensus_provs: list[str] = []
        consensus_thresh = 0.8
        max_consensus_rnds = 3

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                enable_consensus = getattr(db_j, "enable_consensus", False)
                try:
                    consensus_provs = json.loads(db_j.consensus_providers_json) if db_j.consensus_providers_json else []
                except Exception:
                    consensus_provs = []
                if not consensus_provs:
                    consensus_provs = delegated_providers[:3] if delegated_providers else [orchestrator_prov, lead_prov]
                consensus_thresh = getattr(db_j, "consensus_threshold", 0.8)
                max_consensus_rnds = getattr(db_j, "max_consensus_rounds", 3)

        if enable_consensus and runs:
            consensus_result = await run_delphi_consensus(
                job_id=job_id,
                research_topic=research_topic,
                runs=runs,
                debate_transcript=debate_transcript,
                consensus_providers=consensus_provs,
                threshold=consensus_thresh,
                max_rounds=max_consensus_rnds,
                cancel_event=cancel_event,
                initial_conv_urls=initial_conv_urls,
            )

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # ---------------------------------------------------------
        # PHASE 5: LEADING (Lead Provider Synthesis)
        # ---------------------------------------------------------
        report_format = "narrative"
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None:
                report_format = getattr(db_j, "report_format", "narrative") or "narrative"

        lead_start = time.monotonic()
        await _set_agent_status(
            job_id,
            "leading",
            message=f"Lead Provider ({lead_prov}) đang tổng hợp báo cáo chuyên sâu (định dạng: {report_format}, văn phong: '{tone}')...",
            data={
                "lead": lead_prov,
                "tone": tone,
                "report_format": report_format,
                "config": lead_config,
                "role": "lead",
                "provider_role_key": "lead",
                "elapsed_s": 0.0,
            },
            subtasks_total=total_subtasks,
            subtasks_done=total_subtasks,
        )

        lead_conv_url = initial_conv_urls.get("lead") or initial_conv_urls.get(lead_prov)
        lead_adapter = create_adapter(lead_prov)

        if report_format == "matrix":
            lead_prompt = build_matrix_report_prompt(
                research_topic,
                runs,
                tone,
                context_summary=context_summary,
                fact_check_claims=fact_check_claims,
                debate_transcript=debate_transcript,
                consensus_result=consensus_result,
            )
        else:
            lead_prompt = build_lead_prompt(
                research_topic,
                runs,
                tone,
                context_summary=context_summary,
                fact_check_claims=fact_check_claims,
                debate_transcript=debate_transcript,
                consensus_result=consensus_result,
            )

        lead_kwargs: dict[str, Any] = {
            "timeout_s": 600,
            "mode": json.dumps(lead_config) if lead_config else "default",
        }
        if "on_step" in inspect.signature(lead_adapter.ask).parameters:
            lead_kwargs["on_step"] = StepEmitter(
                job_id=job_id,
                provider=lead_prov,
                status="leading",
                role="lead",
                cancel_event=cancel_event,
                subtasks_total=total_subtasks,
                get_subtasks_done=lambda: total_subtasks,
                start_time=lead_start,
            )
        if lead_conv_url and ("conversation_url" in inspect.signature(lead_adapter.ask).parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in inspect.signature(lead_adapter.ask).parameters.values())):
            lead_kwargs["conversation_url"] = lead_conv_url

        try:
            lead_res = await lead_adapter.ask(lead_prompt, **lead_kwargs)
            new_lead_url = str(lead_res.conversation_url) if getattr(lead_res, "conversation_url", None) else None
            lead_conv_url = new_lead_url or lead_conv_url

            if report_format == "matrix":
                try:
                    matrix_json = _clean_json_str(lead_res.answer_markdown)
                    matrix_data = json.loads(matrix_json)
                    final_report = render_matrix_to_markdown(matrix_data)
                    async with SessionLocal() as session:
                        db_j = await session.get(Job, job_id)
                        if db_j is not None:
                            db_j.report_matrix_json = json.dumps(matrix_data, ensure_ascii=False)
                            await session.commit()
                except Exception as mx_err:
                    logger.warning("matrix_parse_failed", error=str(mx_err))
                    final_report = lead_res.answer_markdown
            elif report_format == "hybrid":
                narrative_report = lead_res.answer_markdown
                try:
                    matrix_prompt = build_matrix_report_prompt(
                        research_topic,
                        runs,
                        tone,
                        context_summary=context_summary,
                        fact_check_claims=fact_check_claims,
                    )
                    hybrid_kwargs = dict(lead_kwargs)
                    if lead_conv_url and ("conversation_url" in inspect.signature(lead_adapter.ask).parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in inspect.signature(lead_adapter.ask).parameters.values())):
                        hybrid_kwargs["conversation_url"] = lead_conv_url
                    matrix_res = await lead_adapter.ask(matrix_prompt, **hybrid_kwargs)
                    matrix_json = _clean_json_str(matrix_res.answer_markdown)
                    matrix_data = json.loads(matrix_json)
                    rendered_matrix = render_matrix_to_markdown(matrix_data)
                    final_report = f"{narrative_report}\n\n---\n\n{rendered_matrix}"
                    async with SessionLocal() as session:
                        db_j = await session.get(Job, job_id)
                        if db_j is not None:
                            db_j.report_matrix_json = json.dumps(matrix_data, ensure_ascii=False)
                            await session.commit()
                except Exception as hy_err:
                    logger.warning("hybrid_matrix_failed", error=str(hy_err))
                    final_report = narrative_report
            else:
                final_report = lead_res.answer_markdown
        except Exception as exc:
            logger.error("lead_synthesis_failed", provider=lead_prov, error=str(exc))
            # Fallback report compilation
            final_report = f"# Báo cáo Nghiên cứu: {research_topic}\n\n"
            for r in runs:
                final_report += f"## {r.get('branch', r.get('provider'))}\n\n{r.get('answer_md', '')}\n\n"
        finally:
            await BrowserSessionManager.close_session(lead_prov)

        lead_duration = round(time.monotonic() - lead_start, 1)

        if cancel_event.is_set():
            await _set_agent_status(job_id, "cancelled")
            return

        # Complete the job
        ok_count = sum(1 for r in runs if r.get("status") == "ok")
        final_status = "completed" if ok_count > 0 else "failed"

        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None and db_j.status not in TERMINAL_STATUSES:
                db_j.status = final_status
                db_j.report_markdown = final_report
                db_j.lead_conversation_url = lead_conv_url
                db_j.finished_at = utc_now()
                db_j.updated_at = utc_now()

                # Build consolidated map of all provider conversation URLs
                all_convs: dict[str, str] = dict(initial_conv_urls)
                if db_j.orchestrator_conversation_url:
                    all_convs["orchestrator"] = db_j.orchestrator_conversation_url
                if lead_conv_url:
                    all_convs["lead"] = lead_conv_url
                for r in runs:
                    role_key = r.get("provider_role_key") or r.get("provider")
                    if role_key and r.get("conversation_url"):
                        all_convs[role_key] = r["conversation_url"]
                        if r.get("provider") and r["provider"] not in all_convs:
                            all_convs[r["provider"]] = r["conversation_url"]
                db_j.provider_conversations_json = json.dumps(all_convs, ensure_ascii=False)

                session.add(Report(id=job_id, job_id=job_id, markdown=final_report))
                session.add(ProviderRun(
                    id=f"{job_id}:lead:run",
                    subtask_id=f"{job_id}:lead",
                    provider=lead_prov,
                    answer_md=final_report,
                    conversation_url=lead_conv_url,
                    status="ok" if final_status == "completed" else "partial",
                ))
                session.add(JobEvent(
                    job_id=job_id,
                    status=final_status,
                    event_type="progress",
                    provider=lead_prov,
                    step="completed",
                    message=f"Nhiệm vụ nghiên cứu đa tác nhân hoàn thành ({final_status}).",
                    subtasks_total=total_subtasks,
                    subtasks_done=total_subtasks,
                    data_json=json.dumps({
                        "lead_provider": lead_prov,
                        "elapsed_s": lead_duration,
                        "role": "lead",
                        "provider_role_key": "lead",
                        "tone": tone,
                        "conversation_url": lead_conv_url,
                    }, ensure_ascii=False),
                ))
                await session.commit()

        logger.info("run_agent_pipeline_finished", job_id=job_id, status=final_status)
        await BrowserSessionManager.close_all()

    except asyncio.CancelledError:
        logger.info("run_agent_pipeline_cancelled", job_id=job_id)
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None and db_j.status not in TERMINAL_STATUSES:
                db_j.status = "cancelled"
                db_j.finished_at = utc_now()
                db_j.updated_at = utc_now()
                session.add(JobEvent(
                    job_id=job_id,
                    status="cancelled",
                    event_type="progress",
                    message="Người dùng đã dừng phiên nghiên cứu tác nhân.",
                ))
                await session.commit()
        notify_job_event(job_id)
        await BrowserSessionManager.close_all()
        raise

    except Exception as exc:
        logger.exception("agent_pipeline_fatal_error", job_id=job_id, error=str(exc))
        async with SessionLocal() as session:
            db_j = await session.get(Job, job_id)
            if db_j is not None and db_j.status not in TERMINAL_STATUSES:
                db_j.status = "failed"
                db_j.error = f"Lỗi hệ thống tác nhân: {exc}"
                db_j.finished_at = utc_now()
                db_j.updated_at = utc_now()
                session.add(JobEvent(job_id=job_id, status="failed", event_type="progress", message=f"Lỗi hệ thống tác nhân: {exc}"))
                await session.commit()
