"use client";

import React, { useState, useEffect, useMemo } from "react";
import { PROVIDERS_LIST, TONE_PRESETS } from "../../lib/constants";
import { ProviderInfo } from "../../types/chat";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";
import { BrainIcon, CloseIcon, ModelBadgeLogo, RefreshIcon, SearchIcon, SparklesIcon } from "../icons/Icons";

interface AgentConfigScreenProps {
  onStartAgentResearch: (config: {
    query: string;
    orchestrator_provider: string;
    orchestrator_config: Record<string, any>;
    lead_provider: string;
    lead_config: Record<string, any>;
    tone: string;
    delegated_providers?: string[];
  }) => void;
  onCancel: () => void;
  providers?: ProviderInfo[];
  capabilitiesMap?: Record<string, ProviderLiveCapabilities>;
  selectionsMap?: Record<string, ProviderSelectionConfig>;
  onUpdateSelection?: (providerId: string, updates: Partial<ProviderSelectionConfig>) => void;
  onSyncProvider?: (providerId: string) => Promise<any>;
  loadingProvider?: string | null;
  onLoadCapabilities?: (providerId: string) => void;
}

const SUGGESTED_AGENT_TOPICS = [
  "Ứng dụng của Deep Learning trong đời sống và y học hiện đại",
  "So sánh cơ chế Thinking & Reasoning giữa Gemini 3.1 Pro, ChatGPT o3 và DeepSeek R1",
  "Khảo sát kiến trúc Agentic AI và khả năng tự động phân rã nhiệm vụ (Task Decomposition)",
  "Xu hướng bán dẫn và chip tăng tốc AI (GPU vs NPU vs TPU) giai đoạn 2026-2030",
];

export function AgentConfigScreen({
  onStartAgentResearch,
  onCancel,
  providers,
  capabilitiesMap = {},
  selectionsMap = {},
  onUpdateSelection,
  onSyncProvider,
  loadingProvider,
  onLoadCapabilities,
}: AgentConfigScreenProps) {
  // Use all providers implemented in normal chat mode
  const availableProviders = providers && providers.length > 0 ? providers : PROVIDERS_LIST;

  const [query, setQuery] = useState("");
  const [selectedOrchestrator, setSelectedOrchestrator] = useState<string>("gemini");
  const [orchThinking, setOrchThinking] = useState<boolean>(true);
  const [orchThinkingLevel, setOrchThinkingLevel] = useState<string>("auto");
  const [orchModel, setOrchModel] = useState<string>("pro");
  const [orchMode, setOrchMode] = useState<string>("high");
  const [orchDeepThinking, setOrchDeepThinking] = useState<boolean>(false);
  const [orchWebSearch, setOrchWebSearch] = useState<boolean>(true);
  const [orchDeepResearch, setOrchDeepResearch] = useState<boolean>(false);
  const [orchResearchMode, setOrchResearchMode] = useState<string>("normal");
  const [isSyncingOrch, setIsSyncingOrch] = useState(false);
  const [orchSyncMessage, setOrchSyncMessage] = useState<string | null>(null);

  // Sub-providers delegation state (default to top reasoning models)
  const DEFAULT_DELEGATED = ["copilot", "gemini", "chatgpt", "deepseek", "qwen", "perplexity", "claude"];
  const [selectedDelegatedProviders, setSelectedDelegatedProviders] = useState<string[]>(DEFAULT_DELEGATED);

  const [selectedLead, setSelectedLead] = useState<string>("chatgpt");
  const [leadThinking, setLeadThinking] = useState<boolean>(true);
  const [leadThinkingLevel, setLeadThinkingLevel] = useState<string>("auto");
  const [leadModel, setLeadModel] = useState<string>("default");
  const [leadMode, setLeadMode] = useState<string>("standard");
  const [leadDeepThinking, setLeadDeepThinking] = useState<boolean>(false);
  const [leadWebSearch, setLeadWebSearch] = useState<boolean>(true);
  const [leadDeepResearch, setLeadDeepResearch] = useState<boolean>(false);
  const [leadResearchMode, setLeadResearchMode] = useState<string>("normal");
  const [isSyncingLead, setIsSyncingLead] = useState(false);
  const [leadSyncMessage, setLeadSyncMessage] = useState<string | null>(null);

  const [selectedTone, setSelectedTone] = useState<string>("professional");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auto-fetch capabilities if not cached when provider selected
  useEffect(() => {
    if (onLoadCapabilities && selectedOrchestrator && !capabilitiesMap[selectedOrchestrator]) {
      onLoadCapabilities(selectedOrchestrator);
    }
  }, [selectedOrchestrator, capabilitiesMap, onLoadCapabilities]);

  useEffect(() => {
    if (onLoadCapabilities && selectedLead && !capabilitiesMap[selectedLead]) {
      onLoadCapabilities(selectedLead);
    }
  }, [selectedLead, capabilitiesMap, onLoadCapabilities]);

  const orchProviderObj = availableProviders.find((p) => p.id === selectedOrchestrator);
  const leadProviderObj = availableProviders.find((p) => p.id === selectedLead);

  const orchCaps = capabilitiesMap[selectedOrchestrator];
  const orchSel = selectionsMap[selectedOrchestrator];

  const leadCaps = capabilitiesMap[selectedLead];
  const leadSel = selectionsMap[selectedLead];

  // Helper to format synced time
  const formatSyncTime = (timestamp?: string) => {
    if (!timestamp) return null;
    try {
      return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return null;
    }
  };

  // Sync Orchestrator local state when capabilities or selections update
  useEffect(() => {
    if (selectedOrchestrator === "deepseek") {
      setOrchModel("");
      setOrchThinkingLevel("");
      setOrchMode("");
      if (orchSel?.deep_thinking !== undefined) {
        setOrchDeepThinking(orchSel.deep_thinking);
      } else if (orchCaps?.deep_thinking !== undefined) {
        setOrchDeepThinking(orchCaps.deep_thinking);
      }
      if (orchSel?.web_search !== undefined) {
        setOrchWebSearch(orchSel.web_search);
      } else if (orchCaps?.web_search !== undefined) {
        setOrchWebSearch(orchCaps.web_search);
      }
      return;
    }

    if (selectedOrchestrator === "chatgpt") {
      setOrchModel("");
      setOrchThinkingLevel("");
      setOrchMode("");
      if (orchSel?.web_search !== undefined) {
        setOrchWebSearch(orchSel.web_search);
      } else if (orchCaps?.web_search !== undefined) {
        setOrchWebSearch(orchCaps.web_search);
      }
      if (orchSel?.deep_research !== undefined) {
        setOrchDeepResearch(orchSel.deep_research);
      } else if (orchCaps?.deep_research !== undefined) {
        setOrchDeepResearch(orchCaps.deep_research);
      }
      if (orchSel?.deep_thinking !== undefined) {
        setOrchDeepThinking(orchSel.deep_thinking);
      } else if (orchCaps?.deep_thinking !== undefined) {
        setOrchDeepThinking(orchCaps.deep_thinking);
      }
      return;
    }

    if (selectedOrchestrator === "perplexity") {
      setOrchModel("auto");
      setOrchThinkingLevel("");
      setOrchMode("");
      setOrchDeepThinking(false);
      setOrchWebSearch(true);
      return;
    }

    if (selectedOrchestrator === "kimi") {
      setOrchMode("");
      const isDr = orchSel?.deep_research !== undefined ? orchSel.deep_research : (orchCaps?.deep_research ?? false);
      setOrchDeepResearch(isDr);
      const chosenModel = orchSel?.model_id || orchCaps?.selected_model_id || (orchCaps?.available_models && orchCaps.available_models.length > 0 ? orchCaps.available_models[0].id : "instant");
      if (isDr && (chosenModel === "instant" || !chosenModel || chosenModel === "default")) {
        setOrchModel("k3");
      } else {
        setOrchModel(chosenModel || "instant");
      }
      if (orchSel?.thinking_level_id) {
        setOrchThinkingLevel(orchSel.thinking_level_id);
      } else if (orchCaps?.selected_thinking_level_id) {
        setOrchThinkingLevel(orchCaps.selected_thinking_level_id);
      } else if (orchCaps?.thinking_levels && orchCaps.thinking_levels.length > 0) {
        setOrchThinkingLevel(orchCaps.thinking_levels[0].id);
      } else {
        setOrchThinkingLevel("high");
      }
      return;
    }

    if (selectedOrchestrator === "qwen") {
      setOrchMode("");
      const isDr = orchSel?.deep_research !== undefined ? orchSel.deep_research : (orchCaps?.deep_research ?? false);
      setOrchDeepResearch(isDr);
      const chosenModel = orchSel?.model_id || orchCaps?.selected_model_id || (orchCaps?.available_models && orchCaps.available_models.length > 0 ? orchCaps.available_models[0].id : "qwen-3.8-max");
      setOrchModel(chosenModel);
      if (isDr) {
        setOrchThinkingLevel("auto");
      } else if (orchSel?.thinking_level_id) {
        setOrchThinkingLevel(orchSel.thinking_level_id);
      } else if (orchCaps?.selected_thinking_level_id) {
        setOrchThinkingLevel(orchCaps.selected_thinking_level_id);
      } else if (orchCaps?.thinking_levels && orchCaps.thinking_levels.length > 0) {
        setOrchThinkingLevel(orchCaps.thinking_levels[0].id);
      } else {
        setOrchThinkingLevel("auto");
      }
      setOrchWebSearch(orchSel?.web_search !== undefined ? orchSel.web_search : (orchCaps?.web_search ?? true));
      setOrchResearchMode(orchSel?.research_mode || orchCaps?.research_mode || "normal");
      return;
    }

    if (selectedOrchestrator === "gemini") {
      setOrchMode("");
      const isDr = orchSel?.deep_research !== undefined ? orchSel.deep_research : (orchCaps?.deep_research ?? false);
      setOrchDeepResearch(isDr);
      const chosenModel = orchSel?.model_id || orchCaps?.selected_model_id || (orchCaps?.available_models && orchCaps.available_models.length > 0 ? orchCaps.available_models[0].id : "pro");
      setOrchModel(chosenModel);
      if (orchSel?.thinking_level_id) {
        setOrchThinkingLevel(orchSel.thinking_level_id);
      } else if (orchCaps?.selected_thinking_level_id) {
        setOrchThinkingLevel(orchCaps.selected_thinking_level_id);
      } else if (orchCaps?.thinking_levels && orchCaps.thinking_levels.length > 0) {
        setOrchThinkingLevel(orchCaps.thinking_levels[0].id);
      } else {
        setOrchThinkingLevel("medium");
      }
      return;
    }

    if (selectedOrchestrator === "grok") {
      setOrchModel("");
      setOrchThinkingLevel("");
      setOrchMode("");
      setOrchDeepThinking(false);
      setOrchDeepResearch(false);
      return;
    }

    if (selectedOrchestrator === "copilot") {
      setOrchModel("");
      setOrchThinkingLevel("");
      if (orchSel?.mode_id) {
        setOrchMode(orchSel.mode_id);
      } else if (orchCaps?.selected_mode_id) {
        setOrchMode(orchCaps.selected_mode_id);
      } else if (orchCaps?.modes && orchCaps.modes.length > 0) {
        setOrchMode(orchCaps.modes[0].id);
      } else {
        setOrchMode("auto");
      }
      return;
    }

    if (orchSel?.model_id && orchSel.model_id !== "claude-opus-5.5" && orchSel.model_id !== "claude-fable-5.1") {
      setOrchModel(orchSel.model_id);
    } else if (orchCaps?.selected_model_id && orchCaps.selected_model_id !== "claude-opus-5.5" && orchCaps.selected_model_id !== "claude-fable-5.1") {
      setOrchModel(orchCaps.selected_model_id);
    } else if (selectedOrchestrator === "claude") {
      setOrchModel("claude-sonnet-5.5");
    } else if (orchCaps?.available_models && orchCaps.available_models.length > 0) {
      setOrchModel(orchCaps.available_models[0].id);
    } else if (selectedOrchestrator === "gemini") {
      setOrchModel("pro");
    } else if (selectedOrchestrator === "qwen") {
      setOrchModel("qwen-3.8-max");
    }

    if (orchSel?.thinking_level_id) {
      setOrchThinkingLevel(orchSel.thinking_level_id);
    } else if (orchCaps?.selected_thinking_level_id) {
      setOrchThinkingLevel(orchCaps.selected_thinking_level_id);
    } else if (selectedOrchestrator === "claude") {
      setOrchThinkingLevel("medium");
    } else if (orchCaps?.thinking_levels && orchCaps.thinking_levels.length > 0) {
      setOrchThinkingLevel(orchCaps.thinking_levels[0].id);
    }

    if (orchSel?.mode_id) {
      setOrchMode(orchSel.mode_id);
    } else if (orchCaps?.selected_mode_id) {
      setOrchMode(orchCaps.selected_mode_id);
    } else if (orchCaps?.modes && orchCaps.modes.length > 0) {
      setOrchMode(orchCaps.modes[0].id);
    } else {
      setOrchMode("");
    }
  }, [selectedOrchestrator, orchCaps, orchSel]);

  // Sync Lead local state when capabilities or selections update
  useEffect(() => {
    if (selectedLead === "deepseek") {
      setLeadModel("");
      setLeadThinkingLevel("");
      setLeadMode("");
      if (leadSel?.deep_thinking !== undefined) {
        setLeadDeepThinking(leadSel.deep_thinking);
      } else if (leadCaps?.deep_thinking !== undefined) {
        setLeadDeepThinking(leadCaps.deep_thinking);
      }
      if (leadSel?.web_search !== undefined) {
        setLeadWebSearch(leadSel.web_search);
      } else if (leadCaps?.web_search !== undefined) {
        setLeadWebSearch(leadCaps.web_search);
      }
      return;
    }

    if (selectedLead === "chatgpt") {
      setLeadModel("");
      setLeadThinkingLevel("");
      setLeadMode("");
      if (leadSel?.web_search !== undefined) {
        setLeadWebSearch(leadSel.web_search);
      } else if (leadCaps?.web_search !== undefined) {
        setLeadWebSearch(leadCaps.web_search);
      }
      if (leadSel?.deep_research !== undefined) {
        setLeadDeepResearch(leadSel.deep_research);
      } else if (leadCaps?.deep_research !== undefined) {
        setLeadDeepResearch(leadCaps.deep_research);
      }
      if (leadSel?.deep_thinking !== undefined) {
        setLeadDeepThinking(leadSel.deep_thinking);
      } else if (leadCaps?.deep_thinking !== undefined) {
        setLeadDeepThinking(leadCaps.deep_thinking);
      }
      return;
    }

    if (selectedLead === "perplexity") {
      setLeadModel("auto");
      setLeadThinkingLevel("");
      setLeadMode("");
      setLeadDeepThinking(false);
      setLeadWebSearch(true);
      return;
    }

    if (selectedLead === "kimi") {
      setLeadMode("");
      const isDr = leadSel?.deep_research !== undefined ? leadSel.deep_research : (leadCaps?.deep_research ?? false);
      setLeadDeepResearch(isDr);
      const chosenModel = leadSel?.model_id || leadCaps?.selected_model_id || (leadCaps?.available_models && leadCaps.available_models.length > 0 ? leadCaps.available_models[0].id : "instant");
      if (isDr && (chosenModel === "instant" || !chosenModel || chosenModel === "default")) {
        setLeadModel("k3");
      } else {
        setLeadModel(chosenModel || "instant");
      }
      if (leadSel?.thinking_level_id) {
        setLeadThinkingLevel(leadSel.thinking_level_id);
      } else if (leadCaps?.selected_thinking_level_id) {
        setLeadThinkingLevel(leadCaps.selected_thinking_level_id);
      } else if (leadCaps?.thinking_levels && leadCaps.thinking_levels.length > 0) {
        setLeadThinkingLevel(leadCaps.thinking_levels[0].id);
      } else {
        setLeadThinkingLevel("high");
      }
      return;
    }

    if (selectedLead === "qwen") {
      setLeadMode("");
      const isDr = leadSel?.deep_research !== undefined ? leadSel.deep_research : (leadCaps?.deep_research ?? false);
      setLeadDeepResearch(isDr);
      const chosenModel = leadSel?.model_id || leadCaps?.selected_model_id || (leadCaps?.available_models && leadCaps.available_models.length > 0 ? leadCaps.available_models[0].id : "qwen-3.8-max");
      setLeadModel(chosenModel);
      if (isDr) {
        setLeadThinkingLevel("auto");
      } else if (leadSel?.thinking_level_id) {
        setLeadThinkingLevel(leadSel.thinking_level_id);
      } else if (leadCaps?.selected_thinking_level_id) {
        setLeadThinkingLevel(leadCaps.selected_thinking_level_id);
      } else if (leadCaps?.thinking_levels && leadCaps.thinking_levels.length > 0) {
        setLeadThinkingLevel(leadCaps.thinking_levels[0].id);
      } else {
        setLeadThinkingLevel("auto");
      }
      setLeadWebSearch(leadSel?.web_search !== undefined ? leadSel.web_search : (leadCaps?.web_search ?? true));
      setLeadResearchMode(leadSel?.research_mode || leadCaps?.research_mode || "normal");
      return;
    }

    if (selectedLead === "gemini") {
      setLeadMode("");
      const isDr = leadSel?.deep_research !== undefined ? leadSel.deep_research : (leadCaps?.deep_research ?? false);
      setLeadDeepResearch(isDr);
      const chosenModel = leadSel?.model_id || leadCaps?.selected_model_id || (leadCaps?.available_models && leadCaps.available_models.length > 0 ? leadCaps.available_models[0].id : "pro");
      setLeadModel(chosenModel);
      if (leadSel?.thinking_level_id) {
        setLeadThinkingLevel(leadSel.thinking_level_id);
      } else if (leadCaps?.selected_thinking_level_id) {
        setLeadThinkingLevel(leadCaps.selected_thinking_level_id);
      } else if (leadCaps?.thinking_levels && leadCaps.thinking_levels.length > 0) {
        setLeadThinkingLevel(leadCaps.thinking_levels[0].id);
      } else {
        setLeadThinkingLevel("medium");
      }
      return;
    }

    if (selectedLead === "grok") {
      setLeadModel("");
      setLeadThinkingLevel("");
      setLeadMode("");
      setLeadDeepThinking(false);
      setLeadDeepResearch(false);
      return;
    }

    if (selectedLead === "copilot") {
      setLeadModel("");
      setLeadThinkingLevel("");
      if (leadSel?.mode_id) {
        setLeadMode(leadSel.mode_id);
      } else if (leadCaps?.selected_mode_id) {
        setLeadMode(leadCaps.selected_mode_id);
      } else if (leadCaps?.modes && leadCaps.modes.length > 0) {
        setLeadMode(leadCaps.modes[0].id);
      } else {
        setLeadMode("auto");
      }
      return;
    }

    if (leadSel?.model_id && leadSel.model_id !== "claude-opus-5.5" && leadSel.model_id !== "claude-fable-5.1") {
      setLeadModel(leadSel.model_id);
    } else if (leadCaps?.selected_model_id && leadCaps.selected_model_id !== "claude-opus-5.5" && leadCaps.selected_model_id !== "claude-fable-5.1") {
      setLeadModel(leadCaps.selected_model_id);
    } else if (selectedLead === "claude") {
      setLeadModel("claude-sonnet-5.5");
    } else if (leadCaps?.available_models && leadCaps.available_models.length > 0) {
      setLeadModel(leadCaps.available_models[0].id);
    } else if (selectedLead === "gemini") {
      setLeadModel("gemini-3.1-pro");
    } else if (selectedLead === "qwen") {
      setLeadModel("qwen-3.8-max");
    }

    if (leadSel?.thinking_level_id) {
      setLeadThinkingLevel(leadSel.thinking_level_id);
    } else if (leadCaps?.selected_thinking_level_id) {
      setLeadThinkingLevel(leadCaps.selected_thinking_level_id);
    } else if (selectedLead === "claude") {
      setLeadThinkingLevel("medium");
    } else if (leadCaps?.thinking_levels && leadCaps.thinking_levels.length > 0) {
      setLeadThinkingLevel(leadCaps.thinking_levels[0].id);
    }

    if (leadSel?.mode_id) {
      setLeadMode(leadSel.mode_id);
    } else if (leadCaps?.selected_mode_id) {
      setLeadMode(leadCaps.selected_mode_id);
    } else if (leadCaps?.modes && leadCaps.modes.length > 0) {
      setLeadMode(leadCaps.modes[0].id);
    } else {
      setLeadMode("");
    }
  }, [selectedLead, leadCaps, leadSel]);

  type AgentOption = { id: string; label: string; badge?: string; disabled?: boolean };

  // Computed models for Orchestrator
  const orchModels = useMemo<AgentOption[]>(() => {
    if (selectedOrchestrator === "deepseek" || selectedOrchestrator === "copilot" || selectedOrchestrator === "chatgpt" || selectedOrchestrator === "grok") {
      return [];
    }
    if (selectedOrchestrator === "perplexity") {
      const perplexityFallbackModels: AgentOption[] = [
        { id: "auto", label: "Auto (Tự động - Mặc định)", badge: "Auto", disabled: false },
        { id: "gpt-6-1-sol", label: "GPT-6.1 Sol", badge: "Pro", disabled: true },
        { id: "gpt-6-astra", label: "GPT-6 Astra", badge: "Max", disabled: true },
        { id: "gemini-4-argon", label: "Gemini 4 Argon", badge: "New", disabled: true },
        { id: "gemini-3-8-flash", label: "Gemini 3.8 Flash", badge: "Pro", disabled: true },
        { id: "claude-sonnet-5-5", label: "Claude Sonnet 5.5", badge: "Pro", disabled: true },
        { id: "claude-opus-5-5", label: "Claude Opus 5.5", badge: "Max", disabled: true },
        { id: "claude-fable-5-1", label: "Claude Fable 5.1", badge: "Max", disabled: true },
        { id: "kimi-k3", label: "Kimi K3", badge: "Pro", disabled: true },
        { id: "glm-5-3", label: "GLM 5.3", badge: "Pro", disabled: true },
        { id: "grok-4-7", label: "Grok 4.7", badge: "Pro", disabled: true },
        { id: "nemotron-3-ultra", label: "Nemotron 3 Ultra", badge: "Pro", disabled: true },
      ];
      if (orchCaps?.available_models && orchCaps.available_models.length > 0 && !orchCaps.available_models.some((m) => m.id === "default")) {
        return orchCaps.available_models.map((m) => ({
          ...m,
          disabled: m.id !== "auto",
          badge: m.id === "auto" ? "Auto" : (m.badge || "Pro"),
        }));
      }
      return perplexityFallbackModels;
    }
    if (selectedOrchestrator === "claude") {
      const base: AgentOption[] = orchCaps?.available_models && orchCaps.available_models.length > 0
        ? orchCaps.available_models
        : [
          { id: "claude-sonnet-5.5", label: "Claude Sonnet 5.5 (Cân bằng & thông minh)", badge: "Sonnet", disabled: false },
          { id: "claude-haiku-5.5", label: "Claude Haiku 5.5 (Phản hồi nhanh)", badge: "Haiku", disabled: false },
          { id: "claude-opus-5.5", label: "Claude Opus 5.5 (Pro)", badge: "Upgrade", disabled: true },
          { id: "claude-fable-5.1", label: "Claude Fable 5.1 (Max)", badge: "Upgrade", disabled: true },
        ];
      return base.map((m) => {
        const isUpgrade = m.id === "claude-opus-5.5" || m.id === "claude-fable-5.1" || m.disabled || m.badge === "Upgrade";
        return {
          ...m,
          disabled: isUpgrade,
          badge: isUpgrade ? "Upgrade" : m.badge,
        };
      });
    }
    if (orchCaps?.available_models && orchCaps.available_models.length > 0) {
      return orchCaps.available_models;
    }
    if (selectedOrchestrator === "gemini") {
      return [
        { id: "pro", label: "Gemini 3.1 Pro (Deep Reasoning)", badge: "Deep" },
        { id: "flash", label: "Gemini Flash (Nhanh)", badge: "Fast" },
        { id: "argon", label: "Gemini Argon", badge: "Pro" },
      ];
    }
    if (selectedOrchestrator === "qwen") {
      return [
        { id: "qwen-3.8-max", label: "Qwen 3.8 Max (Reasoning)", badge: "Max" },
        { id: "qwen-3.7-plus", label: "Qwen 3.7 Plus", badge: "Plus" },
        { id: "qwen-3.8-omni-flash", label: "Qwen 3.8 Omni-Flash", badge: "Omni" },
      ];
    }
    if (selectedOrchestrator === "zhipu") {
      return [
        { id: "glm-5.3", label: "GLM-5.3", badge: "GLM" },
        { id: "glm-4-plus", label: "GLM-4 Plus", badge: "GLM" },
      ];
    }
    if (selectedOrchestrator === "kimi") {
      const kimiFallbackModels: AgentOption[] = [
        { id: "instant", label: "Instant (Phản hồi nhanh)", badge: "Fast" },
        { id: "k3", label: "K3 (Chat & Agent)", badge: "All-Rounder" },
        { id: "k2.8", label: "K2.8 (Preview · Well-rounded)", badge: "Preview" },
      ];
      const baseModels = orchCaps?.available_models && orchCaps.available_models.length > 0 && !orchCaps.available_models.some((m) => m.id === "default")
        ? orchCaps.available_models
        : kimiFallbackModels;
      return baseModels.map((m) => {
        const isInstantDisabled = orchDeepResearch && m.id === "instant";
        return {
          ...m,
          disabled: isInstantDisabled || m.disabled,
          badge: isInstantDisabled ? "Không hỗ trợ DR" : m.badge,
        };
      });
    }
    return [
      { id: "default", label: orchProviderObj?.modelName || "Mặc định" },
    ];
  }, [orchCaps, selectedOrchestrator, orchProviderObj, orchDeepResearch]);

  // Computed thinking levels for Orchestrator
  const orchThinkingLevels = useMemo<AgentOption[]>(() => {
    if (selectedOrchestrator === "deepseek" || selectedOrchestrator === "copilot" || selectedOrchestrator === "chatgpt" || selectedOrchestrator === "perplexity" || selectedOrchestrator === "grok") {
      return [];
    }
    if (orchCaps?.thinking_levels && orchCaps.thinking_levels.length > 0) {
      return orchCaps.thinking_levels;
    }
    if (selectedOrchestrator === "gemini") {
      return [
        { id: "high", label: "Cao (High Thinking)", badge: "High" },
        { id: "medium", label: "Vừa (Medium)", badge: "Med" },
        { id: "low", label: "Thấp (Low)", badge: "Low" },
      ];
    }
    if (selectedOrchestrator === "qwen") {
      return [
        { id: "auto", label: "Auto (Tự động cân bằng)", badge: "Auto" },
        { id: "thinking", label: "Thinking (Suy luận sâu)", badge: "Think" },
        { id: "fast", label: "Fast (Phản hồi nhanh)", badge: "Fast" },
      ];
    }
    if (selectedOrchestrator === "claude") {
      return [
        { id: "medium", label: "Trung bình (Medium - Khuyên dùng)", badge: "Med" },
        { id: "low", label: "Thấp (Low - Nhanh)", badge: "Low" },
        { id: "high", label: "Cao (High - Kỹ lưỡng)", badge: "High" },
        { id: "extra", label: "Rất cao (Extra)", badge: "Extra" },
        { id: "max", label: "Tối đa (Max)", badge: "Max" },
      ];
    }
    if (selectedOrchestrator === "kimi") {
      const kimiFallbackThinking: AgentOption[] = [
        { id: "standard", label: "Standard (Tiêu chuẩn)", badge: "Standard" },
        { id: "high", label: "High (Chuyên sâu)", badge: "High" },
      ];
      if (orchCaps?.thinking_levels && orchCaps.thinking_levels.length > 0) {
        return orchCaps.thinking_levels;
      }
      return kimiFallbackThinking;
    }
    return [];
  }, [orchCaps, selectedOrchestrator]);

  // Computed modes for Orchestrator
  const orchModes = useMemo<AgentOption[]>(() => {
    if (selectedOrchestrator === "gemini" || selectedOrchestrator === "qwen" || selectedOrchestrator === "claude" || selectedOrchestrator === "deepseek" || selectedOrchestrator === "chatgpt" || selectedOrchestrator === "perplexity" || selectedOrchestrator === "kimi" || selectedOrchestrator === "grok") {
      return [];
    }
    if (orchCaps?.modes && orchCaps.modes.length > 0) {
      return orchCaps.modes;
    }
    if (selectedOrchestrator === "copilot") {
      return [
        { id: "auto", label: "Auto (Cân bằng tốc độ & độ chính xác)", badge: "Auto" },
        { id: "quick", label: "Quick Response (Phản hồi nhanh)", badge: "Fast" },
        { id: "think_deeper", label: "Think Deeper (Suy luận đa bước chuyên sâu)", badge: "Think" },
        { id: "gpt_5_6_quick", label: "GPT > GPT-5.6 Sol Quick Response", badge: "GPT-5.6" },
        { id: "gpt_5_6_think", label: "GPT > GPT-5.6 Sol Think Deeper", badge: "GPT-5.6" },
      ];
    }
    return [];
  }, [orchCaps, selectedOrchestrator]);

  // Computed models for Lead Provider
  const leadModels = useMemo<AgentOption[]>(() => {
    if (selectedLead === "deepseek" || selectedLead === "copilot" || selectedLead === "chatgpt" || selectedLead === "grok") {
      return [];
    }
    if (selectedLead === "perplexity") {
      const perplexityFallbackModels: AgentOption[] = [
        { id: "auto", label: "Auto (Tự động - Mặc định)", badge: "Auto", disabled: false },
        { id: "gpt-6-1-sol", label: "GPT-6.1 Sol", badge: "Pro", disabled: true },
        { id: "gpt-6-astra", label: "GPT-6 Astra", badge: "Max", disabled: true },
        { id: "gemini-4-argon", label: "Gemini 4 Argon", badge: "New", disabled: true },
        { id: "gemini-3-8-flash", label: "Gemini 3.8 Flash", badge: "Pro", disabled: true },
        { id: "claude-sonnet-5-5", label: "Claude Sonnet 5.5", badge: "Pro", disabled: true },
        { id: "claude-opus-5-5", label: "Claude Opus 5.5", badge: "Max", disabled: true },
        { id: "claude-fable-5-1", label: "Claude Fable 5.1", badge: "Max", disabled: true },
        { id: "kimi-k3", label: "Kimi K3", badge: "Pro", disabled: true },
        { id: "glm-5-3", label: "GLM 5.3", badge: "Pro", disabled: true },
        { id: "grok-4-7", label: "Grok 4.7", badge: "Pro", disabled: true },
        { id: "nemotron-3-ultra", label: "Nemotron 3 Ultra", badge: "Pro", disabled: true },
      ];
      if (leadCaps?.available_models && leadCaps.available_models.length > 0 && !leadCaps.available_models.some((m) => m.id === "default")) {
        return leadCaps.available_models.map((m) => ({
          ...m,
          disabled: m.id !== "auto",
          badge: m.id === "auto" ? "Auto" : (m.badge || "Pro"),
        }));
      }
      return perplexityFallbackModels;
    }
    if (selectedLead === "claude") {
      const base: AgentOption[] = leadCaps?.available_models && leadCaps.available_models.length > 0
        ? leadCaps.available_models
        : [
          { id: "claude-sonnet-5.5", label: "Claude Sonnet 5.5 (Cân bằng & thông minh)", badge: "Sonnet", disabled: false },
          { id: "claude-haiku-5.5", label: "Claude Haiku 5.5 (Phản hồi nhanh)", badge: "Haiku", disabled: false },
          { id: "claude-opus-5.5", label: "Claude Opus 5.5 (Pro)", badge: "Upgrade", disabled: true },
          { id: "claude-fable-5.1", label: "Claude Fable 5.1 (Max)", badge: "Upgrade", disabled: true },
        ];
      return base.map((m) => {
        const isUpgrade = m.id === "claude-opus-5.5" || m.id === "claude-fable-5.1" || m.disabled || m.badge === "Upgrade";
        return {
          ...m,
          disabled: isUpgrade,
          badge: isUpgrade ? "Upgrade" : m.badge,
        };
      });
    }
    if (leadCaps?.available_models && leadCaps.available_models.length > 0) {
      return leadCaps.available_models;
    }
    if (selectedLead === "gemini") {
      return [
        { id: "pro", label: "Gemini 3.1 Pro (Deep Reasoning)", badge: "Deep" },
        { id: "flash", label: "Gemini Flash (Nhanh)", badge: "Fast" },
        { id: "argon", label: "Gemini Argon", badge: "Pro" },
      ];
    }
    if (selectedLead === "qwen") {
      return [
        { id: "qwen-3.8-max", label: "Qwen 3.8 Max (Reasoning)", badge: "Max" },
        { id: "qwen-3.7-plus", label: "Qwen 3.7 Plus", badge: "Plus" },
        { id: "qwen-3.8-omni-flash", label: "Qwen 3.8 Omni-Flash", badge: "Omni" },
      ];
    }
    if (selectedLead === "zhipu") {
      return [
        { id: "glm-5.3", label: "GLM-5.3", badge: "GLM" },
        { id: "glm-4-plus", label: "GLM-4 Plus", badge: "GLM" },
      ];
    }
    if (selectedLead === "kimi") {
      const kimiFallbackModels: AgentOption[] = [
        { id: "instant", label: "Instant (Phản hồi nhanh)", badge: "Fast" },
        { id: "k3", label: "K3 (Chat & Agent)", badge: "All-Rounder" },
        { id: "k2.8", label: "K2.8 (Preview · Well-rounded)", badge: "Preview" },
      ];
      const baseModels = leadCaps?.available_models && leadCaps.available_models.length > 0 && !leadCaps.available_models.some((m) => m.id === "default")
        ? leadCaps.available_models
        : kimiFallbackModels;
      return baseModels.map((m) => {
        const isInstantDisabled = leadDeepResearch && m.id === "instant";
        return {
          ...m,
          disabled: isInstantDisabled || m.disabled,
          badge: isInstantDisabled ? "Không hỗ trợ DR" : m.badge,
        };
      });
    }
    return [
      { id: "default", label: leadProviderObj?.modelName || "Mặc định" },
    ];
  }, [leadCaps, selectedLead, leadProviderObj, leadDeepResearch]);

  // Computed thinking levels for Lead Provider
  const leadThinkingLevels = useMemo<AgentOption[]>(() => {
    if (selectedLead === "deepseek" || selectedLead === "copilot" || selectedLead === "chatgpt" || selectedLead === "perplexity" || selectedLead === "grok") {
      return [];
    }
    if (leadCaps?.thinking_levels && leadCaps.thinking_levels.length > 0) {
      return leadCaps.thinking_levels;
    }
    if (selectedLead === "gemini") {
      return [
        { id: "high", label: "Cao (High Thinking)", badge: "High" },
        { id: "medium", label: "Vừa (Medium)", badge: "Med" },
        { id: "low", label: "Thấp (Low)", badge: "Low" },
      ];
    }
    if (selectedLead === "qwen") {
      return [
        { id: "auto", label: "Auto (Tự động cân bằng)", badge: "Auto" },
        { id: "thinking", label: "Thinking (Suy luận sâu)", badge: "Think" },
        { id: "fast", label: "Fast (Phản hồi nhanh)", badge: "Fast" },
      ];
    }
    if (selectedLead === "claude") {
      return [
        { id: "medium", label: "Trung bình (Medium - Khuyên dùng)", badge: "Med" },
        { id: "low", label: "Thấp (Low - Nhanh)", badge: "Low" },
        { id: "high", label: "Cao (High - Kỹ lưỡng)", badge: "High" },
        { id: "extra", label: "Rất cao (Extra)", badge: "Extra" },
        { id: "max", label: "Tối đa (Max)", badge: "Max" },
      ];
    }
    if (selectedLead === "kimi") {
      const kimiFallbackThinking: AgentOption[] = [
        { id: "standard", label: "Standard (Tiêu chuẩn)", badge: "Standard" },
        { id: "high", label: "High (Chuyên sâu)", badge: "High" },
      ];
      if (leadCaps?.thinking_levels && leadCaps.thinking_levels.length > 0) {
        return leadCaps.thinking_levels;
      }
      return kimiFallbackThinking;
    }
    return [];
  }, [leadCaps, selectedLead]);

  // Computed modes for Lead Provider
  const leadModes = useMemo<AgentOption[]>(() => {
    if (selectedLead === "gemini" || selectedLead === "qwen" || selectedLead === "claude" || selectedLead === "deepseek" || selectedLead === "chatgpt" || selectedLead === "perplexity" || selectedLead === "kimi" || selectedLead === "grok") {
      return [];
    }
    if (leadCaps?.modes && leadCaps.modes.length > 0) {
      return leadCaps.modes;
    }
    if (selectedLead === "copilot") {
      return [
        { id: "auto", label: "Auto (Cân bằng tốc độ & độ chính xác)", badge: "Auto" },
        { id: "quick", label: "Quick Response (Phản hồi nhanh)", badge: "Fast" },
        { id: "think_deeper", label: "Think Deeper (Suy luận đa bước chuyên sâu)", badge: "Think" },
        { id: "gpt_5_6_quick", label: "GPT > GPT-5.6 Sol Quick Response", badge: "GPT-5.6" },
        { id: "gpt_5_6_think", label: "GPT > GPT-5.6 Sol Think Deeper", badge: "GPT-5.6" },
      ];
    }
    return [];
  }, [leadCaps, selectedLead]);

  // Sub-providers delegation toggle handlers
  const toggleDelegatedProvider = (providerId: string) => {
    setSelectedDelegatedProviders((prev) =>
      prev.includes(providerId)
        ? prev.filter((id) => id !== providerId)
        : [...prev, providerId]
    );
  };

  const handleSelectAllDelegated = () => {
    setSelectedDelegatedProviders(availableProviders.map((p) => p.id));
  };

  const handleSelectTopThinkingDelegated = () => {
    setSelectedDelegatedProviders(
      availableProviders
        .filter((p) => p.supportsDeepMode || ["deepseek", "qwen", "gemini", "chatgpt", "copilot", "claude", "perplexity", "kimi"].includes(p.id))
        .map((p) => p.id)
    );
  };

  const handleDeselectAllDelegated = () => {
    setSelectedDelegatedProviders([]);
  };

  // Handle DOM Resync for Orchestrator
  const handleSyncOrchestrator = async () => {
    if (isSyncingOrch || !onSyncProvider) return;
    setIsSyncingOrch(true);
    setOrchSyncMessage(null);
    try {
      const res = await onSyncProvider(selectedOrchestrator);
      const modelCount = res?.available_models?.length || 0;
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setOrchSyncMessage(`✓ Đã đồng bộ DOM thành công lúc ${timeStr}${modelCount > 0 ? ` (${modelCount} mô hình)` : ""}`);
      if (res?.selected_model_id) setOrchModel(res.selected_model_id);
      if (res?.selected_thinking_level_id) setOrchThinkingLevel(res.selected_thinking_level_id);
      if (res?.selected_mode_id) setOrchMode(res.selected_mode_id);
      if (res?.deep_thinking !== undefined) setOrchDeepThinking(res.deep_thinking);
      if (res?.web_search !== undefined) setOrchWebSearch(res.web_search);
      if (res?.deep_research !== undefined) setOrchDeepResearch(res.deep_research);
    } catch (err: any) {
      setOrchSyncMessage(`Lỗi đồng bộ DOM: ${err?.message || "Không thể kết nối"}`);
    } finally {
      setIsSyncingOrch(false);
    }
  };

  // Handle DOM Resync for Lead Provider
  const handleSyncLead = async () => {
    if (isSyncingLead || !onSyncProvider) return;
    setIsSyncingLead(true);
    setLeadSyncMessage(null);
    try {
      const res = await onSyncProvider(selectedLead);
      const modelCount = res?.available_models?.length || 0;
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setLeadSyncMessage(`✓ Đã đồng bộ DOM thành công lúc ${timeStr}${modelCount > 0 ? ` (${modelCount} mô hình)` : ""}`);
      if (res?.selected_model_id) setLeadModel(res.selected_model_id);
      if (res?.selected_thinking_level_id) setLeadThinkingLevel(res.selected_thinking_level_id);
      if (res?.selected_mode_id) setLeadMode(res.selected_mode_id);
      if (res?.deep_thinking !== undefined) setLeadDeepThinking(res.deep_thinking);
      if (res?.web_search !== undefined) setLeadWebSearch(res.web_search);
      if (res?.deep_research !== undefined) setLeadDeepResearch(res.deep_research);
    } catch (err: any) {
      setLeadSyncMessage(`Lỗi đồng bộ DOM: ${err?.message || "Không thể kết nối"}`);
    } finally {
      setIsSyncingLead(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || selectedDelegatedProviders.length === 0 || isSubmitting) return;

    setIsSubmitting(true);

    // Build comprehensive orchestrator config matching both string matching and DOM models
    const orchConfig: Record<string, any> = {
      model_id: orchModel,
      model: orchModel,
      thinking_level_id: orchThinkingLevel,
      thinking: orchThinking,
      mode_id: orchMode,
      mode: orchMode,
    };
    if (selectedOrchestrator === "gemini") {
      orchConfig.model = orchModel || "pro";
      orchConfig.mode = "";
      orchConfig.mode_id = "";
      orchConfig.deep_research = orchDeepResearch;
    } else if (selectedOrchestrator === "qwen") {
      orchConfig.model = orchModel || "qwen-3.8-max";
      orchConfig.thinking_level_id = orchDeepResearch ? "auto" : (orchThinkingLevel || "auto");
      orchConfig.thinking = orchDeepResearch ? "auto" : (orchThinkingLevel || "auto");
      orchConfig.deep_research = orchDeepResearch;
      orchConfig.web_search = orchWebSearch;
      orchConfig.research_mode = orchResearchMode;
      orchConfig.mode = "";
      orchConfig.mode_id = "";
    } else if (selectedOrchestrator === "claude") {
      orchConfig.model = orchModel || "claude-sonnet-5.5";
      orchConfig.thinking = orchThinkingLevel || "medium";
      orchConfig.mode = "";
    } else if (selectedOrchestrator === "deepseek") {
      orchConfig.deep_thinking = orchDeepThinking;
      orchConfig.web_search = orchWebSearch;
      orchConfig.model = "";
      orchConfig.model_id = "";
      orchConfig.thinking = "";
      orchConfig.thinking_level_id = "";
      orchConfig.mode = "";
      orchConfig.mode_id = "";
    } else if (selectedOrchestrator === "chatgpt") {
      orchConfig.web_search = orchWebSearch;
      orchConfig.deep_research = orchDeepResearch;
      orchConfig.deep_thinking = orchDeepThinking;
      orchConfig.model = "";
      orchConfig.model_id = "";
      orchConfig.thinking = "";
      orchConfig.thinking_level_id = "";
      orchConfig.mode = "";
      orchConfig.mode_id = "";
    } else if (selectedOrchestrator === "perplexity") {
      orchConfig.model = "auto";
      orchConfig.model_id = "auto";
      orchConfig.thinking = false;
      orchConfig.deep_thinking = false;
      orchConfig.web_search = true;
      orchConfig.mode = "";
      orchConfig.mode_id = "";
    } else if (selectedOrchestrator === "kimi") {
      orchConfig.model = orchModel || (orchDeepResearch ? "k3" : "instant");
      orchConfig.model_id = orchModel || (orchDeepResearch ? "k3" : "instant");
      orchConfig.thinking_level_id = orchThinkingLevel || "high";
      orchConfig.thinking = orchThinkingLevel || "high";
      orchConfig.deep_research = orchDeepResearch;
      orchConfig.mode = "";
      orchConfig.mode_id = "";
    } else if (selectedOrchestrator === "grok") {
      orchConfig.model = "";
      orchConfig.model_id = "";
      orchConfig.thinking = "";
      orchConfig.thinking_level_id = "";
      orchConfig.mode = "";
      orchConfig.mode_id = "";
    } else if (selectedOrchestrator === "zhipu") {
      orchConfig.model = orchModel || "glm-5.3";
      orchConfig.mode = orchMode || "high";
    }

    // Build comprehensive lead config matching both string matching and DOM models
    const leadConfig: Record<string, any> = {
      model_id: leadModel,
      model: leadModel,
      thinking_level_id: leadThinkingLevel,
      thinking: leadThinking,
      mode_id: leadMode,
      mode: leadMode,
    };
    if (selectedLead === "gemini") {
      leadConfig.model = leadModel || "pro";
      leadConfig.mode = "";
      leadConfig.mode_id = "";
      leadConfig.deep_research = leadDeepResearch;
    } else if (selectedLead === "qwen") {
      leadConfig.model = leadModel || "qwen-3.8-max";
      leadConfig.thinking_level_id = leadDeepResearch ? "auto" : (leadThinkingLevel || "auto");
      leadConfig.thinking = leadDeepResearch ? "auto" : (leadThinkingLevel || "auto");
      leadConfig.deep_research = leadDeepResearch;
      leadConfig.web_search = leadWebSearch;
      leadConfig.research_mode = leadResearchMode;
      leadConfig.mode = "";
      leadConfig.mode_id = "";
    } else if (selectedLead === "claude") {
      leadConfig.model = leadModel || "claude-sonnet-5.5";
      leadConfig.thinking = leadThinkingLevel || "medium";
      leadConfig.mode = "";
    } else if (selectedLead === "deepseek") {
      leadConfig.deep_thinking = leadDeepThinking;
      leadConfig.web_search = leadWebSearch;
      leadConfig.model = "";
      leadConfig.model_id = "";
      leadConfig.thinking = "";
      leadConfig.thinking_level_id = "";
      leadConfig.mode = "";
      leadConfig.mode_id = "";
    } else if (selectedLead === "chatgpt") {
      leadConfig.web_search = leadWebSearch;
      leadConfig.deep_research = leadDeepResearch;
      leadConfig.deep_thinking = leadDeepThinking;
      leadConfig.model = "";
      leadConfig.model_id = "";
      leadConfig.thinking = "";
      leadConfig.thinking_level_id = "";
      leadConfig.mode = "";
      leadConfig.mode_id = "";
    } else if (selectedLead === "perplexity") {
      leadConfig.model = "auto";
      leadConfig.model_id = "auto";
      leadConfig.thinking = false;
      leadConfig.deep_thinking = false;
      leadConfig.web_search = true;
      leadConfig.mode = "";
      leadConfig.mode_id = "";
    } else if (selectedLead === "kimi") {
      leadConfig.model = leadModel || (leadDeepResearch ? "k3" : "instant");
      leadConfig.model_id = leadModel || (leadDeepResearch ? "k3" : "instant");
      leadConfig.thinking_level_id = leadThinkingLevel || "high";
      leadConfig.thinking = leadThinkingLevel || "high";
      leadConfig.deep_research = leadDeepResearch;
      leadConfig.mode = "";
      leadConfig.mode_id = "";
    } else if (selectedLead === "grok") {
      leadConfig.model = "";
      leadConfig.model_id = "";
      leadConfig.thinking = "";
      leadConfig.thinking_level_id = "";
      leadConfig.mode = "";
      leadConfig.mode_id = "";
    }

    onStartAgentResearch({
      query: query.trim(),
      orchestrator_provider: selectedOrchestrator,
      orchestrator_config: orchConfig,
      delegated_providers: selectedDelegatedProviders,
      lead_provider: selectedLead,
      lead_config: leadConfig,
      tone: selectedTone,
    });
  };

  return (
    <div className="agent-config-overlay">
      <div className="agent-config-container">
        {/* Header */}
        <div className="agent-config-header">
          <div className="agent-config-title-group">
            <div className="agent-badge-icon">
              <span style={{ fontSize: 22 }}>🤖</span>
            </div>
            <div>
              <h2 className="agent-config-title">Deep Research Orchestrator</h2>
              <p className="agent-config-subtitle">
                Hệ thống điều phối đa tác nhân AI tự động: phân tách bài toán, kích hoạt đa mô hình chuyên biệt và tổng hợp báo cáo độc lập.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="agent-close-btn"
            onClick={onCancel}
            title="Đóng cấu hình"
          >
            <CloseIcon size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="agent-config-form">
          {/* Section 1: Research Topic Input */}
          <div className="agent-section">
            <label className="agent-section-label">
              <span className="agent-section-step">1</span>
              <span>Chủ đề / Đề tài Nghiên cứu (Research Topic)</span>
            </label>
            <textarea
              className="agent-topic-input"
              rows={3}
              placeholder="Nhập câu hỏi hoặc chủ đề phức tạp cần điều phối đa tác nhân... (VD: Ứng dụng của Deep Learning trong đời sống và y học)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
            />
            <div className="agent-suggestions-row">
              <span style={{ fontSize: 11.5, color: "var(--text-muted)", alignSelf: "center", marginRight: 4 }}>
                Gợi ý:
              </span>
              {SUGGESTED_AGENT_TOPICS.map((topic, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="agent-suggestion-pill"
                  onClick={() => setQuery(topic)}
                >
                  {topic.length > 45 ? topic.slice(0, 45) + "..." : topic}
                </button>
              ))}
            </div>
          </div>

          {/* Section 2: Orchestrator Provider */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">2</span>
                <span>Chọn Orchestrator Provider (Phân rã nhiệm vụ & Lập kế hoạch)</span>
              </label>
              <span className="agent-role-pill">Phân tích & Tách nhánh</span>
            </div>
            <p className="agent-section-desc">
              Tác nhân này chịu trách nhiệm phân tích chủ đề, bóc tách thành các nhiệm vụ con và gán cho các chatbot phù hợp nhất kèm cấu hình Thinking.
            </p>

            <div className="agent-providers-grid">
              {availableProviders.map((prov) => {
                const isSelected = selectedOrchestrator === prov.id;
                const isLive = capabilitiesMap[prov.id]?.is_live_dom;
                return (
                  <div
                    key={`orch-${prov.id}`}
                    className={`agent-provider-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedOrchestrator(prov.id)}
                  >
                    <div className="agent-provider-card-header">
                      <div
                        className="agent-provider-avatar"
                        style={{ background: prov.avatarBg }}
                      >
                        <ModelBadgeLogo providerId={prov.id} size={15} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                          <span className="agent-provider-name" title={prov.name}>{prov.name}</span>
                          {isLive && (
                            <span className="agent-card-mini-badge" title="Đã đồng bộ trực tiếp từ DOM">LIVE</span>
                          )}
                        </div>
                        <div className="agent-provider-model" title={prov.modelName}>{prov.modelName}</div>
                      </div>
                      <input
                        type="radio"
                        name="orchestrator"
                        checked={isSelected}
                        onChange={() => setSelectedOrchestrator(prov.id)}
                        className="agent-radio"
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Fine-tune config for selected orchestrator with DOM Resync */}
            <div className="agent-provider-finetune">
              <div className="agent-finetune-header">
                <div className="agent-finetune-title">
                  <BrainIcon size={14} color="var(--brand-blue)" />
                  <span>Cấu hình Orchestrator (<strong>{orchProviderObj?.name || selectedOrchestrator.toUpperCase()}</strong>):</span>
                  {orchCaps?.is_live_dom ? (
                    <span className="agent-dom-badge live" title="Đã đồng bộ trực tiếp từ DOM của trình duyệt">
                      LIVE DOM
                    </span>
                  ) : (
                    <span className="agent-dom-badge cached" title="Cấu hình bộ đệm / mặc định. Bấm 'Đồng bộ DOM' để quét trực tiếp từ trình duyệt">
                      CACHED
                    </span>
                  )}
                  {orchCaps?.synced_at && (
                    <span className="agent-synced-time">
                      (Cập nhật: {formatSyncTime(orchCaps.synced_at)})
                    </span>
                  )}
                </div>

                {onSyncProvider && (
                  <button
                    type="button"
                    className="agent-resync-btn"
                    onClick={handleSyncOrchestrator}
                    disabled={isSyncingOrch || loadingProvider === selectedOrchestrator}
                    title={`Quét lại DOM của ${orchProviderObj?.name || selectedOrchestrator} để lấy cấu hình mới nhất`}
                  >
                    <RefreshIcon
                      size={12}
                      className={isSyncingOrch || loadingProvider === selectedOrchestrator ? "spin" : ""}
                    />
                    <span>
                      {isSyncingOrch || loadingProvider === selectedOrchestrator
                        ? "Đang quét DOM..."
                        : "Đồng bộ DOM"}
                    </span>
                  </button>
                )}
              </div>

              {orchSyncMessage && (
                <div className={`agent-sync-feedback ${orchSyncMessage.startsWith("Lỗi") ? "error" : "success"}`}>
                  {orchSyncMessage}
                </div>
              )}

              <div className="agent-finetune-options">
                {selectedOrchestrator === "deepseek" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%" }}>
                    {/* DeepThink (R1) Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !orchDeepThinking;
                        setOrchDeepThinking(nextVal);
                        onUpdateSelection?.(selectedOrchestrator, { deep_thinking: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${orchDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: orchDeepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: orchDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt mô hình suy luận sâu DeepSeek-R1 (Chain of Thought)"
                    >
                      <BrainIcon size={14} color={orchDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
                      <span>DeepThink (R1)</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: orchDeepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                          color: orchDeepThinking ? "#ffffff" : "#64748b",
                        }}
                      >
                        {orchDeepThinking ? "BẬT" : "TẮT"}
                      </span>
                    </button>

                    {/* Web Search Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !orchWebSearch;
                        setOrchWebSearch(nextVal);
                        onUpdateSelection?.(selectedOrchestrator, { web_search: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${orchWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: orchWebSearch ? "#ecfdf5" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: orchWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt tính năng tìm kiếm Web thời gian thực của DeepSeek"
                    >
                      <SearchIcon size={14} color={orchWebSearch ? "#059669" : "#64748b"} />
                      <span>Tìm kiếm Web</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: orchWebSearch ? "#059669" : "#e2e8f0",
                          color: orchWebSearch ? "#ffffff" : "#64748b",
                        }}
                      >
                        {orchWebSearch ? "BẬT" : "TẮT"}
                      </span>
                    </button>
                  </div>
                ) : selectedOrchestrator === "chatgpt" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%" }}>
                    {/* Web Search Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !orchWebSearch;
                        setOrchWebSearch(nextVal);
                        onUpdateSelection?.(selectedOrchestrator, { web_search: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${orchWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: orchWebSearch ? "#ecfdf5" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: orchWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt tìm kiếm Web thời gian thực của ChatGPT"
                    >
                      <SearchIcon size={14} color={orchWebSearch ? "#059669" : "#64748b"} />
                      <span>Web Search</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: orchWebSearch ? "#059669" : "#e2e8f0",
                          color: orchWebSearch ? "#ffffff" : "#64748b",
                        }}
                      >
                        {orchWebSearch ? "BẬT" : "TẮT"}
                      </span>
                    </button>

                    {/* Deep Research Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !orchDeepResearch;
                        setOrchDeepResearch(nextVal);
                        onUpdateSelection?.(selectedOrchestrator, { deep_research: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${orchDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: orchDeepResearch ? "#f5f3ff" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: orchDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt chế độ Deep Research của ChatGPT"
                    >
                      <SparklesIcon size={14} color={orchDeepResearch ? "#7c3aed" : "#64748b"} />
                      <span>Deep Research</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: orchDeepResearch ? "#7c3aed" : "#e2e8f0",
                          color: orchDeepResearch ? "#ffffff" : "#64748b",
                        }}
                      >
                        {orchDeepResearch ? "BẬT" : "TẮT"}
                      </span>
                    </button>

                    {/* Thinking Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !orchDeepThinking;
                        setOrchDeepThinking(nextVal);
                        onUpdateSelection?.(selectedOrchestrator, { deep_thinking: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${orchDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: orchDeepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: orchDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt chế độ Thinking của ChatGPT"
                    >
                      <BrainIcon size={14} color={orchDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
                      <span>Thinking</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: orchDeepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                          color: orchDeepThinking ? "#ffffff" : "#64748b",
                        }}
                      >
                        {orchDeepThinking ? "BẬT" : "TẮT"}
                      </span>
                    </button>
                  </div>
                ) : (
                  <>
                    {/* 1. Model Selector */}
                    {orchModels.length > 0 && (
                      <label className="agent-option-inline">
                        <span>Mô hình:</span>
                        <select
                          value={orchModel}
                          onChange={(e) => {
                            const targetM = orchModels.find((m) => m.id === e.target.value);
                            if (targetM?.disabled) return;
                            const val = e.target.value;
                            setOrchModel(val);
                            onUpdateSelection?.(selectedOrchestrator, { model_id: val });
                          }}
                          className="agent-select"
                        >
                          {orchModels.map((m) => (
                            <option key={m.id} value={m.id} disabled={m.disabled}>
                              {m.label} {m.disabled ? "— [Upgrade]" : m.badge ? `[${m.badge}]` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}

                    {/* 2. Reasoning Effort or Thinking Toggle */}
                    {orchThinkingLevels.length > 0 ? (
                      <label className="agent-option-inline">
                        <span>Reasoning Effort:</span>
                        <select
                          disabled={selectedOrchestrator === "qwen" && orchDeepResearch}
                          value={selectedOrchestrator === "qwen" && orchDeepResearch ? "auto" : orchThinkingLevel}
                          onChange={(e) => {
                            if (selectedOrchestrator === "qwen" && orchDeepResearch) return;
                            const val = e.target.value;
                            setOrchThinkingLevel(val);
                            onUpdateSelection?.(selectedOrchestrator, { thinking_level_id: val });
                          }}
                          className="agent-select"
                          style={selectedOrchestrator === "qwen" && orchDeepResearch ? { opacity: 0.7, cursor: "not-allowed" } : undefined}
                        >
                          {selectedOrchestrator === "qwen" && orchDeepResearch ? (
                            <option value="auto">Auto</option>
                          ) : (
                            orchThinkingLevels.map((lvl) => (
                              <option key={lvl.id} value={lvl.id}>
                                {lvl.label} {lvl.badge ? `[${lvl.badge}]` : ""}
                              </option>
                            ))
                          )}
                        </select>
                      </label>
                    ) : selectedOrchestrator === "copilot" || selectedOrchestrator === "chatgpt" || selectedOrchestrator === "grok" ? (
                      selectedOrchestrator === "grok" ? (
                        <span style={{ fontSize: 12, color: "var(--text-muted, #64748b)", fontStyle: "italic" }}>
                          Tài khoản miễn phí — sử dụng cấu hình mặc định từ xAI Grok.
                        </span>
                      ) : null
                    ) : selectedOrchestrator === "perplexity" ? (
                      <button
                        type="button"
                        disabled
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: "1.5px solid var(--border-default, #cbd5e1)",
                          backgroundColor: "#f8fafc",
                          fontSize: 12,
                          fontWeight: 600,
                          color: "var(--text-muted, #94a3b8)",
                          cursor: "not-allowed",
                          opacity: 0.7,
                        }}
                        title="Tính năng Thinking bị khóa trên tài khoản Perplexity miễn phí"
                      >
                        <BrainIcon size={14} color="#94a3b8" />
                        <span>Thinking</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: "#e2e8f0",
                            color: "#94a3b8",
                          }}
                        >
                          TẮT (KHÓA)
                        </span>
                      </button>
                    ) : (
                      <label className="agent-checkbox-inline">
                        <input
                          type="checkbox"
                          checked={orchThinking}
                          onChange={(e) => setOrchThinking(e.target.checked)}
                        />
                        <span>Kích hoạt Thinking / Deep Reasoning Mode</span>
                      </label>
                    )}

                    {/* Kimi Deep Research Toggle */}
                    {selectedOrchestrator === "kimi" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !orchDeepResearch;
                          setOrchDeepResearch(nextVal);
                          if (nextVal && (orchModel === "instant" || !orchModel || orchModel === "default")) {
                            setOrchModel("k3");
                            onUpdateSelection?.(selectedOrchestrator, { deep_research: nextVal, model_id: "k3" });
                          } else {
                            onUpdateSelection?.(selectedOrchestrator, { deep_research: nextVal });
                          }
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${orchDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: orchDeepResearch ? "#f5f3ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: orchDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt chế độ Deep Research của Moonshot Kimi"
                      >
                        <SparklesIcon size={14} color={orchDeepResearch ? "#7c3aed" : "#64748b"} />
                        <span>Deep Research</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: orchDeepResearch ? "#7c3aed" : "#e2e8f0",
                            color: orchDeepResearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {orchDeepResearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Qwen Web Search Toggle */}
                    {selectedOrchestrator === "qwen" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !orchWebSearch;
                          setOrchWebSearch(nextVal);
                          onUpdateSelection?.(selectedOrchestrator, { web_search: nextVal });
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${orchWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: orchWebSearch ? "#ecfdf5" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: orchWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt tính năng tìm kiếm Web trên Qwen (+ Web search)"
                      >
                        <SearchIcon size={14} color={orchWebSearch ? "#059669" : "#64748b"} />
                        <span>Web Search</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: orchWebSearch ? "#059669" : "#e2e8f0",
                            color: orchWebSearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {orchWebSearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Qwen Deep Research Toggle */}
                    {selectedOrchestrator === "qwen" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !orchDeepResearch;
                          setOrchDeepResearch(nextVal);
                          const updates: Partial<ProviderSelectionConfig> = { deep_research: nextVal };
                          if (nextVal) {
                            setOrchThinkingLevel("auto");
                            updates.thinking_level_id = "auto";
                          }
                          onUpdateSelection?.(selectedOrchestrator, updates);
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${orchDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: orchDeepResearch ? "#f5f3ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: orchDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt chế độ Deep Research của Qwen (+ Deep Research)"
                      >
                        <SparklesIcon size={14} color={orchDeepResearch ? "#7c3aed" : "#64748b"} />
                        <span>Deep Research</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: orchDeepResearch ? "#7c3aed" : "#e2e8f0",
                            color: orchDeepResearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {orchDeepResearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Qwen Research Mode Toggle (when Deep Research is ON) */}
                    {selectedOrchestrator === "qwen" && orchDeepResearch && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextMode = orchResearchMode === "advanced" ? "normal" : "advanced";
                          setOrchResearchMode(nextMode);
                          onUpdateSelection?.(selectedOrchestrator, { research_mode: nextMode });
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${orchResearchMode === "advanced" ? "#9333ea" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: orchResearchMode === "advanced" ? "#f3e8ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: orchResearchMode === "advanced" ? "#9333ea" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title={orchResearchMode === "advanced"
                          ? "Advanced - Devoting extra time to a deeper analysis"
                          : "Normal - Fast, reliable responses for quick tasks"}
                      >
                        <SparklesIcon size={14} color={orchResearchMode === "advanced" ? "#9333ea" : "#64748b"} />
                        <span>{orchResearchMode === "advanced" ? "Advanced" : "Normal"}</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: orchResearchMode === "advanced" ? "#9333ea" : "#e2e8f0",
                            color: orchResearchMode === "advanced" ? "#ffffff" : "#64748b",
                          }}
                        >
                          {orchResearchMode === "advanced" ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Gemini Deep Research Toggle */}
                    {selectedOrchestrator === "gemini" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !orchDeepResearch;
                          setOrchDeepResearch(nextVal);
                          onUpdateSelection?.(selectedOrchestrator, { deep_research: nextVal });
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${orchDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: orchDeepResearch ? "#f5f3ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: orchDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt tính năng Deep Research của Gemini (+ menu)"
                      >
                        <SparklesIcon size={14} color={orchDeepResearch ? "#7c3aed" : "#64748b"} />
                        <span>Deep Research</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: orchDeepResearch ? "#7c3aed" : "#e2e8f0",
                            color: orchDeepResearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {orchDeepResearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* 3. Mode Selector */}
                    {orchModes.length > 0 && (
                      <label className="agent-option-inline">
                        <span>Chế độ (Mode):</span>
                        <select
                          value={orchMode}
                          onChange={(e) => {
                            setOrchMode(e.target.value);
                            onUpdateSelection?.(selectedOrchestrator, { mode_id: e.target.value });
                          }}
                          className="agent-select"
                        >
                          {orchModes.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.label} {m.badge ? `[${m.badge}]` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Section 3: Sub Providers Delegation */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">3</span>
                <span>Chọn Sub-Providers được phép giao việc (Delegated Sub-Providers)</span>
              </label>
              <span className="agent-role-pill sub">Ủy quyền & Phân bổ nhánh</span>
            </div>
            <p className="agent-section-desc">
              Chỉ các AI provider được tích chọn dưới đây mới được phép điều phối thực thi các nhánh nghiên cứu con. Orchestrator sẽ lập kế hoạch và phân rã bài toán dựa trên danh sách này.
            </p>

            {/* Quick Actions Toolbar */}
            <div className="agent-subproviders-toolbar">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>
                  Trạng thái chọn:
                </span>
                <span
                  className={`agent-counter-badge ${selectedDelegatedProviders.length === 0 ? "empty" : ""}`}
                >
                  {selectedDelegatedProviders.length} / {availableProviders.length} providers
                </span>
              </div>
              <div className="agent-subproviders-actions">
                <button
                  type="button"
                  className="agent-mini-action-btn primary"
                  onClick={handleSelectTopThinkingDelegated}
                  title="Chọn các mô hình suy luận chuyên sâu hàng đầu"
                >
                  ⚡ Top Reasoning
                </button>
                <button
                  type="button"
                  className="agent-mini-action-btn"
                  onClick={handleSelectAllDelegated}
                  title="Chọn tất cả 14 providers"
                >
                  Chọn tất cả
                </button>
                <button
                  type="button"
                  className="agent-mini-action-btn"
                  onClick={handleDeselectAllDelegated}
                  title="Bỏ chọn tất cả"
                >
                  Bỏ chọn tất cả
                </button>
              </div>
            </div>

            {selectedDelegatedProviders.length === 0 && (
              <div className="agent-delegated-warning">
                ⚠️ Vui lòng chọn ít nhất 1 sub-provider để Orchestrator có thể giao việc.
              </div>
            )}

            <div className="agent-providers-grid">
              {availableProviders.map((prov) => {
                const isSelected = selectedDelegatedProviders.includes(prov.id);
                const isLive = capabilitiesMap[prov.id]?.is_live_dom;
                return (
                  <div
                    key={`delegated-${prov.id}`}
                    className={`agent-provider-card ${isSelected ? "selected delegated-selected" : ""}`}
                    onClick={() => toggleDelegatedProvider(prov.id)}
                  >
                    <div className="agent-provider-card-header">
                      {/* Checkbox indicator */}
                      <div className={`agent-checkbox-card-indicator ${isSelected ? "checked" : ""}`}>
                        {isSelected ? "✓" : ""}
                      </div>

                      <div
                        className="agent-provider-avatar"
                        style={{ background: prov.avatarBg }}
                      >
                        <ModelBadgeLogo providerId={prov.id} size={15} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                          <span className="agent-provider-name" title={prov.name}>{prov.name}</span>
                          {isLive && (
                            <span className="agent-card-mini-badge" title="Đã đồng bộ trực tiếp từ DOM">LIVE</span>
                          )}
                        </div>
                        <div className="agent-provider-model" title={prov.modelName}>{prov.modelName}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 4: Lead Provider */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">4</span>
                <span>Chọn Lead Provider (Tổng hợp & Viết báo cáo cuối)</span>
              </label>
              <span className="agent-role-pill lead">Tổng hợp & Đúc kết</span>
            </div>
            <p className="agent-section-desc">
              Tác nhân chủ trì tiếp nhận toàn bộ kết quả từ các chatbot vệ tinh, kiểm chứng chéo và đúc kết thành báo cáo chuyên sâu hoàn chỉnh.
            </p>

            <div className="agent-providers-grid">
              {availableProviders.map((prov) => {
                const isSelected = selectedLead === prov.id;
                const isLive = capabilitiesMap[prov.id]?.is_live_dom;
                return (
                  <div
                    key={`lead-${prov.id}`}
                    className={`agent-provider-card ${isSelected ? "selected lead-selected" : ""}`}
                    onClick={() => setSelectedLead(prov.id)}
                  >
                    <div className="agent-provider-card-header">
                      <div
                        className="agent-provider-avatar"
                        style={{ background: prov.avatarBg }}
                      >
                        <ModelBadgeLogo providerId={prov.id} size={15} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                          <span className="agent-provider-name" title={prov.name}>{prov.name}</span>
                          {isLive && (
                            <span className="agent-card-mini-badge" title="Đã đồng bộ trực tiếp từ DOM">LIVE</span>
                          )}
                        </div>
                        <div className="agent-provider-model" title={prov.modelName}>{prov.modelName}</div>
                      </div>
                      <input
                        type="radio"
                        name="lead_provider"
                        checked={isSelected}
                        onChange={() => setSelectedLead(prov.id)}
                        className="agent-radio"
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Fine-tune config for selected lead with DOM Resync */}
            <div className="agent-provider-finetune">
              <div className="agent-finetune-header">
                <div className="agent-finetune-title">
                  <BrainIcon size={14} color="#10a37f" />
                  <span>Cấu hình Lead Provider (<strong>{leadProviderObj?.name || selectedLead.toUpperCase()}</strong>):</span>
                  {leadCaps?.is_live_dom ? (
                    <span className="agent-dom-badge live" title="Đã đồng bộ trực tiếp từ DOM của trình duyệt">
                      LIVE DOM
                    </span>
                  ) : (
                    <span className="agent-dom-badge cached" title="Cấu hình bộ đệm / mặc định. Bấm 'Đồng bộ DOM' để quét trực tiếp từ trình duyệt">
                      CACHED
                    </span>
                  )}
                  {leadCaps?.synced_at && (
                    <span className="agent-synced-time">
                      (Cập nhật: {formatSyncTime(leadCaps.synced_at)})
                    </span>
                  )}
                </div>

                {onSyncProvider && (
                  <button
                    type="button"
                    className="agent-resync-btn"
                    onClick={handleSyncLead}
                    disabled={isSyncingLead || loadingProvider === selectedLead}
                    title={`Quét lại DOM của ${leadProviderObj?.name || selectedLead} để lấy cấu hình mới nhất`}
                  >
                    <RefreshIcon
                      size={12}
                      className={isSyncingLead || loadingProvider === selectedLead ? "spin" : ""}
                    />
                    <span>
                      {isSyncingLead || loadingProvider === selectedLead
                        ? "Đang quét DOM..."
                        : "Đồng bộ DOM"}
                    </span>
                  </button>
                )}
              </div>

              {leadSyncMessage && (
                <div className={`agent-sync-feedback ${leadSyncMessage.startsWith("Lỗi") ? "error" : "success"}`}>
                  {leadSyncMessage}
                </div>
              )}

              <div className="agent-finetune-options">
                {selectedLead === "deepseek" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%" }}>
                    {/* DeepThink (R1) Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !leadDeepThinking;
                        setLeadDeepThinking(nextVal);
                        onUpdateSelection?.(selectedLead, { deep_thinking: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${leadDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: leadDeepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: leadDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt mô hình suy luận sâu DeepSeek-R1 (Chain of Thought)"
                    >
                      <BrainIcon size={14} color={leadDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
                      <span>DeepThink (R1)</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: leadDeepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                          color: leadDeepThinking ? "#ffffff" : "#64748b",
                        }}
                      >
                        {leadDeepThinking ? "BẬT" : "TẮT"}
                      </span>
                    </button>

                    {/* Web Search Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !leadWebSearch;
                        setLeadWebSearch(nextVal);
                        onUpdateSelection?.(selectedLead, { web_search: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${leadWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: leadWebSearch ? "#ecfdf5" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: leadWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt tính năng tìm kiếm Web thời gian thực của DeepSeek"
                    >
                      <SearchIcon size={14} color={leadWebSearch ? "#059669" : "#64748b"} />
                      <span>Tìm kiếm Web</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: leadWebSearch ? "#059669" : "#e2e8f0",
                          color: leadWebSearch ? "#ffffff" : "#64748b",
                        }}
                      >
                        {leadWebSearch ? "BẬT" : "TẮT"}
                      </span>
                    </button>
                  </div>
                ) : selectedLead === "chatgpt" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%" }}>
                    {/* Web Search Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !leadWebSearch;
                        setLeadWebSearch(nextVal);
                        onUpdateSelection?.(selectedLead, { web_search: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${leadWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: leadWebSearch ? "#ecfdf5" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: leadWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt tìm kiếm Web thời gian thực của ChatGPT"
                    >
                      <SearchIcon size={14} color={leadWebSearch ? "#059669" : "#64748b"} />
                      <span>Web Search</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: leadWebSearch ? "#059669" : "#e2e8f0",
                          color: leadWebSearch ? "#ffffff" : "#64748b",
                        }}
                      >
                        {leadWebSearch ? "BẬT" : "TẮT"}
                      </span>
                    </button>

                    {/* Deep Research Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !leadDeepResearch;
                        setLeadDeepResearch(nextVal);
                        onUpdateSelection?.(selectedLead, { deep_research: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${leadDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: leadDeepResearch ? "#f5f3ff" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: leadDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt chế độ Deep Research của ChatGPT"
                    >
                      <SparklesIcon size={14} color={leadDeepResearch ? "#7c3aed" : "#64748b"} />
                      <span>Deep Research</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: leadDeepResearch ? "#7c3aed" : "#e2e8f0",
                          color: leadDeepResearch ? "#ffffff" : "#64748b",
                        }}
                      >
                        {leadDeepResearch ? "BẬT" : "TẮT"}
                      </span>
                    </button>

                    {/* Thinking Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        const nextVal = !leadDeepThinking;
                        setLeadDeepThinking(nextVal);
                        onUpdateSelection?.(selectedLead, { deep_thinking: nextVal });
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        borderRadius: "var(--radius-sm, 6px)",
                        border: `1.5px solid ${leadDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                        backgroundColor: leadDeepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                        fontSize: 12,
                        fontWeight: 600,
                        color: leadDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Bật/Tắt chế độ Thinking của ChatGPT"
                    >
                      <BrainIcon size={14} color={leadDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
                      <span>Thinking</span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "1px 6px",
                          borderRadius: 10,
                          backgroundColor: leadDeepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                          color: leadDeepThinking ? "#ffffff" : "#64748b",
                        }}
                      >
                        {leadDeepThinking ? "BẬT" : "TẮT"}
                      </span>
                    </button>
                  </div>
                ) : (
                  <>
                    {/* 1. Model Selector */}
                    {leadModels.length > 0 && (
                      <label className="agent-option-inline">
                        <span>Mô hình:</span>
                        <select
                          value={leadModel}
                          onChange={(e) => {
                            const targetM = leadModels.find((m) => m.id === e.target.value);
                            if (targetM?.disabled) return;
                            const val = e.target.value;
                            setLeadModel(val);
                            onUpdateSelection?.(selectedLead, { model_id: val });
                          }}
                          className="agent-select"
                        >
                          {leadModels.map((m) => (
                            <option key={m.id} value={m.id} disabled={m.disabled}>
                              {m.label} {m.disabled ? "— [Upgrade]" : m.badge ? `[${m.badge}]` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}

                    {/* 2. Reasoning Effort or Thinking Toggle */}
                    {leadThinkingLevels.length > 0 ? (
                      <label className="agent-option-inline">
                        <span>Reasoning Effort:</span>
                        <select
                          disabled={selectedLead === "qwen" && leadDeepResearch}
                          value={selectedLead === "qwen" && leadDeepResearch ? "auto" : leadThinkingLevel}
                          onChange={(e) => {
                            if (selectedLead === "qwen" && leadDeepResearch) return;
                            const val = e.target.value;
                            setLeadThinkingLevel(val);
                            onUpdateSelection?.(selectedLead, { thinking_level_id: val });
                          }}
                          className="agent-select"
                          style={selectedLead === "qwen" && leadDeepResearch ? { opacity: 0.7, cursor: "not-allowed" } : undefined}
                        >
                          {selectedLead === "qwen" && leadDeepResearch ? (
                            <option value="auto">Auto</option>
                          ) : (
                            leadThinkingLevels.map((lvl) => (
                              <option key={lvl.id} value={lvl.id}>
                                {lvl.label} {lvl.badge ? `[${lvl.badge}]` : ""}
                              </option>
                            ))
                          )}
                        </select>
                      </label>
                    ) : selectedLead === "copilot" || selectedLead === "chatgpt" || selectedLead === "grok" ? (
                      selectedLead === "grok" ? (
                        <span style={{ fontSize: 12, color: "var(--text-muted, #64748b)", fontStyle: "italic" }}>
                          Tài khoản miễn phí — sử dụng cấu hình mặc định từ xAI Grok.
                        </span>
                      ) : null
                    ) : selectedLead === "perplexity" ? (
                      <button
                        type="button"
                        disabled
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: "1.5px solid var(--border-default, #cbd5e1)",
                          backgroundColor: "#f8fafc",
                          fontSize: 12,
                          fontWeight: 600,
                          color: "var(--text-muted, #94a3b8)",
                          cursor: "not-allowed",
                          opacity: 0.7,
                        }}
                        title="Tính năng Thinking bị khóa trên tài khoản Perplexity miễn phí"
                      >
                        <BrainIcon size={14} color="#94a3b8" />
                        <span>Thinking</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: "#e2e8f0",
                            color: "#94a3b8",
                          }}
                        >
                          TẮT (KHÓA)
                        </span>
                      </button>
                    ) : (
                      <label className="agent-checkbox-inline">
                        <input
                          type="checkbox"
                          checked={leadThinking}
                          onChange={(e) => setLeadThinking(e.target.checked)}
                        />
                        <span>Kích hoạt Suy luận sâu (Thinking / Deep Research) cho Lead Provider</span>
                      </label>
                    )}

                    {/* Kimi Deep Research Toggle */}
                    {selectedLead === "kimi" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !leadDeepResearch;
                          setLeadDeepResearch(nextVal);
                          if (nextVal && (leadModel === "instant" || !leadModel || leadModel === "default")) {
                            setLeadModel("k3");
                            onUpdateSelection?.(selectedLead, { deep_research: nextVal, model_id: "k3" });
                          } else {
                            onUpdateSelection?.(selectedLead, { deep_research: nextVal });
                          }
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${leadDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: leadDeepResearch ? "#f5f3ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: leadDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt chế độ Deep Research của Moonshot Kimi"
                      >
                        <SparklesIcon size={14} color={leadDeepResearch ? "#7c3aed" : "#64748b"} />
                        <span>Deep Research</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: leadDeepResearch ? "#7c3aed" : "#e2e8f0",
                            color: leadDeepResearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {leadDeepResearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Qwen Web Search Toggle */}
                    {selectedLead === "qwen" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !leadWebSearch;
                          setLeadWebSearch(nextVal);
                          onUpdateSelection?.(selectedLead, { web_search: nextVal });
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${leadWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: leadWebSearch ? "#ecfdf5" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: leadWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt tính năng tìm kiếm Web trên Qwen (+ Web search)"
                      >
                        <SearchIcon size={14} color={leadWebSearch ? "#059669" : "#64748b"} />
                        <span>Web Search</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: leadWebSearch ? "#059669" : "#e2e8f0",
                            color: leadWebSearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {leadWebSearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Qwen Deep Research Toggle */}
                    {selectedLead === "qwen" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !leadDeepResearch;
                          setLeadDeepResearch(nextVal);
                          const updates: Partial<ProviderSelectionConfig> = { deep_research: nextVal };
                          if (nextVal) {
                            setLeadThinkingLevel("auto");
                            updates.thinking_level_id = "auto";
                          }
                          onUpdateSelection?.(selectedLead, updates);
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${leadDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: leadDeepResearch ? "#f5f3ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: leadDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt chế độ Deep Research của Qwen (+ Deep Research)"
                      >
                        <SparklesIcon size={14} color={leadDeepResearch ? "#7c3aed" : "#64748b"} />
                        <span>Deep Research</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: leadDeepResearch ? "#7c3aed" : "#e2e8f0",
                            color: leadDeepResearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {leadDeepResearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Qwen Research Mode Toggle (when Deep Research is ON) */}
                    {selectedLead === "qwen" && leadDeepResearch && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextMode = leadResearchMode === "advanced" ? "normal" : "advanced";
                          setLeadResearchMode(nextMode);
                          onUpdateSelection?.(selectedLead, { research_mode: nextMode });
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${leadResearchMode === "advanced" ? "#9333ea" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: leadResearchMode === "advanced" ? "#f3e8ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: leadResearchMode === "advanced" ? "#9333ea" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title={leadResearchMode === "advanced"
                          ? "Advanced - Devoting extra time to a deeper analysis"
                          : "Normal - Fast, reliable responses for quick tasks"}
                      >
                        <SparklesIcon size={14} color={leadResearchMode === "advanced" ? "#9333ea" : "#64748b"} />
                        <span>{leadResearchMode === "advanced" ? "Advanced" : "Normal"}</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: leadResearchMode === "advanced" ? "#9333ea" : "#e2e8f0",
                            color: leadResearchMode === "advanced" ? "#ffffff" : "#64748b",
                          }}
                        >
                          {leadResearchMode === "advanced" ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* Gemini Deep Research Toggle */}
                    {selectedLead === "gemini" && (
                      <button
                        type="button"
                        onClick={() => {
                          const nextVal = !leadDeepResearch;
                          setLeadDeepResearch(nextVal);
                          onUpdateSelection?.(selectedLead, { deep_research: nextVal });
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 12px",
                          borderRadius: "var(--radius-sm, 6px)",
                          border: `1.5px solid ${leadDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                          backgroundColor: leadDeepResearch ? "#f5f3ff" : "#ffffff",
                          fontSize: 12,
                          fontWeight: 600,
                          color: leadDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        title="Bật/Tắt tính năng Deep Research của Gemini (+ menu)"
                      >
                        <SparklesIcon size={14} color={leadDeepResearch ? "#7c3aed" : "#64748b"} />
                        <span>Deep Research</span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 10,
                            backgroundColor: leadDeepResearch ? "#7c3aed" : "#e2e8f0",
                            color: leadDeepResearch ? "#ffffff" : "#64748b",
                          }}
                        >
                          {leadDeepResearch ? "BẬT" : "TẮT"}
                        </span>
                      </button>
                    )}

                    {/* 3. Mode Selector */}
                    {leadModes.length > 0 && (
                      <label className="agent-option-inline">
                        <span>Chế độ (Mode):</span>
                        <select
                          value={leadMode}
                          onChange={(e) => {
                            setLeadMode(e.target.value);
                            onUpdateSelection?.(selectedLead, { mode_id: e.target.value });
                          }}
                          className="agent-select"
                        >
                          {leadModes.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.label} {m.badge ? `[${m.badge}]` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Section 5: Report Tone Selection */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">5</span>
                <span>Chọn Văn phong Báo cáo (Lead Provider Tone)</span>
              </label>
              <span className="agent-role-pill tone">Định hình văn phong</span>
            </div>
            <p className="agent-section-desc">
              Văn phong sẽ được chuyển thành chỉ thị hệ thống chuyên sâu cho Lead Provider để điều chỉnh cách cấu trúc, lập luận và diễn đạt.
            </p>

            <div className="agent-tones-grid">
              {TONE_PRESETS.map((tone) => {
                const isSelected = selectedTone === tone.id;
                return (
                  <div
                    key={tone.id}
                    className={`agent-tone-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedTone(tone.id)}
                  >
                    <div className="agent-tone-header">
                      <span className="agent-tone-icon">{tone.icon}</span>
                      <span className="agent-tone-badge">{tone.badge}</span>
                    </div>
                    <div className="agent-tone-name">{tone.label}</div>
                    <div className="agent-tone-desc">{tone.description}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer Submit */}
          <div className="agent-config-footer">
            <button
              type="button"
              className="agent-btn-secondary"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Hủy
            </button>
            <button
              type="submit"
              className="agent-btn-primary"
              disabled={!query.trim() || selectedDelegatedProviders.length === 0 || isSubmitting}
            >
              <span style={{ fontSize: 16 }}>🚀</span>
              <span>
                {isSubmitting ? "Đang khởi tạo Agent..." : "Khởi chạy Deep Research Orchestrator"}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
