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
      if (cachedCaps["gemini"].deep_research === undefined) cachedCaps["gemini"].deep_research = false;
    }
    if (cachedSelections["gemini"]) {
      cachedSelections["gemini"].mode_id = "";
      if (cachedSelections["gemini"].deep_research === undefined) cachedSelections["gemini"].deep_research = false;
    }
    if (cachedCaps["grok"]) {
      cachedCaps["grok"].modes = [];
      cachedCaps["grok"].selected_mode_id = undefined;
      cachedCaps["grok"].available_models = [];
      cachedCaps["grok"].selected_model_id = undefined;
      cachedCaps["grok"].thinking_levels = [];
      cachedCaps["grok"].selected_thinking_level_id = undefined;
      cachedCaps["grok"].account_type = "free";
    }
    if (cachedSelections["grok"]) {
      cachedSelections["grok"].model_id = "";
      cachedSelections["grok"].thinking_level_id = "";
      cachedSelections["grok"].mode_id = "";
    }
    if (cachedCaps["mistral"]) {
      cachedCaps["mistral"].modes = [];
      cachedCaps["mistral"].selected_mode_id = undefined;
      cachedCaps["mistral"].available_models = [];
      cachedCaps["mistral"].selected_model_id = undefined;
      const hasBadMistralThinking =
        !cachedCaps["mistral"].thinking_levels ||
        cachedCaps["mistral"].thinking_levels.length === 0 ||
        cachedCaps["mistral"].thinking_levels.some((t) => t.id === "auto");
      if (hasBadMistralThinking) {
        cachedCaps["mistral"].thinking_levels = [
          { id: "fast", label: "Fast (Nhanh)", description: "Get answers fast — Phản hồi nhanh cho câu hỏi thường ngày", selected: true, disabled: false, badge: "Fast" },
          { id: "think", label: "Think (Suy luận)", description: "Handle complex tasks — Suy luận sâu cho tác vụ phức tạp", selected: false, disabled: false, badge: "Think" },
        ];
        cachedCaps["mistral"].selected_thinking_level_id = "fast";
      }
      if (cachedCaps["mistral"].deep_research === undefined) cachedCaps["mistral"].deep_research = false;
      if (cachedCaps["mistral"].web_search === undefined) cachedCaps["mistral"].web_search = true;
    }
    if (cachedSelections["mistral"]) {
      cachedSelections["mistral"].model_id = "";
      cachedSelections["mistral"].mode_id = "";
      if (!cachedSelections["mistral"].thinking_level_id || cachedSelections["mistral"].thinking_level_id === "auto") {
        cachedSelections["mistral"].thinking_level_id = "fast";
      }
      if (cachedSelections["mistral"].deep_research === undefined) cachedSelections["mistral"].deep_research = false;
      if (cachedSelections["mistral"].web_search === undefined) cachedSelections["mistral"].web_search = true;
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
    if (cachedCaps["perplexity"]) {
      cachedCaps["perplexity"].modes = [];
      cachedCaps["perplexity"].selected_mode_id = undefined;
      cachedCaps["perplexity"].thinking_levels = [];
      cachedCaps["perplexity"].selected_thinking_level_id = undefined;
      cachedCaps["perplexity"].selected_model_id = "auto";
      cachedCaps["perplexity"].deep_thinking = false;
      cachedCaps["perplexity"].web_search = true;
      const hasBadPerplexityModels =
        !cachedCaps["perplexity"].available_models ||
        cachedCaps["perplexity"].available_models.length <= 1 ||
        cachedCaps["perplexity"].available_models.some((m) => m.id === "default");
      if (hasBadPerplexityModels) {
        cachedCaps["perplexity"].available_models = [
          { id: "auto", label: "Auto (Tự động)", description: "Mô hình mặc định của Perplexity (Tối ưu tự động theo ngữ cảnh)", selected: true, disabled: false, badge: "Auto" },
          { id: "gpt-6-1-sol", label: "GPT-6.1 Sol", description: "Mô hình GPT-6.1 Sol trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Pro" },
          { id: "gpt-6-astra", label: "GPT-6 Astra", description: "Mô hình GPT-6 Astra trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Max" },
          { id: "gemini-4-argon", label: "Gemini 4 Argon", description: "Mô hình Gemini 4 Argon trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "New" },
          { id: "gemini-3-8-flash", label: "Gemini 3.8 Flash", description: "Mô hình Gemini 3.8 Flash trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Pro" },
          { id: "claude-sonnet-5-5", label: "Claude Sonnet 5.5", description: "Mô hình Claude Sonnet 5.5 trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Pro" },
          { id: "claude-opus-5-5", label: "Claude Opus 5.5", description: "Mô hình Claude Opus 5.5 trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Max" },
          { id: "claude-fable-5-1", label: "Claude Fable 5.1", description: "Mô hình Claude Fable 5.1 trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Max" },
          { id: "kimi-k3", label: "Kimi K3", description: "Mô hình Kimi K3 trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Pro" },
          { id: "glm-5-3", label: "GLM 5.3", description: "Mô hình GLM 5.3 trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Pro" },
          { id: "grok-4-7", label: "Grok 4.7", description: "Mô hình Grok 4.7 trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Pro" },
          { id: "nemotron-3-ultra", label: "Nemotron 3 Ultra", description: "Mô hình Nemotron 3 Ultra trên Perplexity (Yêu cầu Pro)", selected: false, disabled: true, badge: "Pro" },
        ];
      }
    }
    if (cachedSelections["perplexity"]) {
      cachedSelections["perplexity"].model_id = "auto";
      cachedSelections["perplexity"].thinking_level_id = "";
      cachedSelections["perplexity"].mode_id = "";
      cachedSelections["perplexity"].deep_thinking = false;
      cachedSelections["perplexity"].web_search = true;
    }
    if (cachedCaps["kimi"]) {
      cachedCaps["kimi"].modes = [];
      cachedCaps["kimi"].selected_mode_id = undefined;
      const hasBadKimiModels =
        !cachedCaps["kimi"].available_models ||
        cachedCaps["kimi"].available_models.length === 0 ||
        cachedCaps["kimi"].available_models.some((m) => m.id === "default");
      if (hasBadKimiModels) {
        cachedCaps["kimi"].available_models = [
          { id: "instant", label: "Instant", description: "Fast chat, quick replies (Phản hồi nhanh)", selected: true, disabled: false, badge: "Instant" },
          { id: "k3", label: "K3", description: "Chat & Agent, flagship all-rounder (Toàn diện, suy luận mạnh)", selected: false, disabled: false, badge: "K3" },
          { id: "k2.8", label: "K2.8", description: "Preview · Well-rounded and efficient for everyday tasks", selected: false, disabled: false, badge: "Preview" },
        ];
        cachedCaps["kimi"].selected_model_id = "instant";
      }
      const hasBadKimiThinking =
        !cachedCaps["kimi"].thinking_levels ||
        cachedCaps["kimi"].thinking_levels.length === 0 ||
        cachedCaps["kimi"].thinking_levels.some((t) => t.id === "auto");
      if (hasBadKimiThinking) {
        cachedCaps["kimi"].thinking_levels = [
          { id: "standard", label: "Standard", description: "Suy luận tiêu chuẩn, phản hồi cân bằng", selected: false, disabled: false, badge: "Standard" },
          { id: "high", label: "High", description: "Suy luận chuyên sâu cao nhất", selected: true, disabled: false, badge: "High" },
        ];
        cachedCaps["kimi"].selected_thinking_level_id = "high";
      }
      if (cachedCaps["kimi"].deep_research === undefined) cachedCaps["kimi"].deep_research = false;
      if (cachedCaps["kimi"].web_search === undefined) cachedCaps["kimi"].web_search = true;
    }
    if (cachedSelections["kimi"]) {
      cachedSelections["kimi"].mode_id = "";
      if (cachedSelections["kimi"].deep_research === undefined) cachedSelections["kimi"].deep_research = false;
      if (cachedSelections["kimi"].deep_research) {
        if (!cachedSelections["kimi"].model_id || cachedSelections["kimi"].model_id === "instant" || cachedSelections["kimi"].model_id === "default") {
          cachedSelections["kimi"].model_id = "k3";
        }
      } else {
        if (!cachedSelections["kimi"].model_id || cachedSelections["kimi"].model_id === "default") {
          cachedSelections["kimi"].model_id = "instant";
        }
      }
      if (!cachedSelections["kimi"].thinking_level_id || cachedSelections["kimi"].thinking_level_id === "auto") {
        cachedSelections["kimi"].thinking_level_id = "high";
      }
    }
    if (cachedCaps["qwen"]) {
      if (cachedCaps["qwen"].deep_research === undefined) cachedCaps["qwen"].deep_research = false;
      if (cachedCaps["qwen"].web_search === undefined) cachedCaps["qwen"].web_search = true;
      if (!cachedCaps["qwen"].research_mode) cachedCaps["qwen"].research_mode = "normal";
    }
    if (cachedSelections["qwen"]) {
      cachedSelections["qwen"].mode_id = "";
      if (cachedSelections["qwen"].deep_research === undefined) cachedSelections["qwen"].deep_research = false;
      if (cachedSelections["qwen"].web_search === undefined) cachedSelections["qwen"].web_search = true;
      if (!cachedSelections["qwen"].research_mode) cachedSelections["qwen"].research_mode = "normal";
      if (cachedSelections["qwen"].deep_research) {
        cachedSelections["qwen"].thinking_level_id = "auto";
      }
    }
    if (cachedCaps["zhipu"]) {
      cachedCaps["zhipu"].modes = [];
      cachedCaps["zhipu"].selected_mode_id = undefined;
      cachedCaps["zhipu"].thinking_levels = [];
      cachedCaps["zhipu"].selected_thinking_level_id = undefined;
      cachedCaps["zhipu"].deep_research = false;
      cachedCaps["zhipu"].deep_thinking = false;
      cachedCaps["zhipu"].web_search = false;
      const hasBadZhipuModels =
        !cachedCaps["zhipu"].available_models ||
        cachedCaps["zhipu"].available_models.length === 0 ||
        cachedCaps["zhipu"].available_models.some((m) => m.id === "default" || m.id === "glm-5");
      if (hasBadZhipuModels) {
        cachedCaps["zhipu"].available_models = [
          { id: "glm-5.3-flash", label: "GLM-5.3-Flash", description: "Lightweight flagship model, instant response (Mô hình cờ đầu gọn nhẹ, phản hồi tức thì)", selected: true, badge: "Flash" },
          { id: "glm-5.3", label: "GLM-5.3", description: "Flagship model, excels at coding and long-horizon tasks (Mô hình cờ đầu, lập trình & tác vụ chuyên sâu)", selected: false, badge: "Flagship" },
          { id: "glm-5.2", label: "GLM-5.2", description: "Previous flagship model (Mô hình cờ đầu thế hệ trước)", selected: false, badge: "5.2" },
          { id: "glm-4-plus", label: "GLM-4-Plus", description: "Mô hình hiệu năng cao toàn diện cho tác vụ phức tạp", selected: false, badge: "Plus" },
          { id: "glm-4-air", label: "GLM-4-Air", description: "Cân bằng tốc độ xử lý nhanh và độ chính xác cao", selected: false, badge: "Air" },
        ];
        cachedCaps["zhipu"].selected_model_id = "glm-5.3-flash";
      }
    }
    if (cachedSelections["zhipu"]) {
      cachedSelections["zhipu"].thinking_level_id = "";
      cachedSelections["zhipu"].mode_id = "";
      cachedSelections["zhipu"].deep_research = false;
      cachedSelections["zhipu"].deep_thinking = false;
      cachedSelections["zhipu"].web_search = false;
      if (!cachedSelections["zhipu"].model_id || cachedSelections["zhipu"].model_id === "default" || cachedSelections["zhipu"].model_id === "glm-5") {
        cachedSelections["zhipu"].model_id = "glm-5.3-flash";
      }
    }
    if (cachedCaps["minimax"]) {
      cachedCaps["minimax"].modes = [];
      cachedCaps["minimax"].selected_mode_id = undefined;
      cachedCaps["minimax"].thinking_levels = [];
      cachedCaps["minimax"].selected_thinking_level_id = undefined;
      cachedCaps["minimax"].deep_thinking = false;
      cachedCaps["minimax"].web_search = false;
      if (cachedCaps["minimax"].deep_research === undefined) cachedCaps["minimax"].deep_research = false;
      const hasBadMinimaxModels =
        !cachedCaps["minimax"].available_models ||
        cachedCaps["minimax"].available_models.length === 0 ||
        cachedCaps["minimax"].available_models.some((m) => m.id === "default");
      if (hasBadMinimaxModels) {
        cachedCaps["minimax"].available_models = [
          { id: "m3", label: "M3", description: "Mô hình cờ đầu toàn diện của MiniMax, xử lý tác vụ phức tạp", selected: true, badge: "M3" },
          { id: "m3.1-flash", label: "M3.1-Flash-Preview", description: "Mô hình tốc độ cao, phản hồi tức thì cho tác vụ nhanh", selected: false, badge: "Flash" },
          { id: "m2.7", label: "M2.7", description: "Mô hình tiêu chuẩn ổn định", selected: false, badge: "2.7" },
          { id: "m2.7-highspeed", label: "M2.7 HighSpeed", description: "Phiên bản tốc độ cao", selected: false, badge: "HighSpeed" },
        ];
        cachedCaps["minimax"].selected_model_id = "m3";
      }
    }
    if (cachedSelections["minimax"]) {
      cachedSelections["minimax"].thinking_level_id = "";
      cachedSelections["minimax"].mode_id = "";
      cachedSelections["minimax"].deep_thinking = false;
      cachedSelections["minimax"].web_search = false;
      if (cachedSelections["minimax"].deep_research === undefined) {
        cachedSelections["minimax"].deep_research = false;
      }
      if (!cachedSelections["minimax"].model_id || cachedSelections["minimax"].model_id === "default") {
        cachedSelections["minimax"].model_id = "m3";
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
        if (p === "perplexity" && caps) {
          caps.modes = [];
          caps.selected_mode_id = undefined;
          caps.thinking_levels = [];
          caps.selected_thinking_level_id = undefined;
          caps.selected_model_id = "auto";
          caps.deep_thinking = false;
          caps.web_search = true;
        }
        if (p === "kimi" && caps) {
          caps.modes = [];
          caps.selected_mode_id = undefined;
          const hasBadKimiModels =
            !caps.available_models ||
            caps.available_models.length === 0 ||
            caps.available_models.some((m) => m.id === "default");
          if (hasBadKimiModels) {
            caps.available_models = [
              { id: "instant", label: "Instant", description: "Fast chat, quick replies (Phản hồi nhanh)", selected: true, disabled: false, badge: "Instant" },
              { id: "k3", label: "K3", description: "Chat & Agent, flagship all-rounder (Toàn diện, suy luận mạnh)", selected: false, disabled: false, badge: "K3" },
              { id: "k2.8", label: "K2.8", description: "Preview · Well-rounded and efficient for everyday tasks", selected: false, disabled: false, badge: "Preview" },
            ];
            caps.selected_model_id = "instant";
          }
          const hasBadKimiThinking =
            !caps.thinking_levels ||
            caps.thinking_levels.length === 0 ||
            caps.thinking_levels.some((t) => t.id === "auto");
          if (hasBadKimiThinking) {
            caps.thinking_levels = [
              { id: "standard", label: "Standard", description: "Suy luận tiêu chuẩn, phản hồi cân bằng", selected: false, disabled: false, badge: "Standard" },
              { id: "high", label: "High", description: "Suy luận chuyên sâu cao nhất", selected: true, disabled: false, badge: "High" },
            ];
            caps.selected_thinking_level_id = "high";
          }
          if (caps.deep_research === undefined) caps.deep_research = false;
          if (caps.web_search === undefined) caps.web_search = true;
        }
        if (p === "qwen" && caps) {
          if (caps.web_search === undefined) caps.web_search = true;
          if (caps.deep_research === undefined) caps.deep_research = false;
          if (!caps.research_mode) caps.research_mode = "normal";
        }
        if (p === "gemini" && caps) {
          if (caps.deep_research === undefined) caps.deep_research = false;
        }
        if (p === "grok" && caps) {
          caps.modes = [];
          caps.selected_mode_id = undefined;
          caps.available_models = [];
          caps.selected_model_id = undefined;
          caps.thinking_levels = [];
          caps.selected_thinking_level_id = undefined;
          caps.account_type = "free";
        }
        if (p === "mistral" && caps) {
          caps.modes = [];
          caps.selected_mode_id = undefined;
          caps.available_models = [];
          caps.selected_model_id = undefined;
          const hasBadMistralThinking =
            !caps.thinking_levels ||
            caps.thinking_levels.length === 0 ||
            caps.thinking_levels.some((t) => t.id === "auto");
          if (hasBadMistralThinking) {
            caps.thinking_levels = [
              { id: "fast", label: "Fast (Nhanh)", description: "Get answers fast — Phản hồi nhanh cho câu hỏi thường ngày", selected: true, disabled: false, badge: "Fast" },
              { id: "think", label: "Think (Suy luận)", description: "Handle complex tasks — Suy luận sâu cho tác vụ phức tạp", selected: false, disabled: false, badge: "Think" },
            ];
            caps.selected_thinking_level_id = "fast";
          }
          if (caps.deep_research === undefined) caps.deep_research = false;
          if (caps.web_search === undefined) caps.web_search = true;
        }
        if (p === "zhipu" && caps) {
          caps.modes = [];
          caps.selected_mode_id = undefined;
          caps.thinking_levels = [];
          caps.selected_thinking_level_id = undefined;
          caps.deep_research = false;
          caps.deep_thinking = false;
          caps.web_search = false;
          const hasBadZhipuModels =
            !caps.available_models ||
            caps.available_models.length === 0 ||
            caps.available_models.some((m) => m.id === "default" || m.id === "glm-5");
          if (hasBadZhipuModels) {
            caps.available_models = [
              { id: "glm-5.3-flash", label: "GLM-5.3-Flash", description: "Lightweight flagship model, instant response (Mô hình cờ đầu gọn nhẹ, phản hồi tức thì)", selected: true, badge: "Flash" },
              { id: "glm-5.3", label: "GLM-5.3", description: "Flagship model, excels at coding and long-horizon tasks (Mô hình cờ đầu, lập trình & tác vụ chuyên sâu)", selected: false, badge: "Flagship" },
              { id: "glm-5.2", label: "GLM-5.2", description: "Previous flagship model (Mô hình cờ đầu thế hệ trước)", selected: false, badge: "5.2" },
              { id: "glm-4-plus", label: "GLM-4-Plus", description: "Mô hình hiệu năng cao toàn diện cho tác vụ phức tạp", selected: false, badge: "Plus" },
              { id: "glm-4-air", label: "GLM-4-Air", description: "Cân bằng tốc độ xử lý nhanh và độ chính xác cao", selected: false, badge: "Air" },
            ];
            caps.selected_model_id = "glm-5.3-flash";
          }
        }
        if (p === "minimax" && caps) {
          caps.modes = [];
          caps.selected_mode_id = undefined;
          caps.thinking_levels = [];
          caps.selected_thinking_level_id = undefined;
          caps.deep_thinking = false;
          caps.web_search = false;
          const hasBadMinimaxModels =
            !caps.available_models ||
            caps.available_models.length === 0 ||
            caps.available_models.some((m) => m.id === "default");
          if (hasBadMinimaxModels) {
            caps.available_models = [
              { id: "m3", label: "M3", description: "Mô hình cờ đầu toàn diện của MiniMax, xử lý tác vụ phức tạp", selected: true, badge: "M3" },
              { id: "m3.1-flash", label: "M3.1-Flash-Preview", description: "Mô hình tốc độ cao, phản hồi tức thì cho tác vụ nhanh", selected: false, badge: "Flash" },
              { id: "m2.7", label: "M2.7", description: "Mô hình tiêu chuẩn ổn định", selected: false, badge: "2.7" },
              { id: "m2.7-highspeed", label: "M2.7 HighSpeed", description: "Phiên bản tốc độ cao", selected: false, badge: "HighSpeed" },
            ];
            caps.selected_model_id = "m3";
          }
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
          const isPerplexity = p === "perplexity";
          const isKimi = p === "kimi";
          const isQwen = p === "qwen";
          const isGemini = p === "gemini";
          const isGrok = p === "grok";
          const isMistral = p === "mistral";
          const isZhipu = p === "zhipu";
          const isMinimax = p === "minimax";

          // Safe model for Claude & Kimi
          const isKimiDeepResearch = isKimi && (existing.deep_research !== undefined ? existing.deep_research : (caps.deep_research ?? false));
          const isQwenDeepResearch = isQwen && (existing.deep_research !== undefined ? existing.deep_research : (caps.deep_research ?? false));
          const rawModelId = existing.model_id || caps.selected_model_id || caps.available_models.find((m) => !m.disabled)?.id || "";
          const safeModelId = isClaude && (!rawModelId || rawModelId === "default" || rawModelId === "claude-opus-5.5" || rawModelId === "claude-fable-5.1")
            ? "claude-sonnet-5.5"
            : isKimi && isKimiDeepResearch && (!rawModelId || rawModelId === "instant" || rawModelId === "default")
            ? "k3"
            : isKimi && (!rawModelId || rawModelId === "default")
            ? "instant"
            : isZhipu && (!rawModelId || rawModelId === "default" || rawModelId === "glm-5")
            ? "glm-5.3-flash"
            : isMinimax && (!rawModelId || rawModelId === "default")
            ? "m3"
            : rawModelId;

          // Safe thinking for Claude, Kimi & Qwen
          const defaultThinking = isClaude ? "medium" : isKimi ? "high" : isQwen ? "auto" : "";
          const safeThinking = isClaude && (!existing.thinking_level_id || existing.thinking_level_id === "auto")
            ? (caps.selected_thinking_level_id || "medium")
            : isQwen && isQwenDeepResearch
            ? "auto"
            : isKimi && (!existing.thinking_level_id || existing.thinking_level_id === "auto")
            ? (caps.selected_thinking_level_id || "high")
            : (existing.thinking_level_id || caps.selected_thinking_level_id || caps.thinking_levels[0]?.id || defaultThinking);

          const updated = {
            ...prev,
            [p]: {
              model_id: isPerplexity
                ? "auto"
                : (isDeepSeek || isCopilot || isChatGPT || isGrok || isMistral)
                ? ""
                : safeModelId,
              thinking_level_id: (isDeepSeek || isCopilot || isChatGPT || isPerplexity || isGrok || isZhipu || isMinimax)
                ? ""
                : isMistral
                ? (existing.thinking_level_id || caps.selected_thinking_level_id || "fast")
                : safeThinking,
              mode_id: (isDeepSeek || isChatGPT || isPerplexity || isKimi || isQwen || isGemini || isGrok || isMistral || isZhipu || isMinimax)
                ? ""
                : existing.mode_id || caps.selected_mode_id || caps.modes[0]?.id || (isCopilot ? "auto" : ""),
              deep_thinking: (isPerplexity || isZhipu || isMinimax)
                ? false
                : (isDeepSeek || isChatGPT)
                ? (existing.deep_thinking !== undefined ? existing.deep_thinking : (caps.deep_thinking ?? false))
                : existing.deep_thinking,
              web_search: isPerplexity || isKimi
                ? true
                : (isZhipu || isMinimax)
                ? false
                : (isDeepSeek || isChatGPT || isQwen)
                ? (existing.web_search !== undefined ? existing.web_search : (caps.web_search ?? true))
                : existing.web_search,
              deep_research: isZhipu
                ? false
                : (isChatGPT || isKimi || isQwen || isGemini || isMistral || isMinimax)
                ? (existing.deep_research !== undefined ? existing.deep_research : (caps.deep_research ?? false))
                : existing.deep_research,
              research_mode: isQwen
                ? (existing.research_mode || caps.research_mode || "normal")
                : existing.research_mode,
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
        const isChatGPT = p === "chatgpt";
        const isPerplexity = p === "perplexity";
        const isKimi = p === "kimi";
        let safeUpdates = updates;
        if (isChatGPT) {
          safeUpdates = { ...updates, model_id: "", thinking_level_id: "", mode_id: "" };
        } else if (isPerplexity) {
          safeUpdates = { ...updates, model_id: "auto", thinking_level_id: "", mode_id: "", deep_thinking: false, web_search: true };
        } else if (isKimi) {
          safeUpdates = { ...updates, mode_id: "" };
          const willBeDeepResearch = updates.deep_research !== undefined ? updates.deep_research : existing.deep_research;
          if (willBeDeepResearch) {
            const currentOrUpdatedModel = updates.model_id !== undefined ? updates.model_id : existing.model_id;
            if (!currentOrUpdatedModel || currentOrUpdatedModel === "instant" || currentOrUpdatedModel === "default") {
              safeUpdates.model_id = "k3";
            }
          }
        } else if (p === "qwen") {
          safeUpdates = { ...updates, mode_id: "" };
          const willBeDeepResearch = updates.deep_research !== undefined ? updates.deep_research : existing.deep_research;
          if (willBeDeepResearch) {
            safeUpdates.thinking_level_id = "auto";
            if (!existing.research_mode && !updates.research_mode) {
              safeUpdates.research_mode = "normal";
            }
          }
        } else if (p === "gemini") {
          safeUpdates = { ...updates, mode_id: "" };
        } else if (p === "grok") {
          safeUpdates = { ...updates, model_id: "", thinking_level_id: "", mode_id: "" };
        } else if (p === "zhipu") {
          safeUpdates = { ...updates, thinking_level_id: "", mode_id: "", deep_thinking: false, deep_research: false, web_search: false };
        } else if (p === "minimax") {
          safeUpdates = { ...updates, thinking_level_id: "", mode_id: "", deep_thinking: false, web_search: false };
        }
        const updated = {
          ...prev,
          [p]: { ...existing, ...safeUpdates },
        };
        saveStorage(SELECTIONS_STORAGE_KEY, updated);
        return updated;
      });
    },
    []
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
