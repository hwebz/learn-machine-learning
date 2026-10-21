"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { PROVIDERS_LIST } from "../../lib/constants";
import { ProviderInfo } from "../../types/chat";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";
import { CloseIcon } from "../icons/Icons";

import {
  resolveSubProviderLiveConfig,
  constructOrchestrationPrompt,
} from "../../lib/agentPromptBuilder";

import { AgentTopicSection, SUGGESTED_AGENT_TOPICS } from "./AgentTopicSection";
import { ProviderGridPicker } from "./ProviderGridPicker";
import { ProviderFinetuneSection } from "./ProviderFinetuneSection";
import { SubProvidersDelegationSection } from "./SubProvidersDelegationSection";
import { OrchestratorPromptPreview } from "./OrchestratorPromptPreview";
import { AgentToneSection } from "./AgentToneSection";

// Re-export for backward compatibility
export { resolveSubProviderLiveConfig, constructOrchestrationPrompt, SUGGESTED_AGENT_TOPICS };

export interface AgentConfigScreenProps {
  onStartAgentResearch: (config: {
    query: string;
    orchestrator_provider: string;
    orchestrator_config: Record<string, any>;
    lead_provider: string;
    lead_config: Record<string, any>;
    summarization_provider: string;
    summarization_config: Record<string, any>;
    tone: string;
    delegated_providers?: string[];
    provider_configs?: Record<string, any>;
    provider_capabilities?: Record<string, any>;
    enable_fact_check?: boolean;
    fact_check_provider?: string;
    fact_check_config?: Record<string, any>;
  }) => void;
  onCancel: () => void;
  providers?: ProviderInfo[];
  capabilitiesMap?: Record<string, ProviderLiveCapabilities>;
  selectionsMap?: Record<string, ProviderSelectionConfig>;
  onUpdateSelection?: (providerId: string, updates: Partial<ProviderSelectionConfig>) => void;
  onSyncProvider?: (providerId: string) => Promise<any>;
  loadingProvider?: string | null;
  onLoadCapabilities?: (providerId: string) => void;
  initialQuery?: string;
  initialOrchestratorProvider?: string;
  initialOrchestratorConfig?: Record<string, any>;
  initialLeadProvider?: string;
  initialLeadConfig?: Record<string, any>;
  initialSummarizationProvider?: string;
  initialSummarizationConfig?: Record<string, any>;
  initialDelegatedProviders?: string[];
  initialTone?: string;
  initialEnableFactCheck?: boolean;
  initialFactCheckProvider?: string;
  initialFactCheckConfig?: Record<string, any>;
}

const DEFAULT_DELEGATED = ["copilot", "gemini", "chatgpt", "deepseek", "qwen", "perplexity", "claude"];

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
  initialQuery,
  initialOrchestratorProvider,
  initialOrchestratorConfig,
  initialLeadProvider,
  initialLeadConfig,
  initialSummarizationProvider,
  initialSummarizationConfig,
  initialDelegatedProviders,
  initialTone,
  initialEnableFactCheck,
  initialFactCheckProvider,
  initialFactCheckConfig,
}: AgentConfigScreenProps) {
  const availableProviders = providers && providers.length > 0 ? providers : PROVIDERS_LIST;

  // 1. Topic Query
  const [query, setQuery] = useState(initialQuery || "");

  // 2. Orchestrator State
  const [selectedOrchestrator, setSelectedOrchestrator] = useState<string>(
    initialOrchestratorProvider || "gemini"
  );
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

  // 3. Delegated Sub-Providers State
  const [selectedDelegatedProviders, setSelectedDelegatedProviders] = useState<string[]>(
    initialDelegatedProviders && initialDelegatedProviders.length > 0
      ? initialDelegatedProviders
      : DEFAULT_DELEGATED
  );
  const [isSyncingAllSub, setIsSyncingAllSub] = useState(false);
  const [subSyncMessage, setSubSyncMessage] = useState<string | null>(null);

  // 4. Lead Provider State
  const [selectedLead, setSelectedLead] = useState<string>(
    initialLeadProvider || "chatgpt"
  );
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

  // 5. Summarization Provider State (Default: 9router with Daily model)
  const [selectedSummarizer, setSelectedSummarizer] = useState<string>(
    initialSummarizationProvider || "9router"
  );
  const [sumThinking, setSumThinking] = useState<boolean>(true);
  const [sumThinkingLevel, setSumThinkingLevel] = useState<string>("auto");
  const [sumModel, setSumModel] = useState<string>(
    initialSummarizationConfig?.model_id || initialSummarizationConfig?.model || "Daily"
  );
  const [sumMode, setSumMode] = useState<string>("");
  const [sumDeepThinking, setSumDeepThinking] = useState<boolean>(false);
  const [sumWebSearch, setSumWebSearch] = useState<boolean>(false);
  const [sumDeepResearch, setSumDeepResearch] = useState<boolean>(false);
  const [sumResearchMode, setSumResearchMode] = useState<string>("normal");
  const [isSyncingSum, setIsSyncingSum] = useState(false);
  const [sumSyncMessage, setSumSyncMessage] = useState<string | null>(null);

  // 6. Fact-Check State
  const [enableFactCheck, setEnableFactCheck] = useState<boolean>(initialEnableFactCheck || false);
  const [selectedFactChecker, setSelectedFactChecker] = useState<string>(
    initialFactCheckProvider || "perplexity"
  );

  // 7. Tone & Submit State
  const [selectedTone, setSelectedTone] = useState<string>(
    initialTone || "professional"
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Synchronize initial props
  useEffect(() => {
    if (initialOrchestratorProvider) setSelectedOrchestrator(initialOrchestratorProvider);
    if (initialLeadProvider) setSelectedLead(initialLeadProvider);
    if (initialSummarizationProvider) setSelectedSummarizer(initialSummarizationProvider);
    if (initialDelegatedProviders && initialDelegatedProviders.length > 0) {
      setSelectedDelegatedProviders(initialDelegatedProviders);
    }
    if (initialTone) setSelectedTone(initialTone);
    if (initialQuery !== undefined) setQuery(initialQuery);
    if (initialEnableFactCheck !== undefined) setEnableFactCheck(initialEnableFactCheck);
    if (initialFactCheckProvider) setSelectedFactChecker(initialFactCheckProvider);
  }, [
    initialOrchestratorProvider,
    initialLeadProvider,
    initialSummarizationProvider,
    initialDelegatedProviders,
    initialTone,
    initialQuery,
    initialEnableFactCheck,
    initialFactCheckProvider,
  ]);

  // Load capabilities if missing
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

  useEffect(() => {
    if (onLoadCapabilities && selectedSummarizer && !capabilitiesMap[selectedSummarizer]) {
      onLoadCapabilities(selectedSummarizer);
    }
  }, [selectedSummarizer, capabilitiesMap, onLoadCapabilities]);

  useEffect(() => {
    if (onLoadCapabilities && selectedFactChecker && !capabilitiesMap[selectedFactChecker]) {
      onLoadCapabilities(selectedFactChecker);
    }
  }, [selectedFactChecker, capabilitiesMap, onLoadCapabilities]);

  // Merged selections for active providers
  const orchSel = useMemo(() => {
    const base = selectionsMap[selectedOrchestrator] || {};
    const configMerged = selectedOrchestrator === initialOrchestratorProvider ? initialOrchestratorConfig : undefined;
    if (!configMerged) return base;
    return {
      ...base,
      ...configMerged,
      model_id: configMerged.model_id || configMerged.model || base.model_id,
      thinking_level_id: configMerged.thinking_level_id || (typeof configMerged.thinking === "string" ? configMerged.thinking : undefined) || base.thinking_level_id,
      mode_id: configMerged.mode_id || configMerged.mode || base.mode_id,
      deep_research: configMerged.deep_research !== undefined ? configMerged.deep_research : base.deep_research,
      deep_thinking: configMerged.deep_thinking !== undefined ? configMerged.deep_thinking : base.deep_thinking,
      web_search: configMerged.web_search !== undefined ? configMerged.web_search : base.web_search,
      research_mode: configMerged.research_mode || base.research_mode,
    };
  }, [selectionsMap, selectedOrchestrator, initialOrchestratorProvider, initialOrchestratorConfig]);

  const leadSel = useMemo(() => {
    const base = selectionsMap[selectedLead] || {};
    const configMerged = selectedLead === initialLeadProvider ? initialLeadConfig : undefined;
    if (!configMerged) return base;
    return {
      ...base,
      ...configMerged,
      model_id: configMerged.model_id || configMerged.model || base.model_id,
      thinking_level_id: configMerged.thinking_level_id || (typeof configMerged.thinking === "string" ? configMerged.thinking : undefined) || base.thinking_level_id,
      mode_id: configMerged.mode_id || configMerged.mode || base.mode_id,
      deep_research: configMerged.deep_research !== undefined ? configMerged.deep_research : base.deep_research,
      deep_thinking: configMerged.deep_thinking !== undefined ? configMerged.deep_thinking : base.deep_thinking,
      web_search: configMerged.web_search !== undefined ? configMerged.web_search : base.web_search,
      research_mode: configMerged.research_mode || base.research_mode,
    };
  }, [selectionsMap, selectedLead, initialLeadProvider, initialLeadConfig]);

  const sumSel = useMemo(() => {
    const base = selectionsMap[selectedSummarizer] || {};
    const configMerged = selectedSummarizer === initialSummarizationProvider ? initialSummarizationConfig : undefined;
    if (!configMerged) {
      return {
        ...base,
        model_id: selectedSummarizer === "9router" ? "Daily" : base.model_id,
      };
    }
    return {
      ...base,
      ...configMerged,
      model_id: configMerged.model_id || configMerged.model || (selectedSummarizer === "9router" ? "Daily" : base.model_id),
      thinking_level_id: configMerged.thinking_level_id || (typeof configMerged.thinking === "string" ? configMerged.thinking : undefined) || base.thinking_level_id,
      mode_id: configMerged.mode_id || configMerged.mode || base.mode_id,
      deep_research: configMerged.deep_research !== undefined ? configMerged.deep_research : base.deep_research,
      deep_thinking: configMerged.deep_thinking !== undefined ? configMerged.deep_thinking : base.deep_thinking,
      web_search: configMerged.web_search !== undefined ? configMerged.web_search : base.web_search,
      research_mode: configMerged.research_mode || base.research_mode,
    };
  }, [selectionsMap, selectedSummarizer, initialSummarizationProvider, initialSummarizationConfig]);

  // Sync Orchestrator local state when provider or selection changes
  useEffect(() => {
    const caps = capabilitiesMap[selectedOrchestrator];
    const isDr = orchSel?.deep_research !== undefined ? orchSel.deep_research : (caps?.deep_research ?? false);
    const isDt = orchSel?.deep_thinking !== undefined ? orchSel.deep_thinking : (caps?.deep_thinking ?? false);
    const isWs = orchSel?.web_search !== undefined ? orchSel.web_search : (caps?.web_search ?? true);

    setOrchDeepResearch(isDr);
    setOrchDeepThinking(isDt);
    setOrchWebSearch(isWs);
    setOrchResearchMode(orchSel?.research_mode || caps?.research_mode || "normal");

    if (orchSel?.model_id) {
      setOrchModel(orchSel.model_id);
    } else if (caps?.selected_model_id) {
      setOrchModel(caps.selected_model_id);
    } else if (caps?.available_models && caps.available_models.length > 0) {
      setOrchModel(caps.available_models[0].id);
    } else {
      setOrchModel("default");
    }

    if (orchSel?.thinking_level_id) {
      setOrchThinkingLevel(orchSel.thinking_level_id);
    } else if (caps?.selected_thinking_level_id) {
      setOrchThinkingLevel(caps.selected_thinking_level_id);
    } else if (caps?.thinking_levels && caps.thinking_levels.length > 0) {
      setOrchThinkingLevel(caps.thinking_levels[0].id);
    } else {
      setOrchThinkingLevel(selectedOrchestrator === "meta" && isDt ? "thinking" : "auto");
    }

    if (orchSel?.mode_id) {
      setOrchMode(orchSel.mode_id);
    } else if (caps?.selected_mode_id) {
      setOrchMode(caps.selected_mode_id);
    } else if (caps?.modes && caps.modes.length > 0) {
      setOrchMode(caps.modes[0].id);
    } else {
      setOrchMode("");
    }
  }, [selectedOrchestrator, capabilitiesMap, orchSel]);

  // Sync Lead local state when provider or selection changes
  useEffect(() => {
    const caps = capabilitiesMap[selectedLead];
    const isDr = leadSel?.deep_research !== undefined ? leadSel.deep_research : (caps?.deep_research ?? false);
    const isDt = leadSel?.deep_thinking !== undefined ? leadSel.deep_thinking : (caps?.deep_thinking ?? false);
    const isWs = leadSel?.web_search !== undefined ? leadSel.web_search : (caps?.web_search ?? true);

    setLeadDeepResearch(isDr);
    setLeadDeepThinking(isDt);
    setLeadWebSearch(isWs);
    setLeadResearchMode(leadSel?.research_mode || caps?.research_mode || "normal");

    if (leadSel?.model_id) {
      setLeadModel(leadSel.model_id);
    } else if (caps?.selected_model_id) {
      setLeadModel(caps.selected_model_id);
    } else if (caps?.available_models && caps.available_models.length > 0) {
      setLeadModel(caps.available_models[0].id);
    } else {
      setLeadModel("default");
    }

    if (leadSel?.thinking_level_id) {
      setLeadThinkingLevel(leadSel.thinking_level_id);
    } else if (caps?.selected_thinking_level_id) {
      setLeadThinkingLevel(caps.selected_thinking_level_id);
    } else if (caps?.thinking_levels && caps.thinking_levels.length > 0) {
      setLeadThinkingLevel(caps.thinking_levels[0].id);
    } else {
      setLeadThinkingLevel(selectedLead === "meta" && isDt ? "thinking" : "auto");
    }

    if (leadSel?.mode_id) {
      setLeadMode(leadSel.mode_id);
    } else if (caps?.selected_mode_id) {
      setLeadMode(caps.selected_mode_id);
    } else if (caps?.modes && caps.modes.length > 0) {
      setLeadMode(caps.modes[0].id);
    } else {
      setLeadMode("");
    }
  }, [selectedLead, capabilitiesMap, leadSel]);

  // Sync Summarizer local state when provider or selection changes
  useEffect(() => {
    const caps = capabilitiesMap[selectedSummarizer];
    const isDr = sumSel?.deep_research !== undefined ? sumSel.deep_research : (caps?.deep_research ?? false);
    const isDt = sumSel?.deep_thinking !== undefined ? sumSel.deep_thinking : (caps?.deep_thinking ?? false);
    const isWs = sumSel?.web_search !== undefined ? sumSel.web_search : (caps?.web_search ?? false);

    setSumDeepResearch(isDr);
    setSumDeepThinking(isDt);
    setSumWebSearch(isWs);
    setSumResearchMode(sumSel?.research_mode || caps?.research_mode || "normal");

    if (initialSummarizationConfig?.model_id || initialSummarizationConfig?.model) {
      setSumModel(initialSummarizationConfig.model_id || initialSummarizationConfig.model);
    } else if (selectedSummarizer === "9router") {
      setSumModel("Daily");
    } else if (sumSel?.model_id) {
      setSumModel(sumSel.model_id);
    } else if (caps?.selected_model_id) {
      setSumModel(caps.selected_model_id);
    } else if (caps?.available_models && caps.available_models.length > 0) {
      setSumModel(caps.available_models[0].id);
    } else {
      setSumModel("Daily");
    }

    if (sumSel?.thinking_level_id) {
      setSumThinkingLevel(sumSel.thinking_level_id);
    } else if (caps?.selected_thinking_level_id) {
      setSumThinkingLevel(caps.selected_thinking_level_id);
    } else if (caps?.thinking_levels && caps.thinking_levels.length > 0) {
      setSumThinkingLevel(caps.thinking_levels[0].id);
    } else {
      setSumThinkingLevel(selectedSummarizer === "meta" && isDt ? "thinking" : "auto");
    }

    if (sumSel?.mode_id) {
      setSumMode(sumSel.mode_id);
    } else if (caps?.selected_mode_id) {
      setSumMode(caps.selected_mode_id);
    } else if (caps?.modes && caps.modes.length > 0) {
      setSumMode(caps.modes[0].id);
    } else {
      setSumMode("");
    }
  }, [selectedSummarizer, capabilitiesMap, sumSel]);

  // Live Decomposition Prompt Construction
  const constructedOrchestratorPrompt = useMemo(() => {
    return constructOrchestrationPrompt(
      query.trim(),
      selectedDelegatedProviders,
      capabilitiesMap,
      selectionsMap,
      availableProviders
    );
  }, [query, selectedDelegatedProviders, capabilitiesMap, selectionsMap, availableProviders]);

  // Handlers for Delegated Providers
  const toggleDelegatedProvider = useCallback((providerId: string) => {
    setSelectedDelegatedProviders((prev) =>
      prev.includes(providerId) ? prev.filter((id) => id !== providerId) : [...prev, providerId]
    );
  }, []);

  const handleSelectAllDelegated = useCallback(() => {
    setSelectedDelegatedProviders(availableProviders.map((p) => p.id));
  }, [availableProviders]);

  const handleSelectTopThinkingDelegated = useCallback(() => {
    setSelectedDelegatedProviders(
      availableProviders
        .filter((p) => p.supportsDeepMode || ["deepseek", "qwen", "gemini", "chatgpt", "copilot", "claude", "perplexity", "kimi"].includes(p.id))
        .map((p) => p.id)
    );
  }, [availableProviders]);

  const handleDeselectAllDelegated = useCallback(() => {
    setSelectedDelegatedProviders([]);
  }, []);

  // Handlers for DOM Resync
  const handleSyncOrchestrator = useCallback(async () => {
    if (isSyncingOrch || !onSyncProvider) return;
    setIsSyncingOrch(true);
    setOrchSyncMessage(null);
    try {
      const res = await onSyncProvider(selectedOrchestrator);
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setOrchSyncMessage(`✓ Đã đồng bộ DOM thành công lúc ${timeStr}`);
      if (res?.selected_model_id) setOrchModel(res.selected_model_id);
      if (res?.selected_thinking_level_id) setOrchThinkingLevel(res.selected_thinking_level_id);
      if (res?.selected_mode_id) setOrchMode(res.selected_mode_id);
    } catch (err: any) {
      setOrchSyncMessage(`Lỗi đồng bộ DOM: ${err?.message || "Không thể kết nối"}`);
    } finally {
      setIsSyncingOrch(false);
    }
  }, [isSyncingOrch, onSyncProvider, selectedOrchestrator]);

  const handleSyncLead = useCallback(async () => {
    if (isSyncingLead || !onSyncProvider) return;
    setIsSyncingLead(true);
    setLeadSyncMessage(null);
    try {
      const res = await onSyncProvider(selectedLead);
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setLeadSyncMessage(`✓ Đã đồng bộ DOM thành công lúc ${timeStr}`);
      if (res?.selected_model_id) setLeadModel(res.selected_model_id);
      if (res?.selected_thinking_level_id) setLeadThinkingLevel(res.selected_thinking_level_id);
      if (res?.selected_mode_id) setLeadMode(res.selected_mode_id);
    } catch (err: any) {
      setLeadSyncMessage(`Lỗi đồng bộ DOM: ${err?.message || "Không thể kết nối"}`);
    } finally {
      setIsSyncingLead(false);
    }
  }, [isSyncingLead, onSyncProvider, selectedLead]);

  const handleSyncSummarizer = useCallback(async () => {
    if (isSyncingSum || !onSyncProvider) return;
    setIsSyncingSum(true);
    setSumSyncMessage(null);
    try {
      const res = await onSyncProvider(selectedSummarizer);
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setSumSyncMessage(`✓ Đã đồng bộ DOM thành công lúc ${timeStr}`);
      if (res?.selected_model_id) setSumModel(res.selected_model_id);
      if (res?.selected_thinking_level_id) setSumThinkingLevel(res.selected_thinking_level_id);
      if (res?.selected_mode_id) setSumMode(res.selected_mode_id);
    } catch (err: any) {
      setSumSyncMessage(`Lỗi đồng bộ DOM: ${err?.message || "Không thể kết nối"}`);
    } finally {
      setIsSyncingSum(false);
    }
  }, [isSyncingSum, onSyncProvider, selectedSummarizer]);

  const handleSyncAllSelectedSubProviders = useCallback(async () => {
    if (isSyncingAllSub || !onSyncProvider || selectedDelegatedProviders.length === 0) return;
    setIsSyncingAllSub(true);
    setSubSyncMessage(null);
    let successCount = 0;
    try {
      for (const pid of selectedDelegatedProviders) {
        try {
          await onSyncProvider(pid);
          successCount++;
        } catch (e) {
          console.warn(`Failed to sync DOM for sub-provider ${pid}`, e);
        }
      }
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setSubSyncMessage(`✓ Đã đồng bộ DOM thành công ${successCount}/${selectedDelegatedProviders.length} sub-providers lúc ${timeStr}`);
    } catch (err: any) {
      setSubSyncMessage(`Lỗi đồng bộ: ${err?.message || "Không thể đồng bộ"}`);
    } finally {
      setIsSyncingAllSub(false);
    }
  }, [isSyncingAllSub, onSyncProvider, selectedDelegatedProviders]);

  // Form Submit Handler
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || selectedDelegatedProviders.length === 0 || isSubmitting) return;

    setIsSubmitting(true);

    const orchResolved = resolveSubProviderLiveConfig(
      selectedOrchestrator,
      {
        ...selectionsMap,
        [selectedOrchestrator]: {
          ...selectionsMap[selectedOrchestrator],
          model_id: orchModel,
          thinking_level_id: orchThinkingLevel,
          mode_id: orchMode,
          deep_research: orchDeepResearch,
          deep_thinking: orchDeepThinking,
          web_search: orchWebSearch,
          research_mode: orchResearchMode,
        },
      },
      capabilitiesMap
    );

    const leadResolved = resolveSubProviderLiveConfig(
      selectedLead,
      {
        ...selectionsMap,
        [selectedLead]: {
          ...selectionsMap[selectedLead],
          model_id: leadModel,
          thinking_level_id: leadThinkingLevel,
          mode_id: leadMode,
          deep_research: leadDeepResearch,
          deep_thinking: leadDeepThinking,
          web_search: leadWebSearch,
          research_mode: leadResearchMode,
        },
      },
      capabilitiesMap
    );

    const sumResolved = resolveSubProviderLiveConfig(
      selectedSummarizer,
      {
        ...selectionsMap,
        [selectedSummarizer]: {
          ...selectionsMap[selectedSummarizer],
          model_id: sumModel,
          thinking_level_id: sumThinkingLevel,
          mode_id: sumMode,
          deep_research: sumDeepResearch,
          deep_thinking: sumDeepThinking,
          web_search: sumWebSearch,
          research_mode: sumResearchMode,
        },
      },
      capabilitiesMap
    );

    const subProviderConfigs: Record<string, any> = {};
    const subProviderCaps: Record<string, any> = {};
    selectedDelegatedProviders.forEach((pid) => {
      const subResolved = resolveSubProviderLiveConfig(pid, selectionsMap, capabilitiesMap);
      subProviderConfigs[pid] = subResolved.configObj;
      if (capabilitiesMap[pid]) {
        subProviderCaps[pid] = capabilitiesMap[pid];
      }
    });

    const fcResolved = enableFactCheck
      ? resolveSubProviderLiveConfig(selectedFactChecker, selectionsMap, capabilitiesMap)
      : null;

    onStartAgentResearch({
      query: query.trim(),
      orchestrator_provider: selectedOrchestrator,
      orchestrator_config: {
        ...orchResolved.configObj,
        model: orchModel,
        thinking: orchThinking,
        mode: orchMode,
      },
      delegated_providers: selectedDelegatedProviders,
      lead_provider: selectedLead,
      lead_config: {
        ...leadResolved.configObj,
        model: leadModel,
        thinking: leadThinking,
        mode: leadMode,
      },
      summarization_provider: selectedSummarizer,
      summarization_config: {
        ...sumResolved.configObj,
        model: sumModel,
        thinking: sumThinking,
        mode: sumMode,
      },
      tone: selectedTone,
      provider_configs: subProviderConfigs,
      provider_capabilities: subProviderCaps,
      enable_fact_check: enableFactCheck,
      fact_check_provider: enableFactCheck ? selectedFactChecker : undefined,
      fact_check_config: enableFactCheck ? fcResolved?.configObj : undefined,
    });
  };

  const orchProviderObj = availableProviders.find((p) => p.id === selectedOrchestrator) || availableProviders[0];
  const leadProviderObj = availableProviders.find((p) => p.id === selectedLead) || availableProviders[0];
  const summarizerProviderObj = availableProviders.find((p) => p.id === selectedSummarizer) || availableProviders[0];

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
          <AgentTopicSection query={query} setQuery={setQuery} />

          {/* Section 2: Orchestrator Provider Selection & Fine-Tuning */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">2</span>
                <span>Chọn Orchestrator (Tác nhân Điều phối phân rã bài toán)</span>
              </label>
              <span className="agent-role-pill orch">Lập kế hoạch & Phân tách</span>
            </div>
            <p className="agent-section-desc">
              Tác nhân chủ trì tiếp nhận đề tài của bạn, phân tích toàn diện và chia nhỏ thành các nhiệm vụ con (sub-topics) để giao cho các AI khác.
            </p>

            <ProviderGridPicker
              providers={availableProviders}
              selectedProviderId={selectedOrchestrator}
              onSelectProvider={setSelectedOrchestrator}
              capabilitiesMap={capabilitiesMap}
              nameRadioGroup="orchestrator_radio"
              selectedCardClass="selected"
            />

            <ProviderFinetuneSection
              role="orchestrator"
              provider={orchProviderObj}
              caps={capabilitiesMap[selectedOrchestrator]}
              model={orchModel}
              setModel={setOrchModel}
              thinkingLevel={orchThinkingLevel}
              setThinkingLevel={setOrchThinkingLevel}
              thinking={orchThinking}
              setThinking={setOrchThinking}
              deepThinking={orchDeepThinking}
              setDeepThinking={setOrchDeepThinking}
              webSearch={orchWebSearch}
              setWebSearch={setOrchWebSearch}
              deepResearch={orchDeepResearch}
              setDeepResearch={setOrchDeepResearch}
              researchMode={orchResearchMode}
              setResearchMode={setOrchResearchMode}
              mode={orchMode}
              setMode={setOrchMode}
              onUpdateSelection={onUpdateSelection}
              onSync={handleSyncOrchestrator}
              isSyncing={isSyncingOrch}
              syncMessage={orchSyncMessage}
              loadingProvider={loadingProvider}
            />
          </div>

          {/* Section 3: Sub Providers Delegation & Batch Sync */}
          <SubProvidersDelegationSection
            availableProviders={availableProviders}
            selectedDelegatedProviders={selectedDelegatedProviders}
            toggleDelegatedProvider={toggleDelegatedProvider}
            onSelectTopThinking={handleSelectTopThinkingDelegated}
            onSelectAll={handleSelectAllDelegated}
            onDeselectAll={handleDeselectAllDelegated}
            capabilitiesMap={capabilitiesMap}
            selectionsMap={selectionsMap}
            onSyncProvider={onSyncProvider}
            isSyncingAllSub={isSyncingAllSub}
            onSyncAllSub={handleSyncAllSelectedSubProviders}
            subSyncMessage={subSyncMessage}
          />

          {/* Section 3.5: Live Decomposition Prompt Preview */}
          <OrchestratorPromptPreview
            promptText={constructedOrchestratorPrompt}
            orchestratorProvider={orchProviderObj}
            orchestratorModel={orchModel}
            selectedDelegatedCount={selectedDelegatedProviders.length}
            selectedDelegatedProviders={selectedDelegatedProviders}
            capabilitiesMap={capabilitiesMap}
          />

          {/* Section 4: Lead Provider Selection & Fine-Tuning */}
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

            <ProviderGridPicker
              providers={availableProviders}
              selectedProviderId={selectedLead}
              onSelectProvider={setSelectedLead}
              capabilitiesMap={capabilitiesMap}
              nameRadioGroup="lead_radio"
              selectedCardClass="selected lead-selected"
            />

            <ProviderFinetuneSection
              role="lead"
              provider={leadProviderObj}
              caps={capabilitiesMap[selectedLead]}
              model={leadModel}
              setModel={setLeadModel}
              thinkingLevel={leadThinkingLevel}
              setThinkingLevel={setLeadThinkingLevel}
              thinking={leadThinking}
              setThinking={setLeadThinking}
              deepThinking={leadDeepThinking}
              setDeepThinking={setLeadDeepThinking}
              webSearch={leadWebSearch}
              setWebSearch={setLeadWebSearch}
              deepResearch={leadDeepResearch}
              setDeepResearch={setLeadDeepResearch}
              researchMode={leadResearchMode}
              setResearchMode={setLeadResearchMode}
              mode={leadMode}
              setMode={setLeadMode}
              onUpdateSelection={onUpdateSelection}
              onSync={handleSyncLead}
              isSyncing={isSyncingLead}
              syncMessage={leadSyncMessage}
              loadingProvider={loadingProvider}
            />
          </div>

          {/* Section 5: Summarization Provider Selection & Fine-Tuning */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">5</span>
                <span>Chọn Summarization Provider (Tóm tắt bối cảnh các vòng)</span>
              </label>
              <span
                className="agent-role-pill summarizer"
                style={{
                  background: "rgba(217, 119, 6, 0.15)",
                  color: "#d97706",
                  borderColor: "rgba(217, 119, 6, 0.3)",
                }}
              >
                Tóm tắt bối cảnh
              </span>
            </div>
            <p className="agent-section-desc">
              Tác nhân chạy tuần tự trước khi chia nhỏ nhiệm vụ ở các vòng tiếp theo (round 2+) để cô đọng ngữ cảnh các vòng trước, tránh vượt quá giới hạn token. Mặc định là 9router (Daily).
            </p>

            <ProviderGridPicker
              providers={availableProviders}
              selectedProviderId={selectedSummarizer}
              onSelectProvider={setSelectedSummarizer}
              capabilitiesMap={capabilitiesMap}
              nameRadioGroup="summarizer_radio"
              selectedCardClass="selected summarizer-selected"
            />

            <ProviderFinetuneSection
              role="summarizer"
              provider={summarizerProviderObj}
              caps={capabilitiesMap[selectedSummarizer]}
              model={sumModel}
              setModel={setSumModel}
              thinkingLevel={sumThinkingLevel}
              setThinkingLevel={setSumThinkingLevel}
              thinking={sumThinking}
              setThinking={setSumThinking}
              deepThinking={sumDeepThinking}
              setDeepThinking={setSumDeepThinking}
              webSearch={sumWebSearch}
              setWebSearch={setSumWebSearch}
              deepResearch={sumDeepResearch}
              setDeepResearch={setSumDeepResearch}
              researchMode={sumResearchMode}
              setResearchMode={setSumResearchMode}
              mode={sumMode}
              setMode={setSumMode}
              onUpdateSelection={onUpdateSelection}
              onSync={handleSyncSummarizer}
              isSyncing={isSyncingSum}
              syncMessage={sumSyncMessage}
              loadingProvider={loadingProvider}
            />
          </div>

          {/* Section 6: Report Tone Selection */}
          <AgentToneSection
            selectedTone={selectedTone}
            setSelectedTone={setSelectedTone}
            step={6}
          />

          {/* Section 7: Fact-Check Phase (Post-Research Verification) */}
          <div
            className="agent-section"
            style={{
              border: enableFactCheck ? "1px solid rgba(16, 185, 129, 0.4)" : undefined,
              transition: "border 0.2s ease",
            }}
          >
            <div className="agent-section-header-row">
              <label className="agent-section-label" style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
                <span className="agent-section-step" style={{ background: enableFactCheck ? "#10b981" : undefined }}>
                  7
                </span>
                <span>Kiểm chứng sự thật (Fact-Check Phase)</span>
              </label>
              <span
                className="agent-role-pill"
                style={{
                  background: enableFactCheck ? "rgba(16, 185, 129, 0.15)" : "rgba(148, 163, 184, 0.15)",
                  color: enableFactCheck ? "#10b981" : "#94a3b8",
                  borderColor: enableFactCheck ? "rgba(16, 185, 129, 0.3)" : "rgba(148, 163, 184, 0.3)",
                }}
              >
                {enableFactCheck ? "✅ Đang kích hoạt" : "Tùy chọn"}
              </span>
            </div>
            <div
              style={{
                marginTop: 8,
                padding: "12px 16px",
                borderRadius: 8,
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
              }}
            >
              <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", userSelect: "none" }}>
                <input
                  type="checkbox"
                  checked={enableFactCheck}
                  onChange={(e) => setEnableFactCheck(e.target.checked)}
                  style={{ width: 16, height: 16, accentColor: "#10b981", cursor: "pointer" }}
                />
                <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary, #fff)" }}>
                  🔍 Kích hoạt kiểm chứng chéo luận điểm sau nghiên cứu
                </span>
              </label>
              <p style={{ fontSize: 12, color: "var(--text-secondary, #94a3b8)", marginTop: 6, marginLeft: 26, lineHeight: 1.5 }}>
                Sau khi các tác nhân hoàn thành nghiên cứu, Fact-Checker sẽ trích xuất 5-10 luận điểm thực tế then chốt, gán nhãn kiểm chứng (supported / single_source / unsupported / conflict) và chuyển trực tiếp vào chỉ thị cho Lead Provider trước khi tổng hợp báo cáo.
              </p>
              {enableFactCheck && (
                <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: "var(--text-primary, #fff)" }}>
                    Chọn Tác nhân Kiểm chứng (Fact-Checker Provider):
                  </div>
                  <ProviderGridPicker
                    providers={availableProviders}
                    selectedProviderId={selectedFactChecker}
                    onSelectProvider={setSelectedFactChecker}
                    capabilitiesMap={capabilitiesMap}
                    nameRadioGroup="fact_checker_radio"
                    selectedCardClass="selected"
                  />
                </div>
              )}
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
