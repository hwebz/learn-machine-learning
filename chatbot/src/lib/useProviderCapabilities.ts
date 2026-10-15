"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  ProviderLiveCapabilities,
  ProviderSelectionConfig,
  OptionItem,
  SupportedDataTypes,
  VoiceChatSupport,
} from "../types/capabilities";
import { fetchProviderCapabilities, syncAllProviderCapabilities } from "./api";

const CAPS_STORAGE_KEY = "deep_research_provider_capabilities";
const SELECTIONS_STORAGE_KEY = "deep_research_provider_selections";

function loadStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveStorage<T>(key: string, data: T): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (err) {
    console.warn(`Could not save ${key} to localStorage:`, err);
  }
}

export function useProviderCapabilities(currentProviderId: string = "chatgpt") {
  const [capabilitiesMap, setCapabilitiesMap] = useState<Record<string, ProviderLiveCapabilities>>({});
  const [selectionsMap, setSelectionsMap] = useState<Record<string, ProviderSelectionConfig>>({});
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);
  const [isSyncingAll, setIsSyncingAll] = useState<boolean>(false);
  const [lastError, setLastError] = useState<string | null>(null);

  // Initialize from localStorage on mount
  useEffect(() => {
    const cachedCaps = loadStorage<Record<string, ProviderLiveCapabilities>>(CAPS_STORAGE_KEY, {});
    const cachedSelections = loadStorage<Record<string, ProviderSelectionConfig>>(SELECTIONS_STORAGE_KEY, {});
    if (cachedCaps["chatgpt"]) {
      cachedCaps["chatgpt"].modes = [];
      cachedCaps["chatgpt"].selected_mode_id = undefined;
      cachedCaps["chatgpt"].available_models = [];
      cachedCaps["chatgpt"].selected_model_id = undefined;
      cachedCaps["chatgpt"].thinking_levels = [];
      cachedCaps["chatgpt"].selected_thinking_level_id = undefined;
      if (cachedCaps["chatgpt"].web_search === undefined) cachedCaps["chatgpt"].web_search = true;
      if (cachedCaps["chatgpt"].deep_research === undefined) cachedCaps["chatgpt"].deep_research = false;
      if (cachedCaps["chatgpt"].deep_thinking === undefined) cachedCaps["chatgpt"].deep_thinking = false;
    }
    if (cachedSelections["chatgpt"]) {
      cachedSelections["chatgpt"].model_id = "";
      cachedSelections["chatgpt"].thinking_level_id = "";
      cachedSelections["chatgpt"].mode_id = "";
      if (cachedSelections["chatgpt"].web_search === undefined) cachedSelections["chatgpt"].web_search = true;
      if (cachedSelections["chatgpt"].deep_research === undefined) cachedSelections["chatgpt"].deep_research = false;
      if (cachedSelections["chatgpt"].deep_thinking === undefined) cachedSelections["chatgpt"].deep_thinking = false;
    }
    if (cachedSelections["copilot"]) {
      cachedSelections["copilot"].model_id = "";
      cachedSelections["copilot"].thinking_level_id = "";
      if (!cachedSelections["copilot"].mode_id) {
        cachedSelections["copilot"].mode_id = "auto";
      }
    }
    if (cachedCaps["gemini"]) {
      cachedCaps["gemini"].modes = [];
      cachedCaps["gemini"].selected_mode_id = undefined;
    }
    if (cachedSelections["gemini"]) {
      cachedSelections["gemini"].mode_id = "";
    }
    if (cachedCaps["qwen"]) {
      cachedCaps["qwen"].modes = [];
      cachedCaps["qwen"].selected_mode_id = undefined;
    }
    if (cachedSelections["qwen"]) {
      cachedSelections["qwen"].mode_id = "";
    }
    if (cachedCaps["claude"]) {
      cachedCaps["claude"].modes = [];
      cachedCaps["claude"].selected_mode_id = undefined;
      const hasBadModels =
        !cachedCaps["claude"].available_models ||
        cachedCaps["claude"].available_models.length === 0 ||
        cachedCaps["claude"].available_models.some((m) => m.id === "default");
      if (hasBadModels) {
        cachedCaps["claude"].available_models = [
          { id: "claude-sonnet-5.5", label: "Sonnet 5.5", description: "Cân bằng hoàn hảo giữa trí tuệ và tốc độ", selected: true, badge: "Sonnet", disabled: false },
          { id: "claude-haiku-5.5", label: "Haiku 5.5", description: "Phản hồi nhanh nhất cho tác vụ ngắn gọn", selected: false, badge: "Haiku", disabled: false },
          { id: "claude-opus-5.5", label: "Opus 5.5", description: "Dành cho tài khoản Pro (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
          { id: "claude-fable-5.1", label: "Fable 5.1", description: "Dành cho các thử thách khó khăn nhất (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
        ];
        cachedCaps["claude"].selected_model_id = "claude-sonnet-5.5";
      } else {
        cachedCaps["claude"].available_models = cachedCaps["claude"].available_models.map((m) => {
          const isUpgrade = m.id === "claude-opus-5.5" || m.id === "claude-fable-5.1" || m.disabled || m.metadata?.upgrade;
          return { ...m, disabled: isUpgrade, badge: isUpgrade ? "Upgrade" : m.badge };
        });
      }
      const hasBadThinking =
        !cachedCaps["claude"].thinking_levels ||
        cachedCaps["claude"].thinking_levels.length === 0 ||
        cachedCaps["claude"].thinking_levels.some((t) => t.id === "auto");
      if (hasBadThinking) {
        cachedCaps["claude"].thinking_levels = [
          { id: "medium", label: "Medium", description: "Trung bình - Khuyên dùng, cân bằng độ sâu suy luận", selected: true, badge: "Med" },
          { id: "low", label: "Low", description: "Thấp - Phản hồi nhanh & tiết kiệm giới hạn tin nhắn", selected: false, badge: "Low" },
          { id: "high", label: "High", description: "Cao - Phân tích đa bước kỹ lưỡng cho bài toán phức tạp", selected: false, badge: "High" },
          { id: "extra", label: "Extra", description: "Rất cao - Suy luận chuyên sâu cho nghiên cứu phức tạp", selected: false, badge: "Extra" },
          { id: "max", label: "Max", description: "Tối đa - 8x hoặc nhiều hơn mức sử dụng giới hạn", selected: false, badge: "Max" },
        ];
        cachedCaps["claude"].selected_thinking_level_id = "medium";
      }
    }
    if (cachedSelections["claude"]) {
      cachedSelections["claude"].mode_id = "";
      if (
        !cachedSelections["claude"].model_id ||
        cachedSelections["claude"].model_id === "default" ||
        cachedSelections["claude"].model_id === "claude-opus-5.5" ||
        cachedSelections["claude"].model_id === "claude-fable-5.1"
      ) {
        cachedSelections["claude"].model_id = "claude-sonnet-5.5";
      }
      if (
        !cachedSelections["claude"].thinking_level_id ||
        cachedSelections["claude"].thinking_level_id === "auto"
      ) {
        cachedSelections["claude"].thinking_level_id = "medium";
      }
    }
    if (cachedCaps["deepseek"]) {
      cachedCaps["deepseek"].available_models = [];
      cachedCaps["deepseek"].selected_model_id = undefined;
      cachedCaps["deepseek"].thinking_levels = [];
      cachedCaps["deepseek"].selected_thinking_level_id = undefined;
      cachedCaps["deepseek"].modes = [];
      cachedCaps["deepseek"].selected_mode_id = undefined;
      if (cachedCaps["deepseek"].deep_thinking === undefined) {
        cachedCaps["deepseek"].deep_thinking = false;
      }
      if (cachedCaps["deepseek"].web_search === undefined) {
        cachedCaps["deepseek"].web_search = true;
      }
    }
    if (cachedSelections["deepseek"]) {
      cachedSelections["deepseek"].model_id = "";
      cachedSelections["deepseek"].thinking_level_id = "";
      cachedSelections["deepseek"].mode_id = "";
      if (cachedSelections["deepseek"].deep_thinking === undefined) {
        cachedSelections["deepseek"].deep_thinking = false;
      }
      if (cachedSelections["deepseek"].web_search === undefined) {
        cachedSelections["deepseek"].web_search = true;
      }
    }
    saveStorage(CAPS_STORAGE_KEY, cachedCaps);
    saveStorage(SELECTIONS_STORAGE_KEY, cachedSelections);
    setCapabilitiesMap(cachedCaps);
    setSelectionsMap(cachedSelections);
  }, []);

  // Fetch capabilities for provider if not yet loaded
  const loadProviderCapabilities = useCallback(
    async (provider: string, forceSync: boolean = false): Promise<ProviderLiveCapabilities | null> => {
      const p = provider.toLowerCase();
      setLoadingProvider(p);
      setLastError(null);

      try {
        let caps = await fetchProviderCapabilities(p, forceSync);
        if (p === "claude" && caps) {
          const hasBadModels =
            !caps.available_models ||
            caps.available_models.length === 0 ||
            caps.available_models.some((m) => m.id === "default");
          if (hasBadModels) {
            caps.available_models = [
              { id: "claude-sonnet-5.5", label: "Sonnet 5.5", description: "Cân bằng hoàn hảo giữa trí tuệ và tốc độ", selected: true, badge: "Sonnet", disabled: false },
              { id: "claude-haiku-5.5", label: "Haiku 5.5", description: "Phản hồi nhanh nhất cho tác vụ ngắn gọn", selected: false, badge: "Haiku", disabled: false },
              { id: "claude-opus-5.5", label: "Opus 5.5", description: "Dành cho tài khoản Pro (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
              { id: "claude-fable-5.1", label: "Fable 5.1", description: "Dành cho các thử thách khó khăn nhất (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
            ];
            caps.selected_model_id = "claude-sonnet-5.5";
          } else {
            caps.available_models = caps.available_models.map((m) => {
              const isUpgrade = m.id === "claude-opus-5.5" || m.id === "claude-fable-5.1" || m.disabled || m.metadata?.upgrade;
              return { ...m, disabled: isUpgrade, badge: isUpgrade ? "Upgrade" : m.badge };
            });
          }
          const hasBadThinking =
            !caps.thinking_levels ||
            caps.thinking_levels.length === 0 ||
            caps.thinking_levels.some((t) => t.id === "auto");
          if (hasBadThinking) {
            caps.thinking_levels = [
              { id: "medium", label: "Medium", description: "Trung bình - Khuyên dùng, cân bằng độ sâu suy luận", selected: true, badge: "Med" },
              { id: "low", label: "Low", description: "Thấp - Phản hồi nhanh & tiết kiệm giới hạn tin nhắn", selected: false, badge: "Low" },
              { id: "high", label: "High", description: "Cao - Phân tích đa bước kỹ lưỡng cho bài toán phức tạp", selected: false, badge: "High" },
              { id: "extra", label: "Extra", description: "Rất cao - Suy luận chuyên sâu cho nghiên cứu phức tạp", selected: false, badge: "Extra" },
              { id: "max", label: "Max", description: "Tối đa - 8x hoặc nhiều hơn mức sử dụng giới hạn", selected: false, badge: "Max" },
            ];
            caps.selected_thinking_level_id = "medium";
          }
        }
        if (p === "chatgpt" && caps) {
          caps.modes = [];
          caps.selected_mode_id = undefined;
          caps.available_models = [];
          caps.selected_model_id = undefined;
          caps.thinking_levels = [];
          caps.selected_thinking_level_id = undefined;
          if (caps.web_search === undefined) caps.web_search = true;
          if (caps.deep_research === undefined) caps.deep_research = false;
          if (caps.deep_thinking === undefined) caps.deep_thinking = false;
        }
        setCapabilitiesMap((prev) => {
          const updated = { ...prev, [p]: caps };
          saveStorage(CAPS_STORAGE_KEY, updated);
          return updated;
        });

        // Initialize selections if not set yet
        setSelectionsMap((prev) => {
          const existing = prev[p] || {};
          const isCopilot = p === "copilot";
          const isChatGPT = p === "chatgpt";
          const isDeepSeek = p === "deepseek";
          const isClaude = p === "claude";

          // Safe model for Claude (fallback to sonnet if opus/fable/default was stored)
          const rawModelId = existing.model_id || caps.selected_model_id || caps.available_models.find((m) => !m.disabled)?.id || "";
          const safeModelId = isClaude && (!rawModelId || rawModelId === "default" || rawModelId === "claude-opus-5.5" || rawModelId === "claude-fable-5.1")
            ? "claude-sonnet-5.5"
            : rawModelId;

          // Safe thinking for Claude (fallback to medium if "auto" was stored from prior bug)
          const defaultThinking = isClaude ? "medium" : "";
          const safeThinking = isClaude && (!existing.thinking_level_id || existing.thinking_level_id === "auto")
            ? (caps.selected_thinking_level_id || "medium")
            : (existing.thinking_level_id || caps.selected_thinking_level_id || caps.thinking_levels[0]?.id || defaultThinking);

          const updated = {
            ...prev,
            [p]: {
              model_id: (isDeepSeek || isCopilot || isChatGPT)
                ? ""
                : safeModelId,
              thinking_level_id: (isDeepSeek || isCopilot || isChatGPT)
                ? ""
                : safeThinking,
              mode_id: (isDeepSeek || isChatGPT)
                ? ""
                : existing.mode_id || caps.selected_mode_id || caps.modes[0]?.id || (isCopilot ? "auto" : ""),
              deep_thinking: (isDeepSeek || isChatGPT)
                ? (existing.deep_thinking !== undefined ? existing.deep_thinking : (caps.deep_thinking ?? false))
                : existing.deep_thinking,
              web_search: (isDeepSeek || isChatGPT)
                ? (existing.web_search !== undefined ? existing.web_search : (caps.web_search ?? true))
                : existing.web_search,
              deep_research: isChatGPT
                ? (existing.deep_research !== undefined ? existing.deep_research : (caps.deep_research ?? false))
                : existing.deep_research,
            },
          };
          saveStorage(SELECTIONS_STORAGE_KEY, updated);
          return updated;
        });

        return caps;
      } catch (err: any) {
        const msg = err?.message || String(err);
        setLastError(msg);
        return null;
      } finally {
        setLoadingProvider(null);
      }
    },
    []
  );

  // Auto-fetch current provider if missing
  useEffect(() => {
    const p = currentProviderId.toLowerCase();
    if (!capabilitiesMap[p] && loadingProvider !== p) {
      loadProviderCapabilities(p, false);
    }
  }, [currentProviderId, capabilitiesMap, loadingProvider, loadProviderCapabilities]);

  // Re-sync specific provider from live DOM
  const syncProvider = useCallback(
    async (provider: string = currentProviderId) => {
      return await loadProviderCapabilities(provider, true);
    },
    [currentProviderId, loadProviderCapabilities]
  );

  // Global sync across all providers
  const syncAll = useCallback(async () => {
    setIsSyncingAll(true);
    setLastError(null);
    try {
      const allCaps = await syncAllProviderCapabilities();
      setCapabilitiesMap((prev) => {
        const updated = { ...prev, ...allCaps };
        saveStorage(CAPS_STORAGE_KEY, updated);
        return updated;
      });
      return allCaps;
    } catch (err: any) {
      const msg = err?.message || String(err);
      setLastError(msg);
      return null;
    } finally {
      setIsSyncingAll(false);
    }
  }, []);

  // Update selected model, thinking level, or mode for a provider
  const updateSelection = useCallback(
    (provider: string, updates: Partial<ProviderSelectionConfig>) => {
      const p = provider.toLowerCase();
      setSelectionsMap((prev) => {
        const existing = prev[p] || {};
        const caps = capabilitiesMap[p];
        const isChatGPT = p === "chatgpt";
        const safeUpdates = isChatGPT ? { ...updates, model_id: "", thinking_level_id: "", mode_id: "" } : updates;
        const updated = {
          ...prev,
          [p]: { ...existing, ...safeUpdates },
        };
        saveStorage(SELECTIONS_STORAGE_KEY, updated);
        return updated;
      });
    },
    [capabilitiesMap]
  );

  // Active provider data computed
  const activeCaps = useMemo(() => {
    const p = currentProviderId.toLowerCase();
    return capabilitiesMap[p] || null;
  }, [capabilitiesMap, currentProviderId]);

  const activeSelection = useMemo(() => {
    const p = currentProviderId.toLowerCase();
    return selectionsMap[p] || {};
  }, [selectionsMap, currentProviderId]);

  const supportedDataTypes: SupportedDataTypes = useMemo(() => {
    if (activeCaps?.supported_data_types) {
      return activeCaps.supported_data_types;
    }
    return {
      text: true,
      image: true,
      file: true,
      audio: false,
      video: false,
      max_file_size_mb: 50,
      supported_mime_types: ["image/*", ".pdf", ".txt", ".csv", ".json"],
    };
  }, [activeCaps]);

  const voiceChatSupport: VoiceChatSupport = useMemo(() => {
    if (activeCaps?.voice_chat) {
      return activeCaps.voice_chat;
    }
    return {
      supported: true,
      mode: "backend_stt",
      details: "Voice chat available",
    };
  }, [activeCaps]);

  return {
    capabilitiesMap,
    selectionsMap,
    activeCaps,
    activeSelection,
    supportedDataTypes,
    voiceChatSupport,
    isLoading: loadingProvider === currentProviderId.toLowerCase(),
    loadingProvider,
    isSyncingAll,
    lastError,
    syncProvider,
    syncAll,
    updateSelection,
    loadProviderCapabilities,
  };
}
