import { ProviderInfo } from "../types/chat";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../types/capabilities";

export interface ResolvedSubProviderConfig {
  id: string;
  isLiveDom: boolean;
  activeModel?: string;
  activeThinking?: string;
  isDeepResearch: boolean;
  isDeepThinking: boolean;
  isWebSearch: boolean;
  activeSummary: string;
  configSchema: string;
  role: string;
  configObj: Record<string, any>;
}

/**
 * Resolves live DOM capabilities and user choices for a delegated sub-provider.
 */
export function resolveSubProviderLiveConfig(
  providerId: string,
  selectionsMap: Record<string, ProviderSelectionConfig> = {},
  capabilitiesMap: Record<string, ProviderLiveCapabilities> = {}
): ResolvedSubProviderConfig {
  const p = providerId.toLowerCase();
  const sel = selectionsMap[p] || {};
  const caps = capabilitiesMap[p];
  const isLiveDom = Boolean(caps?.is_live_dom);

  const availableModels = (caps?.available_models || []).filter((m) => !m.disabled).map((m) => m.id);
  const selectedModelId = caps?.selected_model_id;
  const thinkingLevels = (caps?.thinking_levels || []).map((t) => t.id);
  const selectedThinkingLevelId = caps?.selected_thinking_level_id;
  const modes = (caps?.modes || []).map((m) => m.id);
  const selectedModeId = caps?.selected_mode_id;

  const chosenModel = sel.model_id || selectedModelId || (availableModels.length > 0 ? availableModels[0] : undefined);
  const chosenThinking = sel.thinking_level_id || selectedThinkingLevelId || (thinkingLevels.length > 0 ? thinkingLevels[0] : undefined);
  const chosenMode = sel.mode_id || selectedModeId || (modes.length > 0 ? modes[0] : undefined);

  const isDr = sel.deep_research !== undefined ? sel.deep_research : Boolean(caps?.deep_research);
  const isDt = sel.deep_thinking !== undefined ? sel.deep_thinking : Boolean(caps?.deep_thinking);
  const isWs = sel.web_search !== undefined ? sel.web_search : (caps?.web_search !== undefined ? caps.web_search : true);

  let activeModel = chosenModel;
  let activeThinking = chosenThinking;
  let activeSummary = "";
  let configSchema = "";
  let role = "";
  let configObj: Record<string, any> = {};

  if (p === "gemini") {
    activeModel = chosenModel || "gemini-3.1-pro";
    activeThinking = chosenThinking || "high";
    const availStr = (availableModels.length > 0 ? availableModels : ["gemini-3.1-pro", "gemini-3.8-flash", "gemini-4-argon"]).map((m) => `"${m}"`).join(" | ");
    configSchema = `{"model": ${availStr}, "thinking": "low" | "medium" | "high", "deep_research": boolean}`;
    activeSummary = `Model="${activeModel}", Thinking="${activeThinking}"${isDr ? ", Deep Research=Active" : ""}`;
    role = "Deep conceptual reasoning, cross-domain multimodal synthesis, theoretical foundations and math.";
    configObj = { model: activeModel, model_id: activeModel, thinking: activeThinking, thinking_level_id: activeThinking, deep_research: isDr };
  } else if (p === "minimax") {
    activeModel = chosenModel || "m3.1-flash";
    const availStr = (availableModels.length > 0 ? availableModels : ["m3.1-flash", "m3", "m2.7"]).map((m) => `"${m}"`).join(" | ");
    configSchema = `{"model": ${availStr}, "deep_research": boolean}`;
    activeSummary = `Model="${activeModel}"${isDr ? ", Deep Research=Active" : ""}`;
    role = "Document deep processing, high-speed long-form extraction, comprehensive data retrieval and practical execution.";
    configObj = { model: activeModel, model_id: activeModel, deep_research: isDr };
  } else if (p === "meta") {
    const isMetaThinking = chosenThinking === "thinking" || isDt;
    const metaMode = isMetaThinking ? "thinking" : "instant";
    configSchema = `{"thinking": "thinking" | "instant"}`;
    activeSummary = `Thinking Mode="${metaMode}" (DOM 2-option toggle: Thinking vs Instant; no model dropdown)`;
    role = "Open foundation models synthesis, open science perspectives, HTML/code representations and structured knowledge extraction.";
    configObj = { thinking: metaMode, thinking_level_id: metaMode, deep_thinking: isMetaThinking };
  } else if (p === "chatgpt") {
    configSchema = `{"thinking": boolean, "deep_research": boolean, "web_search": boolean}`;
    activeSummary = `Thinking=${isDt ? "Active" : "Off"}, Deep Research=${isDr ? "Active" : "Off"}, Web Search=${isWs ? "Active" : "Off"}`;
    role = "Software architecture, algorithmic engineering, multi-step structured reasoning, reproducible code.";
    configObj = { thinking: isDt, deep_thinking: isDt, deep_research: isDr, web_search: isWs };
  } else if (p === "qwen") {
    activeModel = chosenModel || "qwen-3.8-max";
    activeThinking = chosenThinking || "auto";
    const availStr = (availableModels.length > 0 ? availableModels : ["qwen-3.8-max", "qwen-3.7-plus"]).map((m) => `"${m}"`).join(" | ");
    configSchema = `{"model": ${availStr}, "thinking": "auto" | "thinking" | "fast", "deep_research": boolean, "web_search": boolean}`;
    activeSummary = `Model="${activeModel}", Thinking="${activeThinking}"${isDr ? ", Deep Research=Active" : ""}`;
    role = "Frontier math and code benchmarks, multilingual Chinese/global scientific papers and technical specifications.";
    configObj = { model: activeModel, model_id: activeModel, thinking: activeThinking, thinking_level_id: activeThinking, deep_research: isDr, web_search: isWs };
  } else if (p === "copilot") {
    const activeMode = chosenMode || "gpt_5_6_think";
    const availStr = (modes.length > 0 ? modes : ["auto", "quick", "think_deeper", "gpt_5_6_quick", "gpt_5_6_think"]).map((m) => `"${m}"`).join(" | ");
    configSchema = `{"mode": ${availStr}}`;
    activeSummary = `Mode="${activeMode}" (Microsoft 365 Copilot with live web grounding)`;
    role = "Enterprise business impact, commercial viability, corporate governance, industry market trends and Microsoft ecosystem analysis.";
    configObj = { mode: activeMode, mode_id: activeMode };
  } else if (p === "deepseek") {
    configSchema = `{"deep_thinking": boolean, "web_search": boolean}`;
    activeSummary = `DeepThink R1=${isDt ? "Active" : "Off"}, Web Search=${isWs ? "Active" : "Off"}`;
    role = "Deep algorithmic proofs, formal mathematical logic, chain-of-thought verification and code optimization.";
    configObj = { deep_thinking: isDt, web_search: isWs };
  } else if (p === "claude") {
    activeModel = chosenModel || "claude-sonnet-5.5";
    activeThinking = chosenThinking || "high";
    const availStr = (availableModels.length > 0 ? availableModels : ["claude-sonnet-5.5", "claude-haiku-5.5"]).map((m) => `"${m}"`).join(" | ");
    configSchema = `{"model": ${availStr}, "thinking": "low" | "medium" | "high" | "max"}}`;
    activeSummary = `Model="${activeModel}", Thinking="${activeThinking}"`;
    role = "Nuanced academic critique, formal methodology, scholarly writing and ethical considerations.";
    configObj = { model: activeModel, model_id: activeModel, thinking: activeThinking, thinking_level_id: activeThinking };
  } else if (p === "perplexity") {
    configSchema = `{"web_search": true}`;
    activeSummary = "Web Search=Active (Live online citations & sources)";
    role = "Real-time 2026 data, factual verification, authoritative citations and academic references.";
    configObj = { web_search: true };
  } else if (p === "kimi") {
    activeModel = chosenModel || "k3";
    activeThinking = chosenThinking || "high";
    configSchema = `{"model": "k3" | "instant", "thinking": "high" | "medium" | "low", "deep_research": boolean}`;
    activeSummary = `Model="${activeModel}", Thinking="${activeThinking}"${isDr ? ", Deep Research=Active" : ""}`;
    role = "Long-form document deep dives, comprehensive technical reports and policy cross-referencing.";
    configObj = { model: activeModel, model_id: activeModel, thinking: activeThinking, thinking_level_id: activeThinking, deep_research: isDr };
  } else if (p === "mistral") {
    activeThinking = chosenThinking || "think";
    configSchema = `{"thinking": "think" | "fast", "deep_research": boolean}`;
    activeSummary = `Thinking="${activeThinking}"${isDr ? ", Deep Research=Active" : ""}`;
    role = "European multilingual benchmarks, fast analytical inference and concise technical reasoning.";
    configObj = { thinking: activeThinking, thinking_level_id: activeThinking, deep_research: isDr };
  } else if (p === "zhipu") {
    activeModel = chosenModel || "glm-5.3";
    const activeMode = chosenMode || "high";
    const availStr = (availableModels.length > 0 ? availableModels : ["glm-5.3", "glm-5.3-flash"]).map((m) => `"${m}"`).join(" | ");
    configSchema = `{"model": ${availStr}, "mode": "low" | "high" | "max"}}`;
    activeSummary = `Model="${activeModel}", Mode="${activeMode}"`;
    role = "Structured bilingual knowledge, ontology mapping, Asian technology developments.";
    configObj = { model: activeModel, model_id: activeModel, mode: activeMode, mode_id: activeMode };
  } else if (p === "grok") {
    configSchema = `{"thinking": boolean}`;
    activeSummary = `Thinking=${isDt ? "Active" : "Off"}`;
    role = "Real-time pulse, contrarian angles, edge-case vulnerability assessment.";
    configObj = { thinking: isDt, deep_thinking: isDt };
  } else if (p === "pi") {
    configSchema = `{"thinking": boolean}`;
    activeSummary = "Conversational dialogue mode";
    role = "Pedagogic breakdown, accessible explanations, intuitive analogies.";
    configObj = { thinking: true };
  } else {
    configSchema = `{"thinking": boolean}`;
    activeSummary = "Cấu hình mặc định";
    role = "Nghiên cứu chuyên môn và tổng hợp thông tin.";
    configObj = { thinking: true };
  }

  return {
    id: p,
    isLiveDom,
    activeModel,
    activeThinking,
    isDeepResearch: isDr,
    isDeepThinking: isDt,
    isWebSearch: isWs,
    activeSummary,
    configSchema,
    role,
    configObj,
  };
}

/**
 * Constructs the Master Orchestrator task decomposition prompt using live DOM capabilities.
 */
export function constructOrchestrationPrompt(
  topic: string,
  selectedDelegatedProviders: string[],
  capabilitiesMap: Record<string, ProviderLiveCapabilities>,
  selectionsMap: Record<string, ProviderSelectionConfig>,
  providersList: ProviderInfo[]
): string {
  const providersText = selectedDelegatedProviders
    .map((pid, idx) => {
      const pObj = providersList.find((p) => p.id === pid);
      const name = pObj?.name || pid.toUpperCase();
      const cfg = resolveSubProviderLiveConfig(pid, selectionsMap, capabilitiesMap);
      const badge = cfg.isLiveDom ? "[REAL DOM SYNCED]" : "[LATEST LIVE CONFIG]";
      return `${idx + 1}. ${name} (id: "${pid}") ${badge}\n   - Active DOM Setting: ${cfg.activeSummary}\n   - Expected "config" JSON Schema: ${cfg.configSchema}\n   - Specialized Sub-topic Role: ${cfg.role}`;
    })
    .join("\n");

  const allowedIdsStr = selectedDelegatedProviders.map((pid) => `"${pid}"`).join(", ");

  return `You are a Master Research Orchestrator.
Your goal is to analyze the research topic provided by the user and intelligently decompose it into 2 to 5 specialized sub-tasks.
Each sub-task must be assigned to the most appropriate AI provider from the ALLOWED providers list below.

## Available Allowed Providers and Configurations (Live DOM Synced):
${providersText || "Chưa có provider nào được chọn."}

## STRICT REQUIREMENT: Allowed Delegation Providers
You are STRICTLY RESTRICTED to assigning sub-tasks ONLY to providers in this allowed list: [${allowedIdsStr}].
DO NOT assign any sub-task to any provider outside this list. Every single item in "agents_dispatch" MUST have "id" strictly matching one of [${allowedIdsStr}].

## Rules:
- Decompose the topic into 2 to 5 distinct, non-overlapping specialized sub-topics.
- Assign each sub-topic to the provider best suited for that angle among the allowed providers, matching their active capabilities and strengths described above.
- In each "agents_dispatch" item, provide a valid "config" object that matches the provider's active DOM setting and expected schema.
- Each "question" must be a self-contained, detailed prompt for that provider to investigate.
- The output MUST be strictly valid JSON matching the schema below. Do not wrap in markdown or add explanations.

## Output JSON Schema:
{
  "research_topic": "${topic || "<Chủ đề nghiên cứu>"}",
  "agents_dispatch": [
    {
      "id": "<provider_id>",
      "name": "<provider_name>",
      "config": { ... },
      "sub_topic": "<Brief specialized sub-topic title>",
      "question": "<Detailed research prompt tailored for this provider's capabilities>"
    }
  ]
}

Research Topic to decompose:
${topic || "<Chủ đề nghiên cứu>"}`;
}
