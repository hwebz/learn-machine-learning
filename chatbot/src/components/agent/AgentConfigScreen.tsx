"use client";

import React, { useState, useEffect, useMemo } from "react";
import { PROVIDERS_LIST, TONE_PRESETS } from "../../lib/constants";
import { ProviderInfo } from "../../types/chat";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";
import { BrainIcon, CloseIcon, ModelBadgeLogo, RefreshIcon, SearchIcon } from "../icons/Icons";

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

    if (orchSel?.model_id) {
      setOrchModel(orchSel.model_id);
    } else if (orchCaps?.selected_model_id) {
      setOrchModel(orchCaps.selected_model_id);
    } else if (orchCaps?.available_models && orchCaps.available_models.length > 0) {
      setOrchModel(orchCaps.available_models[0].id);
    } else if (selectedOrchestrator === "gemini") {
      setOrchModel("pro");
    } else if (selectedOrchestrator === "qwen") {
      setOrchModel("qwen-3.8-max");
    } else if (selectedOrchestrator === "claude") {
      setOrchModel("claude-sonnet-5.5");
    }

    if (orchSel?.thinking_level_id) {
      setOrchThinkingLevel(orchSel.thinking_level_id);
    } else if (orchCaps?.selected_thinking_level_id) {
      setOrchThinkingLevel(orchCaps.selected_thinking_level_id);
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

    if (leadSel?.model_id) {
      setLeadModel(leadSel.model_id);
    } else if (leadCaps?.selected_model_id) {
      setLeadModel(leadCaps.selected_model_id);
    } else if (leadCaps?.available_models && leadCaps.available_models.length > 0) {
      setLeadModel(leadCaps.available_models[0].id);
    } else if (selectedLead === "gemini") {
      setLeadModel("gemini-3.1-pro");
    } else if (selectedLead === "qwen") {
      setLeadModel("qwen-3.8-max");
    } else if (selectedLead === "claude") {
      setLeadModel("claude-sonnet-5.5");
    }

    if (leadSel?.thinking_level_id) {
      setLeadThinkingLevel(leadSel.thinking_level_id);
    } else if (leadCaps?.selected_thinking_level_id) {
      setLeadThinkingLevel(leadCaps.selected_thinking_level_id);
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

  type AgentOption = { id: string; label: string; badge?: string };

  // Computed models for Orchestrator
  const orchModels = useMemo<AgentOption[]>(() => {
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
    if (selectedOrchestrator === "copilot") {
      return [
        { id: "auto", label: "Copilot Auto", badge: "Auto" },
        { id: "gpt_5_6_think", label: "GPT > GPT-5.6 Sol Think Deeper", badge: "Think" },
        { id: "gpt_5_6_quick", label: "GPT > GPT-5.6 Sol Quick", badge: "Fast" },
      ];
    }
    if (selectedOrchestrator === "chatgpt") {
      return [
        { id: "o3-mini", label: "o3-mini (Reasoning)", badge: "Think" },
        { id: "gpt-4o", label: "GPT-4o (Omni)", badge: "Auto" },
      ];
    }
    if (selectedOrchestrator === "qwen") {
      return [
        { id: "qwen-3.8-max", label: "Qwen 3.8 Max (Reasoning)", badge: "Max" },
        { id: "qwen-3.7-plus", label: "Qwen 3.7 Plus", badge: "Plus" },
        { id: "qwen-3.8-omni-flash", label: "Qwen 3.8 Omni-Flash", badge: "Omni" },
      ];
    }
    if (selectedOrchestrator === "deepseek") {
      return [];
    }
    if (selectedOrchestrator === "claude") {
      return [
        { id: "claude-sonnet-5.5", label: "Claude Sonnet 5.5 (Cân bằng & thông minh)", badge: "Sonnet" },
        { id: "claude-haiku-5.5", label: "Claude Haiku 5.5 (Phản hồi nhanh)", badge: "Haiku" },
        { id: "claude-opus-5.5", label: "Claude Opus 5.5 (Pro)", badge: "Opus" },
        { id: "claude-fable-5.1", label: "Claude Fable 5.1 (Max)", badge: "Fable" },
      ];
    }
    if (selectedOrchestrator === "zhipu") {
      return [
        { id: "glm-5.3", label: "GLM-5.3", badge: "GLM" },
        { id: "glm-4-plus", label: "GLM-4 Plus", badge: "GLM" },
      ];
    }
    return [
      { id: "default", label: orchProviderObj?.modelName || "Mặc định" },
    ];
  }, [orchCaps, selectedOrchestrator, orchProviderObj]);

  // Computed thinking levels for Orchestrator
  const orchThinkingLevels = useMemo<AgentOption[]>(() => {
    if (selectedOrchestrator === "deepseek") {
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
    return [];
  }, [orchCaps, selectedOrchestrator]);

  // Computed modes for Orchestrator
  const orchModes = useMemo<AgentOption[]>(() => {
    if (selectedOrchestrator === "gemini" || selectedOrchestrator === "qwen" || selectedOrchestrator === "claude" || selectedOrchestrator === "deepseek") {
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
    if (selectedLead === "copilot") {
      return [
        { id: "auto", label: "Copilot Auto", badge: "Auto" },
        { id: "gpt_5_6_think", label: "GPT > GPT-5.6 Sol Think Deeper", badge: "Think" },
        { id: "gpt_5_6_quick", label: "GPT > GPT-5.6 Sol Quick", badge: "Fast" },
      ];
    }
    if (selectedLead === "chatgpt") {
      return [
        { id: "o3-mini", label: "o3-mini (Reasoning)", badge: "Think" },
        { id: "gpt-4o", label: "GPT-4o (Omni)", badge: "Auto" },
      ];
    }
    if (selectedLead === "qwen") {
      return [
        { id: "qwen-3.8-max", label: "Qwen 3.8 Max (Reasoning)", badge: "Max" },
        { id: "qwen-3.7-plus", label: "Qwen 3.7 Plus", badge: "Plus" },
        { id: "qwen-3.8-omni-flash", label: "Qwen 3.8 Omni-Flash", badge: "Omni" },
      ];
    }
    if (selectedLead === "deepseek") {
      return [];
    }
    if (selectedLead === "claude") {
      return [
        { id: "claude-sonnet-5.5", label: "Claude Sonnet 5.5 (Cân bằng & thông minh)", badge: "Sonnet" },
        { id: "claude-haiku-5.5", label: "Claude Haiku 5.5 (Phản hồi nhanh)", badge: "Haiku" },
        { id: "claude-opus-5.5", label: "Claude Opus 5.5 (Pro)", badge: "Opus" },
        { id: "claude-fable-5.1", label: "Claude Fable 5.1 (Max)", badge: "Fable" },
      ];
    }
    if (selectedLead === "zhipu") {
      return [
        { id: "glm-5.3", label: "GLM-5.3", badge: "GLM" },
        { id: "glm-4-plus", label: "GLM-4 Plus", badge: "GLM" },
      ];
    }
    return [
      { id: "default", label: leadProviderObj?.modelName || "Mặc định" },
    ];
  }, [leadCaps, selectedLead, leadProviderObj]);

  // Computed thinking levels for Lead Provider
  const leadThinkingLevels = useMemo<AgentOption[]>(() => {
    if (selectedLead === "deepseek") {
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
    return [];
  }, [leadCaps, selectedLead]);

  // Computed modes for Lead Provider
  const leadModes = useMemo<AgentOption[]>(() => {
    if (selectedLead === "gemini" || selectedLead === "qwen" || selectedLead === "claude" || selectedLead === "deepseek") {
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
        .filter((p) => p.supportsDeepMode || ["deepseek", "qwen", "gemini", "chatgpt", "copilot", "claude", "perplexity"].includes(p.id))
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
      orchConfig.mode = orchMode || "high";
    } else if (selectedOrchestrator === "qwen") {
      orchConfig.model = orchModel || "qwen-3.8-max";
      orchConfig.thinking = orchThinkingLevel || "thinking";
      orchConfig.mode = "";
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
      leadConfig.mode = leadMode || "high";
    } else if (selectedLead === "qwen") {
      leadConfig.model = leadModel || "qwen-3.8-max";
      leadConfig.thinking = leadThinkingLevel || "thinking";
      leadConfig.mode = "";
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
                ) : (
                  <>
                    {/* 1. Model Selector */}
                    {orchModels.length > 0 && (
                      <label className="agent-option-inline">
                        <span>Mô hình:</span>
                        <select
                          value={orchModel}
                          onChange={(e) => {
                            const val = e.target.value;
                            setOrchModel(val);
                            onUpdateSelection?.(selectedOrchestrator, { model_id: val });
                          }}
                          className="agent-select"
                        >
                          {orchModels.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.label} {m.badge ? `[${m.badge}]` : ""}
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
                          value={orchThinkingLevel}
                          onChange={(e) => {
                            const val = e.target.value;
                            setOrchThinkingLevel(val);
                            onUpdateSelection?.(selectedOrchestrator, { thinking_level_id: val });
                          }}
                          className="agent-select"
                        >
                          {orchThinkingLevels.map((lvl) => (
                            <option key={lvl.id} value={lvl.id}>
                              {lvl.label} {lvl.badge ? `[${lvl.badge}]` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
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
                ) : (
                  <>
                    {/* 1. Model Selector */}
                    {leadModels.length > 0 && (
                      <label className="agent-option-inline">
                        <span>Mô hình:</span>
                        <select
                          value={leadModel}
                          onChange={(e) => {
                            const val = e.target.value;
                            setLeadModel(val);
                            onUpdateSelection?.(selectedLead, { model_id: val });
                          }}
                          className="agent-select"
                        >
                          {leadModels.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.label} {m.badge ? `[${m.badge}]` : ""}
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
                          value={leadThinkingLevel}
                          onChange={(e) => {
                            const val = e.target.value;
                            setLeadThinkingLevel(val);
                            onUpdateSelection?.(selectedLead, { thinking_level_id: val });
                          }}
                          className="agent-select"
                        >
                          {leadThinkingLevels.map((lvl) => (
                            <option key={lvl.id} value={lvl.id}>
                              {lvl.label} {lvl.badge ? `[${lvl.badge}]` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
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
