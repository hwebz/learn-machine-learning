from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import structlog

from app.adapters.capabilities import CapabilitiesRegistry

logger = structlog.get_logger(__name__)

# Fallback catalog metadata for providers
PROVIDER_CATALOG: dict[str, dict[str, Any]] = {
    "chatgpt": {"name": "ChatGPT", "desc": "General synthesis, code, structured explanations, multi-step reasoning."},
    "perplexity": {"name": "Perplexity", "desc": "Real-time search, finding live citations, latest statistics, academic papers."},
    "gemini": {"name": "Gemini", "desc": "Deep conceptual reasoning, multimodal data, broad context analysis."},
    "copilot": {"name": "Microsoft Copilot", "desc": "Enterprise research, web grounding, business applications."},
    "qwen": {"name": "Qwen", "desc": "Technical analysis, mathematics, deep Chinese/English bilingual queries."},
    "kimi": {"name": "Moonshot Kimi", "desc": "Long-form context synthesis, document deep dives."},
    "zhipu": {"name": "Zhipu AI GLM", "desc": "Structured knowledge, bilingual analysis."},
    "deepseek": {"name": "DeepSeek", "desc": "Deep algorithmic thinking, rigorous logic, mathematical formulations."},
    "claude": {"name": "Anthropic Claude", "desc": "Rigorous logical analysis, nuanced writing, academic critique."},
    "grok": {"name": "xAI Grok", "desc": "Real-time discovery, contrarian thinking, edge-case analysis."},
    "mistral": {"name": "Mistral Le Chat", "desc": "Concise reasoning, European multilingual benchmarks, fast inference."},
    "minimax": {"name": "MiniMax", "desc": "Document processing, creative angles, conversational reasoning."},
    "meta": {"name": "Meta AI", "desc": "Open foundation research, general knowledge synthesis."},
    "pi": {"name": "Inflection Pi", "desc": "Exploratory inquiry, accessible explanations."},
}


@dataclass(slots=True)
class ProviderPromptContext:
    provider_id: str
    name: str
    is_live_dom: bool
    pcfg: dict[str, Any]
    caps_dict: dict[str, Any]
    available_models: list[str]
    chosen_model: str | None
    thinking_levels: list[str]
    chosen_thinking: str | None
    modes: list[str]
    chosen_mode: str | None
    is_dr: bool
    is_dt: bool
    is_ws: bool
    deep_thinking_cap: Any
    base_info: dict[str, Any]


# Type alias for provider spec resolver: returns (config_schema, active_summary, role, default_config)
ProviderSpecResolver = Callable[[ProviderPromptContext], tuple[str, str, str, dict[str, Any]]]

_PROVIDER_SPEC_REGISTRY: dict[str, ProviderSpecResolver] = {}


def register_provider_spec(provider_id: str):
    """Decorator to register a provider-specific prompt & schema resolution function."""
    def decorator(fn: ProviderSpecResolver):
        _PROVIDER_SPEC_REGISTRY[provider_id.lower()] = fn
        return fn
    return decorator


@register_provider_spec("gemini")
def _resolve_gemini_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_model = ctx.chosen_model or "gemini-3.1-pro"
    active_thinking = ctx.chosen_thinking or "high"
    avail_str = " | ".join(f'"{m}"' for m in (ctx.available_models or ["gemini-3.1-pro", "gemini-3.8-flash", "gemini-4-argon"]))
    config_schema = f'{{"model": {avail_str}, "thinking": "low" | "medium" | "high", "deep_research": boolean}}'
    active_summary = f'Model="{active_model}", Thinking Level="{active_thinking}", Deep Research={"Active" if ctx.is_dr else "Off"}'
    role = "Deep conceptual reasoning, cross-domain multimodal synthesis, theoretical foundations and math."
    default_cfg = {"model": active_model, "thinking": active_thinking, "deep_research": ctx.is_dr}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("minimax")
def _resolve_minimax_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_model = ctx.chosen_model or "m3.1-flash"
    avail_str = " | ".join(f'"{m}"' for m in (ctx.available_models or ["m3.1-flash", "m3", "m2.7"]))
    config_schema = f'{{"model": {avail_str}, "deep_research": boolean}}'
    active_summary = f'Model="{active_model}", Deep Research={"Active" if ctx.is_dr else "Off"}'
    role = "Document deep processing, high-speed long-form extraction, comprehensive data retrieval and practical execution."
    default_cfg = {"model": active_model, "deep_research": ctx.is_dr}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("meta")
def _resolve_meta_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    is_meta_thinking = True if (
        ctx.chosen_thinking == "thinking"
        or ctx.is_dt
        or ctx.pcfg.get("thinking") is True
        or ctx.pcfg.get("thinking") == "thinking"
    ) else False
    active_meta_thinking = "thinking" if is_meta_thinking else "instant"
    config_schema = '{"thinking": "thinking" | "instant"}'
    active_summary = f'Thinking Mode="{active_meta_thinking}" (DOM toggle: Thinking vs Instant; no model dropdown)'
    role = "Open foundation models synthesis, open science perspectives, HTML/code representations and structured knowledge extraction."
    default_cfg = {"thinking": active_meta_thinking}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("chatgpt")
def _resolve_chatgpt_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_thinking_bool = bool(ctx.pcfg.get("deep_thinking", ctx.pcfg.get("thinking", True)))
    config_schema = '{"thinking": boolean, "deep_research": boolean, "web_search": boolean}'
    active_summary = f'Thinking={"Active" if active_thinking_bool else "Off"}, Deep Research={"Active" if ctx.is_dr else "Off"}, Web Search={"Active" if ctx.is_ws else "Off"}'
    role = "Software architecture, algorithmic engineering, multi-step structured reasoning, reproducible code."
    default_cfg = {"thinking": active_thinking_bool, "deep_research": ctx.is_dr, "web_search": ctx.is_ws}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("qwen")
def _resolve_qwen_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_model = ctx.chosen_model or "qwen-3.8-max"
    active_thinking = ctx.chosen_thinking or "auto"
    avail_str = " | ".join(f'"{m}"' for m in (ctx.available_models or ["qwen-3.8-max", "qwen-3.7-plus"]))
    config_schema = f'{{"model": {avail_str}, "thinking": "auto" | "thinking" | "fast", "deep_research": boolean, "web_search": boolean}}'
    active_summary = f'Model="{active_model}", Thinking="{active_thinking}", Deep Research={"Active" if ctx.is_dr else "Off"}, Web Search={"Active" if ctx.is_ws else "Off"}'
    role = "Frontier math and code benchmarks, multilingual Chinese/global scientific papers and technical specifications."
    default_cfg = {"model": active_model, "thinking": active_thinking, "deep_research": ctx.is_dr, "web_search": ctx.is_ws}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("copilot")
def _resolve_copilot_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    avail_str = " | ".join(f'"{m}"' for m in (ctx.modes or ["auto", "quick", "think_deeper", "gpt_5_6_quick", "gpt_5_6_think"]))
    active_mode = ctx.chosen_mode or "gpt_5_6_think"
    config_schema = f'{{"mode": {avail_str}}}'
    active_summary = f'Mode="{active_mode}" (Microsoft 365 Copilot reasoning with live web grounding)'
    role = "Enterprise business impact, commercial viability, corporate governance, industry market trends and Microsoft ecosystem analysis."
    default_cfg = {"mode": active_mode}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("deepseek")
def _resolve_deepseek_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_dt = bool(ctx.pcfg.get("deep_thinking", ctx.deep_thinking_cap if ctx.deep_thinking_cap is not None else True))
    config_schema = '{"deep_thinking": boolean, "web_search": boolean}'
    active_summary = f'DeepThink R1={"Active" if active_dt else "Off"}, Web Search={"Active" if ctx.is_ws else "Off"}'
    role = "Deep algorithmic proofs, formal mathematical logic, chain-of-thought verification and code optimization."
    default_cfg = {"deep_thinking": active_dt, "web_search": ctx.is_ws}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("claude")
def _resolve_claude_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_model = ctx.chosen_model or "claude-sonnet-5.5"
    active_thinking = ctx.chosen_thinking or "high"
    avail_str = " | ".join(f'"{m}"' for m in (ctx.available_models or ["claude-sonnet-5.5", "claude-haiku-5.5"]))
    config_schema = f'{{"model": {avail_str}, "thinking": "low" | "medium" | "high" | "max"}}'
    active_summary = f'Model="{active_model}", Thinking Budget="{active_thinking}"'
    role = "Nuanced academic critique, formal methodology, scholarly writing and ethical considerations."
    default_cfg = {"model": active_model, "thinking": active_thinking}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("perplexity")
def _resolve_perplexity_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    config_schema = '{"web_search": true}'
    active_summary = "Web Search=Active (Live online citations & sources)"
    role = "Real-time 2026 data, factual verification, authoritative citations and academic references."
    default_cfg = {"web_search": True}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("kimi")
def _resolve_kimi_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_model = ctx.chosen_model or "k3"
    active_thinking = ctx.chosen_thinking or "high"
    config_schema = '{"model": "k3" | "instant", "thinking": "high" | "medium" | "low", "deep_research": boolean}'
    active_summary = f'Model="{active_model}", Thinking="{active_thinking}", Deep Research={"Active" if ctx.is_dr else "Off"}'
    role = "Long-form document deep dives, comprehensive technical reports and policy cross-referencing."
    default_cfg = {"model": active_model, "thinking": active_thinking, "deep_research": ctx.is_dr}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("mistral")
def _resolve_mistral_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_thinking = ctx.chosen_thinking or "think"
    config_schema = '{"thinking": "think" | "fast", "deep_research": boolean}'
    active_summary = f'Thinking="{active_thinking}", Deep Research={"Active" if ctx.is_dr else "Off"}'
    role = "European multilingual benchmarks, fast analytical inference and concise technical reasoning."
    default_cfg = {"thinking": active_thinking, "deep_research": ctx.is_dr}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("zhipu")
def _resolve_zhipu_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_model = ctx.chosen_model or "glm-5.3"
    active_mode = ctx.chosen_mode or "high"
    avail_str = " | ".join(f'"{m}"' for m in (ctx.available_models or ["glm-5.3", "glm-5.3-flash"]))
    config_schema = f'{{"model": {avail_str}, "mode": "low" | "high" | "max"}}'
    active_summary = f'Model="{active_model}", Mode="{active_mode}"'
    role = "Structured bilingual knowledge, ontology mapping, Asian technology developments."
    default_cfg = {"model": active_model, "mode": active_mode}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("grok")
def _resolve_grok_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    active_thinking_bool = bool(ctx.pcfg.get("deep_thinking", ctx.pcfg.get("thinking", True)))
    config_schema = '{"thinking": boolean}'
    active_summary = f'Thinking={"Active" if active_thinking_bool else "Off"}'
    role = "Real-time pulse, contrarian angles, edge-case vulnerability assessment."
    default_cfg = {"thinking": active_thinking_bool}
    return config_schema, active_summary, role, default_cfg


@register_provider_spec("pi")
def _resolve_pi_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    config_schema = '{"thinking": boolean}'
    active_summary = "Conversational dialogue mode"
    role = "Pedagogic breakdown, accessible explanations, intuitive analogies."
    default_cfg = {"thinking": True}
    return config_schema, active_summary, role, default_cfg


def _resolve_default_spec(ctx: ProviderPromptContext) -> tuple[str, str, str, dict[str, Any]]:
    config_schema = '{"thinking": boolean}'
    active_summary = "Standard default configuration"
    role = ctx.base_info.get("desc", "Specialized research synthesis.")
    default_cfg = {"thinking": True}
    return config_schema, active_summary, role, default_cfg


def resolve_provider_live_prompt_info(
    provider_id: str,
    user_config: dict[str, Any] | None = None,
    caps_data: Any | None = None,
) -> dict[str, Any]:
    """Inspects live DOM capabilities and user configs to resolve exact parameters for orchestrator prompt."""
    p = provider_id.lower()
    pcfg = user_config or {}

    caps_dict: dict[str, Any] = {}
    if caps_data is not None:
        if isinstance(caps_data, dict):
            caps_dict = caps_data
        elif hasattr(caps_data, "model_dump"):
            caps_dict = caps_data.model_dump()
        else:
            try:
                caps_dict = dict(caps_data)
            except Exception:
                caps_dict = {}

    if not caps_dict:
        try:
            reg = CapabilitiesRegistry.instance()
            cached_caps = reg._cache.get(p)
            if cached_caps is not None:
                caps_dict = cached_caps.model_dump()
            else:
                caps_dict = reg.get_strategy(p).get_default_capabilities().model_dump()
        except Exception as exc:
            logger.warning("resolve_live_caps_fallback", provider=p, error=str(exc))
            caps_dict = {}

    is_live_dom = bool(caps_dict.get("is_live_dom", False))
    available_models = [
        m.get("id") for m in caps_dict.get("available_models", [])
        if isinstance(m, dict) and m.get("id") and not m.get("disabled")
    ]
    selected_model_id = caps_dict.get("selected_model_id")
    thinking_levels = [
        t.get("id") for t in caps_dict.get("thinking_levels", [])
        if isinstance(t, dict) and t.get("id")
    ]
    selected_thinking_level_id = caps_dict.get("selected_thinking_level_id")
    modes = [
        m.get("id") for m in caps_dict.get("modes", [])
        if isinstance(m, dict) and m.get("id")
    ]
    selected_mode_id = caps_dict.get("selected_mode_id")

    deep_thinking_cap = caps_dict.get("deep_thinking")
    deep_research_cap = caps_dict.get("deep_research")
    web_search_cap = caps_dict.get("web_search")

    chosen_model = (
        pcfg.get("model_id")
        or pcfg.get("model")
        or selected_model_id
        or (available_models[0] if available_models else None)
    )
    chosen_thinking = (
        pcfg.get("thinking_level_id")
        or (pcfg.get("thinking") if isinstance(pcfg.get("thinking"), str) else None)
        or selected_thinking_level_id
        or (thinking_levels[0] if thinking_levels else None)
    )
    chosen_mode = (
        pcfg.get("mode_id")
        or pcfg.get("mode")
        or selected_mode_id
        or (modes[0] if modes else None)
    )

    is_dr = (
        bool(pcfg["deep_research"])
        if pcfg.get("deep_research") is not None
        else (bool(deep_research_cap) if deep_research_cap is not None else False)
    )
    is_dt = (
        bool(pcfg["deep_thinking"])
        if pcfg.get("deep_thinking") is not None
        else (bool(deep_thinking_cap) if deep_thinking_cap is not None else False)
    )
    is_ws = (
        bool(pcfg["web_search"])
        if pcfg.get("web_search") is not None
        else (bool(web_search_cap) if web_search_cap is not None else True)
    )

    base_info = PROVIDER_CATALOG.get(p, {})
    name = base_info.get("name") or p.capitalize()

    ctx = ProviderPromptContext(
        provider_id=p,
        name=name,
        is_live_dom=is_live_dom,
        pcfg=pcfg,
        caps_dict=caps_dict,
        available_models=available_models,
        chosen_model=chosen_model,
        thinking_levels=thinking_levels,
        chosen_thinking=chosen_thinking,
        modes=modes,
        chosen_mode=chosen_mode,
        is_dr=is_dr,
        is_dt=is_dt,
        is_ws=is_ws,
        deep_thinking_cap=deep_thinking_cap,
        base_info=base_info,
    )

    resolver = _PROVIDER_SPEC_REGISTRY.get(p, _resolve_default_spec)
    config_schema, active_summary, role, default_cfg = resolver(ctx)

    return {
        "id": p,
        "name": name,
        "is_live_dom": is_live_dom,
        "active_summary": active_summary,
        "config_schema": config_schema,
        "role": role,
        "default_config": default_cfg,
    }
