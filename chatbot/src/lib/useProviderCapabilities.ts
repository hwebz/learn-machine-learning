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
    if (cachedSelections["chatgpt"] && cachedCaps["chatgpt"]?.account_type === "free") {
      cachedSelections["chatgpt"].model_id = "none";
      cachedSelections["chatgpt"].thinking_level_id = "auto";
    }
    if (cachedSelections["copilot"]) {
      cachedSelections["copilot"].model_id = "auto";
      cachedSelections["copilot"].thinking_level_id = "auto";
      if (!cachedSelections["copilot"].mode_id) {
        cachedSelections["copilot"].mode_id = "auto";
      }
    }
    if (cachedCaps["gemini"]) {
      cachedCaps["gemini"].modes = [];
      cachedCaps["gemini"].selected_mode_id = null;
    }
    if (cachedSelections["gemini"]) {
      cachedSelections["gemini"].mode_id = "";
    }
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
        const caps = await fetchProviderCapabilities(p, forceSync);
        setCapabilitiesMap((prev) => {
          const updated = { ...prev, [p]: caps };
          saveStorage(CAPS_STORAGE_KEY, updated);
          return updated;
        });

        // Initialize selections if not set yet
        setSelectionsMap((prev) => {
          const existing = prev[p] || {};
          const isCopilot = p === "copilot";
          const isFree = p === "chatgpt" && caps.account_type === "free";
          const updated = {
            ...prev,
            [p]: {
              model_id: isCopilot
                ? "auto"
                : isFree
                ? "none"
                : (existing.model_id || caps.selected_model_id || caps.available_models[0]?.id || "none"),
              thinking_level_id: isCopilot
                ? "auto"
                : (
                    existing.thinking_level_id ||
                    caps.selected_thinking_level_id ||
                    caps.thinking_levels[0]?.id ||
                    "auto"
                  ),
              mode_id: existing.mode_id || caps.selected_mode_id || caps.modes[0]?.id || (isCopilot ? "auto" : (caps.modes && caps.modes.length > 0 ? "standard" : "")),
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
        const isFree = p === "chatgpt" && caps?.account_type === "free";
        const safeUpdates = isFree ? { ...updates, model_id: "none" } : updates;
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
