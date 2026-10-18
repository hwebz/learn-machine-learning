import { ProviderLiveCapabilities } from "../types/capabilities";

export type AgentOption = { id: string; label: string; badge?: string; disabled?: boolean };

export function formatSyncTime(timestamp?: string): string | null {
  if (!timestamp) return null;
  try {
    return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return null;
  }
}

export function getProviderModels(
  providerId: string,
  caps?: ProviderLiveCapabilities,
  isDeepResearch?: boolean,
  defaultName?: string
): AgentOption[] {
  const p = providerId.toLowerCase();

  if (p === "deepseek" || p === "copilot" || p === "chatgpt" || p === "grok" || p === "mistral" || p === "meta") {
    return [];
  }

  if (p === "perplexity") {
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
    if (caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default")) {
      return caps.available_models.map((m) => ({
        ...m,
        disabled: m.id !== "auto",
        badge: m.id === "auto" ? "Auto" : (m.badge || "Pro"),
      }));
    }
    return perplexityFallbackModels;
  }

  if (p === "claude") {
    const base: AgentOption[] = caps?.available_models && caps.available_models.length > 0
      ? caps.available_models
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

  if (caps?.available_models && caps.available_models.length > 0) {
    return caps.available_models;
  }

  if (p === "gemini") {
    return [
      { id: "pro", label: "Gemini 3.1 Pro (Deep Reasoning)", badge: "Deep" },
      { id: "flash", label: "Gemini Flash (Nhanh)", badge: "Fast" },
      { id: "argon", label: "Gemini Argon", badge: "Pro" },
    ];
  }

  if (p === "qwen") {
    return [
      { id: "qwen-3.8-max", label: "Qwen 3.8 Max (Reasoning)", badge: "Max" },
      { id: "qwen-3.7-plus", label: "Qwen 3.7 Plus", badge: "Plus" },
      { id: "qwen-3.8-omni-flash", label: "Qwen 3.8 Omni-Flash", badge: "Omni" },
    ];
  }

  if (p === "zhipu") {
    return [
      { id: "glm-5.3", label: "GLM-5.3", badge: "GLM" },
      { id: "glm-4-plus", label: "GLM-4 Plus", badge: "GLM" },
    ];
  }

  if (p === "minimax") {
    return [
      { id: "m3", label: "M3 (Toàn diện)", badge: "M3" },
      { id: "m3.1-flash", label: "M3.1-Flash-Preview", badge: "Flash" },
      { id: "m2.7", label: "M2.7", badge: "2.7" },
      { id: "m2.7-highspeed", label: "M2.7 HighSpeed", badge: "HighSpeed" },
    ];
  }

  if (p === "kimi") {
    const kimiFallbackModels: AgentOption[] = [
      { id: "instant", label: "Instant (Phản hồi nhanh)", badge: "Fast" },
      { id: "k3", label: "K3 (Chat & Agent)", badge: "All-Rounder" },
      { id: "k2.8", label: "K2.8 (Preview · Well-rounded)", badge: "Preview" },
    ];
    const baseModels = caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default")
      ? caps.available_models
      : kimiFallbackModels;
    return baseModels.map((m) => {
      const isInstantDisabled = isDeepResearch && m.id === "instant";
      return {
        ...m,
        disabled: isInstantDisabled || m.disabled,
        badge: isInstantDisabled ? "Không hỗ trợ DR" : m.badge,
      };
    });
  }

  return [
    { id: "default", label: defaultName || "Mặc định" },
  ];
}

export function getProviderThinkingLevels(
  providerId: string,
  caps?: ProviderLiveCapabilities
): AgentOption[] {
  const p = providerId.toLowerCase();

  if (p === "deepseek" || p === "copilot" || p === "chatgpt" || p === "perplexity" || p === "grok") {
    return [];
  }

  if (caps?.thinking_levels && caps.thinking_levels.length > 0) {
    return caps.thinking_levels;
  }

  if (p === "meta") {
    return [
      { id: "thinking", label: "Thinking (Suy luận chuyên sâu)", badge: "Thinking" },
      { id: "instant", label: "Instant (Phản hồi tức thì)", badge: "Instant" },
    ];
  }

  if (p === "gemini") {
    return [
      { id: "high", label: "Cao (High Thinking)", badge: "High" },
      { id: "medium", label: "Vừa (Medium)", badge: "Med" },
      { id: "low", label: "Thấp (Low)", badge: "Low" },
    ];
  }

  if (p === "qwen") {
    return [
      { id: "auto", label: "Auto (Tự động cân bằng)", badge: "Auto" },
      { id: "thinking", label: "Thinking (Suy luận sâu)", badge: "Think" },
      { id: "fast", label: "Fast (Phản hồi nhanh)", badge: "Fast" },
    ];
  }

  if (p === "claude") {
    return [
      { id: "medium", label: "Trung bình (Medium - Khuyên dùng)", badge: "Med" },
      { id: "low", label: "Thấp (Low - Nhanh)", badge: "Low" },
      { id: "high", label: "Cao (High - Kỹ lưỡng)", badge: "High" },
      { id: "extra", label: "Rất cao (Extra)", badge: "Extra" },
      { id: "max", label: "Tối đa (Max)", badge: "Max" },
    ];
  }

  if (p === "kimi") {
    return [
      { id: "standard", label: "Standard (Tiêu chuẩn)", badge: "Standard" },
      { id: "high", label: "High (Chuyên sâu)", badge: "High" },
    ];
  }

  if (p === "mistral") {
    return [
      { id: "fast", label: "Fast (Nhanh)", badge: "Fast" },
      { id: "think", label: "Think (Suy luận)", badge: "Think" },
    ];
  }

  return [];
}

export function getProviderModes(
  providerId: string,
  caps?: ProviderLiveCapabilities
): AgentOption[] {
  const p = providerId.toLowerCase();

  if (
    p === "gemini" ||
    p === "qwen" ||
    p === "claude" ||
    p === "deepseek" ||
    p === "chatgpt" ||
    p === "perplexity" ||
    p === "kimi" ||
    p === "grok" ||
    p === "mistral" ||
    p === "meta"
  ) {
    return [];
  }

  if (caps?.modes && caps.modes.length > 0) {
    return caps.modes;
  }

  if (p === "copilot") {
    return [
      { id: "auto", label: "Auto (Cân bằng tốc độ & độ chính xác)", badge: "Auto" },
      { id: "quick", label: "Quick Response (Phản hồi nhanh)", badge: "Fast" },
      { id: "think_deeper", label: "Think Deeper (Suy luận đa bước chuyên sâu)", badge: "Think" },
      { id: "gpt_5_6_quick", label: "GPT > GPT-5.6 Sol Quick Response", badge: "GPT-5.6" },
      { id: "gpt_5_6_think", label: "GPT > GPT-5.6 Sol Think Deeper", badge: "GPT-5.6" },
    ];
  }

  return [];
}
