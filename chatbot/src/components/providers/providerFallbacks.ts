import { OptionItem, ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";

export const claudeFallbackModels: OptionItem[] = [
  { id: "claude-sonnet-5.5", label: "Sonnet 5.5", description: "Cân bằng hoàn hảo giữa trí tuệ và tốc độ", selected: true, badge: "Sonnet", disabled: false },
  { id: "claude-haiku-5.5", label: "Haiku 5.5", description: "Phản hồi nhanh nhất cho tác vụ ngắn gọn", selected: false, badge: "Haiku", disabled: false },
  { id: "claude-opus-5.5", label: "Opus 5.5", description: "Dành cho tài khoản Pro (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
  { id: "claude-fable-5.1", label: "Fable 5.1", description: "Dành cho các thử thách khó khăn nhất (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
];

export const perplexityFallbackModels: OptionItem[] = [
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

export const kimiFallbackModels: OptionItem[] = [
  { id: "instant", label: "Instant", description: "Fast chat, quick replies (Phản hồi nhanh)", selected: true, disabled: false, badge: "Instant" },
  { id: "k3", label: "K3", description: "Chat & Agent, flagship all-rounder (Toàn diện, suy luận mạnh)", selected: false, disabled: false, badge: "K3" },
  { id: "k2.8", label: "K2.8", description: "Preview · Well-rounded and efficient for everyday tasks", selected: false, disabled: false, badge: "Preview" },
];

export const kimiFallbackThinking: OptionItem[] = [
  { id: "standard", label: "Standard", description: "Suy luận tiêu chuẩn, phản hồi cân bằng", selected: false, disabled: false, badge: "Standard" },
  { id: "high", label: "High", description: "Suy luận chuyên sâu cao nhất", selected: true, disabled: false, badge: "High" },
];

export const geminiFallbackModels: OptionItem[] = [
  { id: "gemini-3.8-flash", label: "3.8 Flash", description: "Trợ giúp toàn diện", selected: true, badge: "Flash", disabled: false },
  { id: "gemini-3.5-flash-lite", label: "3.5 Flash-Lite", description: "Câu trả lời nhanh nhất", selected: false, badge: "Lite", disabled: false },
  { id: "gemini-3.1-pro", label: "3.1 Pro", description: "Suy luận nâng cao", selected: false, badge: "Pro", disabled: false },
  { id: "gemini-4-argon", label: "4 Argon", description: "Nhiệm vụ phức tạp", selected: false, badge: "Argon", disabled: false },
];

export const qwenFallbackModels: OptionItem[] = [
  { id: "qwen-3.8-max", label: "Qwen3.8-Max (Flagship)", description: "Mô hình cờ đầu thế hệ mới nhất", selected: true, badge: "Max", disabled: false },
  { id: "qwen-3.7-plus", label: "Qwen3.7-Plus (High Performance)", description: "Mô hình hiệu năng cao", selected: false, badge: "Plus", disabled: false },
  { id: "qwen-3.8-omni-flash", label: "Qwen3.8-Omni-Flash (Multimodal)", description: "Mô hình đa phương tiện tự nhiên", selected: false, badge: "Omni", disabled: false },
];

export const minimaxFallbackModels: OptionItem[] = [
  { id: "m3", label: "M3", description: "Mô hình cờ đầu toàn diện của MiniMax, xử lý tác vụ phức tạp", selected: true, badge: "M3", disabled: false },
  { id: "m3.1-flash", label: "M3.1-Flash-Preview", description: "Mô hình tốc độ cao, phản hồi tức thì cho tác vụ nhanh", selected: false, badge: "Flash", disabled: false },
  { id: "m2.7", label: "M2.7", description: "Mô hình tiêu chuẩn ổn định", selected: false, badge: "2.7", disabled: false },
  { id: "m2.7-highspeed", label: "M2.7 HighSpeed", description: "Phiên bản tốc độ cao", selected: false, badge: "HighSpeed", disabled: false },
];

export const zhipuFallbackModels: OptionItem[] = [
  { id: "glm-5.3-flash", label: "GLM-5.3-Flash", description: "Lightweight flagship model, instant response (Mô hình cờ đầu gọn nhẹ, phản hồi tức thì)", selected: true, badge: "Flash", disabled: false },
  { id: "glm-5.3", label: "GLM-5.3", description: "Flagship model, excels at coding and long-horizon tasks (Mô hình cờ đầu, lập trình & tác vụ chuyên sâu)", selected: false, badge: "Flagship", disabled: false },
  { id: "glm-5.2", label: "GLM-5.2", description: "Previous flagship model (Mô hình cờ đầu thế hệ trước)", selected: false, badge: "5.2", disabled: false },
  { id: "glm-4-plus", label: "GLM-4-Plus", description: "Mô hình hiệu năng cao toàn diện cho tác vụ phức tạp", selected: false, badge: "Plus", disabled: false },
  { id: "glm-4-air", label: "GLM-4-Air", description: "Cân bằng tốc độ xử lý nhanh và độ chính xác cao", selected: false, badge: "Air", disabled: false },
];

export const claudeFallbackThinking: OptionItem[] = [
  { id: "medium", label: "Medium (Recommended)", description: "Khuyên dùng - Cân bằng độ sâu và giới hạn sử dụng", selected: true, badge: "Med" },
  { id: "low", label: "Low", description: "Thấp - Phản hồi nhanh và tiết kiệm giới hạn", selected: false, badge: "Low" },
  { id: "high", label: "High", description: "Cao - Phân tích đa bước kỹ lưỡng cho bài toán hóc búa", selected: false, badge: "High" },
  { id: "extra", label: "Extra", description: "Rất cao - Suy luận chuyên sâu cho nghiên cứu phức tạp", selected: false, badge: "Extra" },
  { id: "max", label: "Max", description: "Tối đa - 8x hoặc nhiều hơn mức sử dụng giới hạn", selected: false, badge: "Max" },
];

export const geminiFallbackThinking: OptionItem[] = [
  { id: "low", label: "Thấp (Nhanh chóng & hiệu quả)", description: "Nhanh chóng và hiệu quả", selected: true, badge: "Low" },
  { id: "medium", label: "Trung bình (Độ sâu cân bằng)", description: "Độ sâu cân bằng", selected: false, badge: "Med" },
  { id: "high", label: "Cao (Cực kỳ kỹ lưỡng)", description: "Cực kỳ kỹ lưỡng", selected: false, badge: "High" },
];

export const qwenFallbackThinking: OptionItem[] = [
  { id: "auto", label: "Auto (Tự động cân bằng)", description: "Tự động điều chỉnh mức độ suy luận", selected: true, badge: "Auto" },
  { id: "thinking", label: "Thinking (Suy luận sâu đa bước)", description: "Kích hoạt chuỗi tư duy mở rộng", selected: false, badge: "Think" },
  { id: "fast", label: "Fast (Phản hồi nhanh)", description: "Bỏ qua tư duy đa bước", selected: false, badge: "Fast" },
];

export const mistralFallbackThinking: OptionItem[] = [
  { id: "fast", label: "Fast (Nhanh)", description: "Get answers fast — Phản hồi nhanh cho câu hỏi thường ngày", selected: true, badge: "Fast" },
  { id: "think", label: "Think (Suy luận)", description: "Handle complex tasks — Suy luận sâu cho tác vụ phức tạp", selected: false, badge: "Think" },
];

export const copilotFallbackModes: OptionItem[] = [
  { id: "auto", label: "Auto", description: "Tự động cân bằng giữa tốc độ và độ chính xác (Mặc định)", selected: true, badge: "Auto" },
  { id: "quick", label: "Quick Response", description: "Ưu tiên tốc độ phản hồi nhanh cho các câu hỏi ngắn gọn", selected: false, badge: "Fast" },
  { id: "think_deeper", label: "Think Deeper", description: "Kích hoạt mô hình suy luận đa bước chuyên sâu cho bài toán phức tạp", selected: false, badge: "Think" },
  { id: "gpt_5_6_quick", label: "GPT > GPT-5.6 Sol Quick Response", description: "Mô hình GPT-5.6 Sol tối ưu tốc độ phản hồi", selected: false, badge: "GPT-5.6" },
  { id: "gpt_5_6_think", label: "GPT > GPT-5.6 Sol Think Deeper", description: "Mô hình GPT-5.6 Sol với khả năng suy luận chuyên sâu", selected: false, badge: "GPT-5.6" },
];

/**
 * Resolves available models for a given provider, taking into account live DOM capabilities and deep research compatibility.
 */
export function resolveProviderModels(
  providerId: string,
  caps?: ProviderLiveCapabilities,
  isDeepResearch?: boolean
): OptionItem[] {
  if (["chatgpt", "copilot", "deepseek", "grok", "mistral", "meta"].includes(providerId)) {
    return [];
  }

  if (providerId === "claude") {
    if (caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default")) {
      return caps.available_models.map((m) => {
        const isUpgrade = m.id === "claude-opus-5.5" || m.id === "claude-fable-5.1" || m.disabled || m.metadata?.upgrade;
        return {
          ...m,
          disabled: isUpgrade,
          badge: isUpgrade ? "Upgrade" : m.badge,
        };
      });
    }
    return claudeFallbackModels;
  }

  if (providerId === "perplexity") {
    if (caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default")) {
      return caps.available_models.map((m) => ({
        ...m,
        disabled: m.id !== "auto",
        badge: m.id === "auto" ? "Auto" : (m.badge || "Pro"),
      }));
    }
    return perplexityFallbackModels;
  }

  if (providerId === "kimi") {
    const base = (caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default"))
      ? caps.available_models
      : kimiFallbackModels;
    return base.map((m) => {
      const isInstantDisabled = Boolean(isDeepResearch && m.id === "instant");
      return {
        ...m,
        disabled: isInstantDisabled || m.disabled,
        badge: isInstantDisabled ? "Không hỗ trợ DR" : m.badge,
      };
    });
  }

  if (caps?.available_models && caps.available_models.length > 0) {
    return caps.available_models;
  }

  if (providerId === "gemini") return geminiFallbackModels;
  if (providerId === "qwen") return qwenFallbackModels;
  if (providerId === "zhipu") return zhipuFallbackModels;
  if (providerId === "minimax") return minimaxFallbackModels;

  return [
    {
      id: "auto",
      label: "Auto (Tự động)",
      description: "Tự động chọn mô hình phù hợp",
      selected: true,
    },
  ];
}

/**
 * Resolves reasoning/thinking levels for a given provider.
 */
export function resolveProviderThinkingLevels(
  providerId: string,
  caps?: ProviderLiveCapabilities
): OptionItem[] {
  if (["chatgpt", "copilot", "deepseek", "perplexity", "grok", "zhipu", "meta"].includes(providerId)) {
    return [];
  }

  if (providerId === "claude") {
    if (caps?.thinking_levels && caps.thinking_levels.length > 0 && !caps.thinking_levels.some((t) => t.id === "auto")) {
      return caps.thinking_levels;
    }
    return claudeFallbackThinking;
  }

  if (providerId === "kimi") {
    if (caps?.thinking_levels && caps.thinking_levels.length > 0 && !caps.thinking_levels.some((t) => t.id === "auto")) {
      return caps.thinking_levels;
    }
    return kimiFallbackThinking;
  }

  if (caps?.thinking_levels && caps.thinking_levels.length > 0) {
    return caps.thinking_levels;
  }

  if (providerId === "gemini") return geminiFallbackThinking;
  if (providerId === "qwen") return qwenFallbackThinking;
  if (providerId === "mistral") return mistralFallbackThinking;

  return [];
}

/**
 * Resolves operating modes for a given provider (e.g. Copilot).
 */
export function resolveProviderModes(
  providerId: string,
  caps?: ProviderLiveCapabilities
): OptionItem[] {
  if (["gemini", "qwen", "claude", "deepseek", "chatgpt", "perplexity", "kimi", "grok", "mistral", "zhipu", "minimax", "meta"].includes(providerId)) {
    return [];
  }

  if (providerId === "copilot" && (!caps?.modes || caps.modes.length === 0)) {
    return copilotFallbackModes;
  }

  return caps?.modes || [];
}

/**
 * Resolves current selected model ID, thinking level ID, and mode ID.
 */
export function resolveCurrentSelections(
  providerId: string,
  caps?: ProviderLiveCapabilities,
  sel?: ProviderSelectionConfig,
  models: OptionItem[] = [],
  thinkingLevels: OptionItem[] = [],
  modes: OptionItem[] = []
) {
  const selectableModels = models.filter((m) => !m.disabled);

  let currentModelId = "";
  if (providerId === "copilot" || providerId === "chatgpt") {
    currentModelId = "";
  } else if (providerId === "perplexity") {
    currentModelId = "auto";
  } else if (providerId === "claude") {
    currentModelId = sel?.model_id && models.some((m) => m.id === sel.model_id && !m.disabled)
      ? sel.model_id
      : caps?.selected_model_id && models.some((m) => m.id === caps.selected_model_id && !m.disabled)
        ? caps.selected_model_id
        : "claude-sonnet-5.5";
  } else if (providerId === "zhipu") {
    currentModelId = sel?.model_id && sel.model_id !== "glm-5" && models.some((m) => m.id === sel.model_id && !m.disabled)
      ? sel.model_id
      : caps?.selected_model_id && caps.selected_model_id !== "glm-5" && models.some((m) => m.id === caps.selected_model_id && !m.disabled)
        ? caps.selected_model_id
        : "glm-5.3-flash";
  } else if (providerId === "minimax") {
    currentModelId = sel?.model_id && models.some((m) => m.id === sel.model_id && !m.disabled)
      ? sel.model_id
      : caps?.selected_model_id && models.some((m) => m.id === caps.selected_model_id && !m.disabled)
        ? caps.selected_model_id
        : "m3";
  } else {
    currentModelId = sel?.model_id && models.some((m) => m.id === sel.model_id && !m.disabled)
      ? sel.model_id
      : caps?.selected_model_id && models.some((m) => m.id === caps.selected_model_id && !m.disabled)
        ? caps.selected_model_id
        : selectableModels[0]?.id || models[0]?.id || "";
  }

  const currentModel = providerId === "perplexity"
    ? (models.find((m) => m.id === "auto") || models[0])
    : (models.find((m) => m.id === currentModelId) || selectableModels[0] || models[0]);

  let currentThinkingId = "";
  if (["copilot", "chatgpt", "perplexity"].includes(providerId)) {
    currentThinkingId = "";
  } else if (providerId === "claude") {
    currentThinkingId = sel?.thinking_level_id && sel.thinking_level_id !== "auto" && thinkingLevels.some((t) => t.id === sel.thinking_level_id)
      ? sel.thinking_level_id
      : caps?.selected_thinking_level_id && caps.selected_thinking_level_id !== "auto" && thinkingLevels.some((t) => t.id === caps.selected_thinking_level_id)
        ? caps.selected_thinking_level_id
        : "medium";
  } else {
    currentThinkingId = sel?.thinking_level_id || caps?.selected_thinking_level_id || thinkingLevels[0]?.id || "";
  }

  const currentThinking = thinkingLevels.find((t) => t.id === currentThinkingId) || thinkingLevels[0];

  const currentModeId = modes.length > 0
    ? (sel?.mode_id || caps?.selected_mode_id || modes[0]?.id || (providerId === "copilot" ? "auto" : "standard"))
    : "";
  const currentMode = modes.length > 0 ? (modes.find((m) => m.id === currentModeId) || modes[0]) : undefined;

  return {
    currentModelId,
    currentModel,
    currentThinkingId,
    currentThinking,
    currentModeId,
    currentMode,
  };
}
