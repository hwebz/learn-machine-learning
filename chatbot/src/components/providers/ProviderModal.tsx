"use client";

import React, { useState, useEffect, useRef } from "react";
import { ProviderInfo } from "../../types/chat";
import { checkBackendHealth, openProviderBrowser } from "../../lib/api";
import { BrainIcon, ModelBadgeLogo, RefreshIcon, SearchIcon, SparklesIcon } from "../icons/Icons";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";

interface ProviderModalProps {
  isOpen: boolean;
  onClose: () => void;
  providers: ProviderInfo[];
  selectedProviderIds: string[];
  onToggleProvider: (id: string) => void;
  onSelectMultipleProviders: (ids: string[]) => void;
  capabilitiesMap?: Record<string, ProviderLiveCapabilities>;
  selectionsMap?: Record<string, ProviderSelectionConfig>;
  onUpdateSelection?: (providerId: string, updates: Partial<ProviderSelectionConfig>) => void;
  onSyncProvider?: (providerId: string) => Promise<any>;
  loadingProvider?: string | null;
  onSyncAll?: () => void;
  isSyncingAll?: boolean;
  onLoadCapabilities?: (providerId: string) => void;
}

export function ProviderModal({
  isOpen,
  onClose,
  providers,
  selectedProviderIds,
  onToggleProvider,
  onSelectMultipleProviders,
  capabilitiesMap = {},
  selectionsMap = {},
  onUpdateSelection,
  onSyncProvider,
  loadingProvider,
  onSyncAll,
  isSyncingAll,
  onLoadCapabilities,
}: ProviderModalProps) {
  const [backendStatus, setBackendStatus] = useState<{ online: boolean; data?: any }>({
    online: false,
  });
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [tempSelected, setTempSelected] = useState<string[]>(selectedProviderIds);

  const prevIsOpenRef = useRef(false);

  useEffect(() => {
    // Only synchronize tempSelected and check health when modal transitions from closed to open
    if (isOpen && !prevIsOpenRef.current) {
      setTempSelected(selectedProviderIds);
      setLoadingHealth(true);
      checkBackendHealth().then((res) => {
        setBackendStatus(res);
        setLoadingHealth(false);
      });
    }
    prevIsOpenRef.current = isOpen;
  }, [isOpen, selectedProviderIds]);

  // Load capabilities for all providers if not yet cached
  useEffect(() => {
    if (isOpen && onLoadCapabilities) {
      providers.forEach((p) => {
        if (!capabilitiesMap[p.id]) {
          onLoadCapabilities(p.id);
        }
      });
    }
  }, [isOpen, onLoadCapabilities, providers, capabilitiesMap]);

  if (!isOpen) return null;

  const handleToggle = (id: string) => {
    if (tempSelected.includes(id)) {
      setTempSelected(tempSelected.filter((p) => p !== id));
    } else {
      setTempSelected([...tempSelected, id]);
    }
  };

  const handleSelectAll = () => {
    setTempSelected(providers.map((p) => p.id));
  };

  const handleSelectTopThinking = () => {
    const thinkingIds = providers
      .filter((p) => p.supportsDeepMode)
      .slice(0, 4)
      .map((p) => p.id);
    setTempSelected(thinkingIds);
  };

  const handleApply = () => {
    if (tempSelected.length === 0) return;
    onSelectMultipleProviders(tempSelected);
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-dialog"
        style={{ maxWidth: 960, maxHeight: "90vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>
              AI Model & Provider Library (Multi-Model Matrix)
            </h2>
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 2 }}>
              Chọn đồng thời các providers, tùy chỉnh mô hình, mức suy luận, chế độ và đồng bộ trực tiếp từ DOM trình duyệt
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        <div className="modal-body">
          {/* Backend Status Alert */}
          <div
            style={{
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              backgroundColor: backendStatus.online ? "var(--accent-success-bg)" : "#fffbeb",
              border: `1px solid ${backendStatus.online ? "var(--accent-success-border)" : "#fde68a"}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: 12.5,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: backendStatus.online ? "var(--accent-success)" : "#f59e0b",
                }}
              />
              <span style={{ fontWeight: 600, color: backendStatus.online ? "#065f46" : "#92400e" }}>
                Backend API ({backendStatus.online ? "Connected at http://127.0.0.1:8000" : "Offline - Running Local Mode"})
              </span>
            </div>
            <span style={{ color: "var(--text-muted)", fontSize: 11 }}>
              {loadingHealth ? "Checking..." : backendStatus.online ? "FastAPI Connected" : "Local Mode"}
            </span>
          </div>

          {/* Preset Buttons & Selection Counter */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "4px 0",
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                Đã chọn: <strong style={{ color: "var(--brand-blue)" }}>{tempSelected.length} / {providers.length}</strong> models
              </span>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                className="btn-composer-pill"
                onClick={handleSelectTopThinking}
                style={{ padding: "4px 10px", fontSize: 12 }}
              >
                <BrainIcon size={13} color="var(--brand-blue)" />
                <span>Top Thinking (Copilot, Gemini, Qwen, ChatGPT)</span>
              </button>
              <button
                type="button"
                className="btn-composer-pill"
                onClick={handleSelectAll}
                style={{ padding: "4px 10px", fontSize: 12 }}
              >
                <span>Chọn tất cả ({providers.length})</span>
              </button>
              <button
                type="button"
                className="btn-composer-pill"
                onClick={() => setTempSelected([])}
                style={{ padding: "4px 10px", fontSize: 12 }}
              >
                <span>Bỏ chọn tất cả</span>
              </button>
              {onSyncAll && (
                <button
                  type="button"
                  className="btn-composer-pill"
                  onClick={onSyncAll}
                  disabled={isSyncingAll}
                  style={{
                    padding: "4px 10px",
                    fontSize: 12,
                    borderColor: "#bfdbfe",
                    color: "var(--brand-blue)",
                    backgroundColor: isSyncingAll ? "#eff6ff" : "transparent",
                    cursor: isSyncingAll ? "not-allowed" : "pointer",
                  }}
                  title="Quét lại DOM của tất cả các chatbot để cập nhật mô hình, suy luận và chế độ"
                >
                  <RefreshIcon
                    size={12}
                    color="var(--brand-blue)"
                    style={isSyncingAll ? { animation: "spin 1s linear infinite" } : undefined}
                  />
                  <span>{isSyncingAll ? "Đang quét tất cả DOM..." : "🔄 Đồng bộ tất cả DOM"}</span>
                </button>
              )}
            </div>
          </div>

          {/* Providers Grid with Combined Options */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
              gap: 14,
              maxHeight: "calc(88vh - 200px)",
              minHeight: 380,
              overflowY: "auto",
              paddingRight: 6,
            }}
          >
            {providers.map((p) => {
              const isSelected = tempSelected.includes(p.id);
              const caps = capabilitiesMap[p.id];
              const sel = selectionsMap[p.id] || {};
              const isSyncingThis = loadingProvider === p.id;

              const isFreeAccount = caps?.account_type === "free";
              const isChatGPT = p.id === "chatgpt";
              const isCopilot = p.id === "copilot";
              const isClaude = p.id === "claude";
              const isDeepSeek = p.id === "deepseek";
              const isPerplexity = p.id === "perplexity";
              const isKimi = p.id === "kimi";
              const isQwen = p.id === "qwen";
              const isGemini = p.id === "gemini";
              const isGrok = p.id === "grok";
              const isMistral = p.id === "mistral";

              const isDeepThinking = sel.deep_thinking !== undefined ? sel.deep_thinking : (caps?.deep_thinking ?? false);
              const isWebSearch = sel.web_search !== undefined ? sel.web_search : (caps?.web_search ?? true);
              const isDeepResearch = sel.deep_research !== undefined ? sel.deep_research : (caps?.deep_research ?? false);
              const researchMode = sel.research_mode || caps?.research_mode || "normal";
              const isResearchAdvanced = researchMode === "advanced";

              // 1. Models: Empty for ChatGPT, Copilot, and DeepSeek
              const claudeFallbackModels = [
                { id: "claude-sonnet-5.5", label: "Sonnet 5.5", description: "Cân bằng hoàn hảo giữa trí tuệ và tốc độ", selected: true, badge: "Sonnet", disabled: false },
                { id: "claude-haiku-5.5", label: "Haiku 5.5", description: "Phản hồi nhanh nhất cho tác vụ ngắn gọn", selected: false, badge: "Haiku", disabled: false },
                { id: "claude-opus-5.5", label: "Opus 5.5", description: "Dành cho tài khoản Pro (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
                { id: "claude-fable-5.1", label: "Fable 5.1", description: "Dành cho các thử thách khó khăn nhất (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
              ];

              const perplexityFallbackModels = [
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

              const kimiFallbackModels = [
                { id: "instant", label: "Instant", description: "Fast chat, quick replies (Phản hồi nhanh)", selected: true, disabled: false, badge: "Instant" },
                { id: "k3", label: "K3", description: "Chat & Agent, flagship all-rounder (Toàn diện, suy luận mạnh)", selected: false, disabled: false, badge: "K3" },
                { id: "k2.8", label: "K2.8", description: "Preview · Well-rounded and efficient for everyday tasks", selected: false, disabled: false, badge: "Preview" },
              ];

              const kimiFallbackThinking = [
                { id: "standard", label: "Standard", description: "Suy luận tiêu chuẩn, phản hồi cân bằng", selected: false, disabled: false, badge: "Standard" },
                { id: "high", label: "High", description: "Suy luận chuyên sâu cao nhất", selected: true, disabled: false, badge: "High" },
              ];

              const models = isChatGPT || isCopilot || isDeepSeek || isGrok || isMistral
                ? []
                : isClaude
                  ? (caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default")
                    ? caps.available_models.map((m) => {
                      const isUpgrade = m.id === "claude-opus-5.5" || m.id === "claude-fable-5.1" || m.disabled || m.metadata?.upgrade;
                      return {
                        ...m,
                        disabled: isUpgrade,
                        badge: isUpgrade ? "Upgrade" : m.badge,
                      };
                    })
                    : claudeFallbackModels)
                  : isPerplexity
                    ? (caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default")
                      ? caps.available_models.map((m) => ({
                        ...m,
                        disabled: m.id !== "auto",
                        badge: m.id === "auto" ? "Auto" : (m.badge || "Pro"),
                      }))
                      : perplexityFallbackModels)
                    : isKimi
                      ? (caps?.available_models && caps.available_models.length > 0 && !caps.available_models.some((m) => m.id === "default")
                        ? caps.available_models
                        : kimiFallbackModels).map((m) => {
                          const isInstantDisabled = isDeepResearch && m.id === "instant";
                          return {
                            ...m,
                            disabled: isInstantDisabled || m.disabled,
                            badge: isInstantDisabled ? "Không hỗ trợ DR" : m.badge,
                          };
                        })
                      : caps?.available_models && caps.available_models.length > 0
                        ? caps.available_models
                        : p.id === "gemini"
                          ? [
                            { id: "gemini-3.8-flash", label: "3.8 Flash", description: "Trợ giúp toàn diện", selected: true, badge: "Flash" },
                            { id: "gemini-3.5-flash-lite", label: "3.5 Flash-Lite", description: "Câu trả lời nhanh nhất", selected: false, badge: "Lite" },
                            { id: "gemini-3.1-pro", label: "3.1 Pro", description: "Suy luận nâng cao", selected: false, badge: "Pro" },
                            { id: "gemini-4-argon", label: "4 Argon", description: "Nhiệm vụ phức tạp", selected: false, badge: "Argon" },
                          ]
                          : p.id === "qwen"
                            ? [
                              { id: "qwen-3.8-max", label: "Qwen3.8-Max (Flagship)", description: "Mô hình cờ đầu thế hệ mới nhất", selected: true, badge: "Max" },
                              { id: "qwen-3.7-plus", label: "Qwen3.7-Plus (High Performance)", description: "Mô hình hiệu năng cao", selected: false, badge: "Plus" },
                              { id: "qwen-3.8-omni-flash", label: "Qwen3.8-Omni-Flash (Multimodal)", description: "Mô hình đa phương tiện tự nhiên", selected: false, badge: "Omni" },
                            ]
                            : [
                              {
                                id: "auto",
                                label: "Auto (Tự động)",
                                description: "Tự động chọn mô hình phù hợp",
                                selected: true,
                              },
                            ];

              // 2. Reasoning: Empty for ChatGPT, Copilot, DeepSeek, Perplexity, and Grok
              const thinkingLevels = isChatGPT || isCopilot || isDeepSeek || isPerplexity || isGrok
                ? []
                : isClaude
                  ? (caps?.thinking_levels && caps.thinking_levels.length > 0 && !caps.thinking_levels.some((t) => t.id === "auto")
                    ? caps.thinking_levels
                    : [
                      { id: "medium", label: "Medium (Recommended)", description: "Khuyên dùng - Cân bằng độ sâu và giới hạn sử dụng", selected: true, badge: "Med" },
                      { id: "low", label: "Low", description: "Thấp - Phản hồi nhanh và tiết kiệm giới hạn", selected: false, badge: "Low" },
                      { id: "high", label: "High", description: "Cao - Phân tích đa bước kỹ lưỡng cho bài toán hóc búa", selected: false, badge: "High" },
                      { id: "extra", label: "Extra", description: "Rất cao - Suy luận chuyên sâu cho nghiên cứu phức tạp", selected: false, badge: "Extra" },
                      { id: "max", label: "Max", description: "Tối đa - 8x hoặc nhiều hơn mức sử dụng giới hạn", selected: false, badge: "Max" },
                    ])
                  : isKimi
                    ? (caps?.thinking_levels && caps.thinking_levels.length > 0 && !caps.thinking_levels.some((t) => t.id === "auto")
                      ? caps.thinking_levels
                      : kimiFallbackThinking)
                    : caps?.thinking_levels && caps.thinking_levels.length > 0
                      ? caps.thinking_levels
                      : p.id === "gemini"
                        ? [
                          { id: "low", label: "Thấp (Nhanh chóng & hiệu quả)", description: "Nhanh chóng và hiệu quả", selected: true, badge: "Low" },
                          { id: "medium", label: "Trung bình (Độ sâu cân bằng)", description: "Độ sâu cân bằng", selected: false, badge: "Med" },
                          { id: "high", label: "Cao (Cực kỳ kỹ lưỡng)", description: "Cực kỳ kỹ lưỡng", selected: false, badge: "High" },
                        ]
                        : p.id === "qwen"
                          ? [
                            { id: "auto", label: "Auto (Tự động cân bằng)", description: "Tự động điều chỉnh mức độ suy luận", selected: true, badge: "Auto" },
                            { id: "thinking", label: "Thinking (Suy luận sâu đa bước)", description: "Kích hoạt chuỗi tư duy mở rộng", selected: false, badge: "Think" },
                            { id: "fast", label: "Fast (Phản hồi nhanh)", description: "Bỏ qua tư duy đa bước", selected: false, badge: "Fast" },
                          ]
                          : p.id === "mistral"
                            ? (caps?.thinking_levels && caps.thinking_levels.length > 0
                              ? caps.thinking_levels
                              : [
                                { id: "fast", label: "Fast (Nhanh)", description: "Get answers fast — Phản hồi nhanh cho câu hỏi thường ngày", selected: true, badge: "Fast" },
                                { id: "think", label: "Think (Suy luận)", description: "Handle complex tasks — Suy luận sâu cho tác vụ phức tạp", selected: false, badge: "Think" },
                              ])
                            : [];

              // 3. Modes: Copilot (All 5 options). Gemini, Qwen, Claude, DeepSeek, ChatGPT, Perplexity, Kimi, and Grok have no modes.
              const modes =
                p.id === "gemini" || p.id === "qwen" || isClaude || isDeepSeek || isChatGPT || isPerplexity || isKimi || isGrok || isMistral
                  ? []
                  : isCopilot && (!caps?.modes || caps.modes.length === 0)
                    ? [
                      {
                        id: "auto",
                        label: "Auto",
                        description: "Tự động cân bằng giữa tốc độ và độ chính xác (Mặc định)",
                        selected: true,
                        badge: "Auto",
                      },
                      {
                        id: "quick",
                        label: "Quick Response",
                        description: "Ưu tiên tốc độ phản hồi nhanh cho các câu hỏi ngắn gọn",
                        selected: false,
                        badge: "Fast",
                      },
                      {
                        id: "think_deeper",
                        label: "Think Deeper",
                        description: "Kích hoạt mô hình suy luận đa bước chuyên sâu cho bài toán phức tạp",
                        selected: false,
                        badge: "Think",
                      },
                      {
                        id: "gpt_5_6_quick",
                        label: "GPT > GPT-5.6 Sol Quick Response",
                        description: "Mô hình GPT-5.6 Sol tối ưu tốc độ phản hồi",
                        selected: false,
                        badge: "GPT-5.6",
                      },
                      {
                        id: "gpt_5_6_think",
                        label: "GPT > GPT-5.6 Sol Think Deeper",
                        description: "Mô hình GPT-5.6 Sol với khả năng suy luận chuyên sâu",
                        selected: false,
                        badge: "GPT-5.6",
                      },
                    ]
                    : caps?.modes || [];

              const dataTypes = caps?.supported_data_types;
              const voice = caps?.voice_chat;

              const selectableModels = models.filter((m) => !m.disabled);
              const currentModelId = isCopilot || isChatGPT
                ? ""
                : isPerplexity
                  ? "auto"
                  : isClaude
                    ? (sel.model_id && models.some((m) => m.id === sel.model_id && !m.disabled)
                      ? sel.model_id
                      : caps?.selected_model_id && models.some((m) => m.id === caps.selected_model_id && !m.disabled)
                        ? caps.selected_model_id
                        : "claude-sonnet-5.5")
                    : sel.model_id && models.some((m) => m.id === sel.model_id && !m.disabled)
                      ? sel.model_id
                      : caps?.selected_model_id && models.some((m) => m.id === caps.selected_model_id && !m.disabled)
                        ? caps.selected_model_id
                        : selectableModels[0]?.id || models[0]?.id || "";
              const currentModel = isPerplexity
                ? (models.find((m) => m.id === "auto") || models[0])
                : (models.find((m) => m.id === currentModelId) || selectableModels[0] || models[0]);

              const currentThinkingId = isCopilot || isChatGPT || isPerplexity
                ? ""
                : isClaude
                  ? (sel.thinking_level_id && sel.thinking_level_id !== "auto" && thinkingLevels.some((t) => t.id === sel.thinking_level_id)
                    ? sel.thinking_level_id
                    : caps?.selected_thinking_level_id && caps.selected_thinking_level_id !== "auto" && thinkingLevels.some((t) => t.id === caps.selected_thinking_level_id)
                      ? caps.selected_thinking_level_id
                      : "medium")
                  : sel.thinking_level_id || caps?.selected_thinking_level_id || thinkingLevels[0]?.id || "";
              const currentThinking =
                thinkingLevels.find((t) => t.id === currentThinkingId) || thinkingLevels[0];

              const currentModeId = modes.length > 0 ? (sel.mode_id || caps?.selected_mode_id || modes[0]?.id || (isCopilot ? "auto" : "standard")) : "";
              const currentMode = modes.length > 0 ? (modes.find((m) => m.id === currentModeId) || modes[0]) : undefined;

              return (
                <div
                  key={p.id}
                  onClick={() => handleToggle(p.id)}
                  style={{
                    padding: "14px 16px",
                    borderRadius: "var(--radius-lg)",
                    border: `1.5px solid ${isSelected ? "var(--brand-blue)" : "var(--border-default)"}`,
                    backgroundColor: isSelected ? "var(--brand-blue-light)" : "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                    transition: "all var(--transition-fast)",
                    boxShadow: isSelected ? "0 4px 12px rgba(37, 99, 235, 0.12)" : "var(--shadow-sm)",
                    position: "relative",
                  }}
                >
                  {/* Top Header Row: Checkbox, Logo, Name, Badges */}
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                    {/* Checkbox indicator */}
                    <div
                      style={{
                        width: 20,
                        height: 20,
                        borderRadius: 5,
                        border: `2px solid ${isSelected ? "var(--brand-blue)" : "#cbd5e1"}`,
                        backgroundColor: isSelected ? "var(--brand-blue)" : "#ffffff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#ffffff",
                        fontSize: 12,
                        fontWeight: 800,
                        flexShrink: 0,
                        marginTop: 2,
                      }}
                    >
                      {isSelected ? "✓" : ""}
                    </div>

                    <ModelBadgeLogo type={p.iconType} size={32} />

                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)" }}>
                            {p.name}
                          </span>
                          {p.supportsDeepMode && (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 3,
                                fontSize: 9.5,
                                fontWeight: 700,
                                color: "var(--brand-blue)",
                                backgroundColor: "#ffffff",
                                padding: "2px 6px",
                                borderRadius: 4,
                                border: "1px solid #bfdbfe",
                              }}
                            >
                              <BrainIcon size={10} color="var(--brand-blue)" />
                              {p.deepModeLabel?.split(" ")[0] || "Deep"}
                            </span>
                          )}
                        </div>

                        {/* DOM Status Indicator */}
                        {caps?.is_live_dom ? (
                          <span
                            style={{
                              fontSize: 9.5,
                              fontWeight: 700,
                              color: "#15803d",
                              backgroundColor: "#dcfce7",
                              padding: "2px 6px",
                              borderRadius: 4,
                              border: "1px solid #bbf7d0",
                            }}
                            title="Đã đồng bộ trực tiếp từ DOM của trình duyệt"
                          >
                            LIVE DOM
                          </span>
                        ) : (
                          <span
                            style={{
                              fontSize: 9.5,
                              fontWeight: 600,
                              color: "#64748b",
                              backgroundColor: "#f1f5f9",
                              padding: "2px 6px",
                              borderRadius: 4,
                              border: "1px solid #e2e8f0",
                            }}
                            title="Tùy chọn mặc định — Bấm 'Đồng bộ DOM' để quét trực tiếp"
                          >
                            CACHED
                          </span>
                        )}
                      </div>

                      <span style={{ fontSize: 11.5, color: "var(--text-muted)", display: "block", marginTop: 1 }}>
                        {isChatGPT ? "Web Search, Deep Research & Thinking" : isCopilot ? "Quản lý theo Chế độ (Mode)" : p.modelName}
                      </span>
                    </div>
                  </div>

                  {/* Short Description */}
                  <p
                    style={{
                      fontSize: 11.5,
                      color: "var(--text-secondary)",
                      lineHeight: 1.4,
                      margin: 0,
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {p.shortDesc}
                  </p>

                  {/* Provider Options Box (Model, Thinking, Mode, Tools, Data Types) */}
                  <div
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 8,
                      backgroundColor: isSelected ? "rgba(255, 255, 255, 0.92)" : "#f8fafc",
                      border: `1px solid ${isSelected ? "#bfdbfe" : "#e2e8f0"}`,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                      flexGrow: 1
                    }}
                  >
                    {/* DeepSeek: Exactly 2 toggles: DeepThink (R1) and Web Search */}
                    {isDeepSeek ? (
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 10,
                          flexGrow: 1,
                        }}
                      >
                        {/* 1. DeepThink (R1) Toggle */}
                        <div
                          onClick={() => onUpdateSelection?.(p.id, { deep_thinking: !isDeepThinking })}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 12px",
                            borderRadius: 6,
                            border: `1.5px solid ${isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isDeepThinking ? "#eff6ff" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt mô hình suy luận sâu DeepSeek-R1 (Chain of Thought)"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <BrainIcon size={16} color={isDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
                            <div>
                              <div style={{ fontSize: 12, fontWeight: 700, color: isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)" }}>
                                DeepThink (R1)
                              </div>
                              <div style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)" }}>
                                Suy luận chuyên sâu
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: "2px 8px",
                              borderRadius: 10,
                              backgroundColor: isDeepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                              color: isDeepThinking ? "#ffffff" : "#64748b",
                            }}
                          >
                            {isDeepThinking ? "BẬT" : "TẮT"}
                          </span>
                        </div>

                        {/* 2. Web Search Toggle */}
                        <div
                          onClick={() => onUpdateSelection?.(p.id, { web_search: !isWebSearch })}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 12px",
                            borderRadius: 6,
                            border: `1.5px solid ${isWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isWebSearch ? "#ecfdf5" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt tính năng tìm kiếm Web thời gian thực của DeepSeek"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <SearchIcon size={14} color={isWebSearch ? "#059669" : "#64748b"} />
                            <div>
                              <div style={{ fontSize: 12, fontWeight: 700, color: isWebSearch ? "#059669" : "var(--text-primary, #0f172a)" }}>
                                Tìm kiếm Web
                              </div>
                              <div style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)" }}>
                                Tra cứu trực tuyến
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: "2px 8px",
                              borderRadius: 10,
                              backgroundColor: isWebSearch ? "#059669" : "#e2e8f0",
                              color: isWebSearch ? "#ffffff" : "#64748b",
                            }}
                          >
                            {isWebSearch ? "BẬT" : "TẮT"}
                          </span>
                        </div>
                      </div>
                    ) : isChatGPT ? (
                      /* ChatGPT: Exactly 3 toggles: Web Search, Deep Research, Thinking */
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(2, 1fr)",
                          gridTemplateRows: "repeat(2, 1fr)",
                          gap: 8,
                          flexGrow: 1,
                        }}
                      >
                        {/* 1. Web Search Toggle */}
                        <div
                          onClick={() => onUpdateSelection?.(p.id, { web_search: !isWebSearch })}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 10px",
                            borderRadius: 6,
                            border: `1.5px solid ${isWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isWebSearch ? "#ecfdf5" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt tính năng tìm kiếm Web (+ Web search)"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                            <SearchIcon size={14} color={isWebSearch ? "#059669" : "#64748b"} />
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontSize: 11.5, fontWeight: 700, color: isWebSearch ? "#059669" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Web Search
                              </div>
                              <div style={{ fontSize: 9.5, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Tra cứu trực tuyến
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 9.5,
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: 10,
                              backgroundColor: isWebSearch ? "#059669" : "#e2e8f0",
                              color: isWebSearch ? "#ffffff" : "#64748b",
                              marginLeft: 4,
                              flexShrink: 0,
                            }}
                          >
                            {isWebSearch ? "BẬT" : "TẮT"}
                          </span>
                        </div>

                        {/* 2. Deep Research Toggle */}
                        <div
                          onClick={() => onUpdateSelection?.(p.id, { deep_research: !isDeepResearch })}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 10px",
                            borderRadius: 6,
                            border: `1.5px solid ${isDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt tính năng Deep Research (+ Deep research)"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                            <SparklesIcon size={14} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontSize: 11.5, fontWeight: 700, color: isDeepResearch ? "#7c3aed" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Deep Research
                              </div>
                              <div style={{ fontSize: 9.5, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Nghiên cứu sâu
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 9.5,
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: 10,
                              backgroundColor: isDeepResearch ? "#7c3aed" : "#e2e8f0",
                              color: isDeepResearch ? "#ffffff" : "#64748b",
                              marginLeft: 4,
                              flexShrink: 0,
                            }}
                          >
                            {isDeepResearch ? "BẬT" : "TẮT"}
                          </span>
                        </div>

                        {/* 3. Thinking Toggle */}
                        <div
                          onClick={() => onUpdateSelection?.(p.id, { deep_thinking: !isDeepThinking })}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 10px",
                            borderRadius: 6,
                            border: `1.5px solid ${isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isDeepThinking ? "#eff6ff" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt chế độ suy luận chuyên sâu (Nút Think)"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                            <BrainIcon size={14} color={isDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontSize: 11.5, fontWeight: 700, color: isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Thinking
                              </div>
                              <div style={{ fontSize: 9.5, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Chuỗi suy luận
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 9.5,
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: 10,
                              backgroundColor: isDeepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                              color: isDeepThinking ? "#ffffff" : "#64748b",
                              marginLeft: 4,
                              flexShrink: 0,
                            }}
                          >
                            {isDeepThinking ? "BẬT" : "TẮT"}
                          </span>
                        </div>
                      </div>
                    ) : isCopilot ? (
                      /* Copilot: Only Mode selector */
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 6,
                          flexGrow: 1,
                        }}
                      >
                        {modes.length > 0 ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: "var(--brand-blue)",
                                  letterSpacing: "0.4px",
                                }}
                              >
                                Chế độ mô hình Copilot (Mode)
                              </label>
                              {currentMode?.badge && (
                                <span
                                  style={{
                                    fontSize: 9.5,
                                    padding: "1px 5px",
                                    borderRadius: 3,
                                    backgroundColor: "#eff6ff",
                                    color: "var(--brand-blue)",
                                    fontWeight: 700,
                                  }}
                                >
                                  {currentMode.badge}
                                </span>
                              )}
                            </div>
                            <select
                              value={currentModeId}
                              onChange={(e) => {
                                onUpdateSelection?.(p.id, { mode_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: "1px solid var(--border-default, #cbd5e1)",
                                backgroundColor: "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: "var(--text-primary, #0f172a)",
                                cursor: "pointer",
                                outline: "none",
                              }}
                            >
                              {modes.map((m) => (
                                <option key={m.id} value={m.id}>
                                  {m.label}
                                </option>
                              ))}
                            </select>
                            <span style={{ fontSize: 10.5, color: "var(--brand-blue)", lineHeight: 1.25, fontWeight: 500 }}>
                              Mỗi tùy chọn tương ứng với một tùy chọn trong menu chọn mô hình trên Copilot
                            </span>
                          </div>
                        ) : (
                          <div style={{ fontSize: 11, color: "var(--text-muted)", fontStyle: "italic", padding: "4px 0" }}>
                            Copilot tự động chọn chế độ tối ưu
                          </div>
                        )}
                      </div>
                    ) : isPerplexity ? (
                      /* Perplexity: Column 1 = Model list (Auto selected, Pro models disabled), Column 2 = Disabled Thinking Toggle */
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 10,
                          flexGrow: 1,
                        }}
                      >
                        {/* 1. Model Selector */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <label
                              style={{
                                fontSize: 11,
                                fontWeight: 700,
                                color: "var(--text-secondary)",
                                letterSpacing: "0.4px",
                              }}
                            >
                              Mô hình AI (Model)
                            </label>
                            <span
                              style={{
                                fontSize: 9.5,
                                padding: "1px 5px",
                                borderRadius: 3,
                                backgroundColor: "var(--brand-blue)",
                                color: "#ffffff",
                                fontWeight: 700,
                              }}
                            >
                              Auto
                            </span>
                          </div>
                          <select
                            value="auto"
                            onChange={() => {
                              // Always Auto for free accounts
                            }}
                            style={{
                              width: "100%",
                              padding: "6px 8px",
                              borderRadius: 6,
                              border: "1px solid var(--border-default, #cbd5e1)",
                              backgroundColor: "#ffffff",
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--text-primary, #0f172a)",
                              cursor: "default",
                              outline: "none",
                            }}
                          >
                            {models.map((m) => (
                              <option key={m.id} value={m.id} disabled={m.disabled}>
                                {m.label}{m.disabled ? " (Pro - Khóa)" : " (Mặc định)"}
                              </option>
                            ))}
                          </select>
                          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                            Tài khoản miễn phí cố định ở Auto. Mô hình Pro được đồng bộ từ DOM nhưng bị khóa.
                          </span>
                        </div>

                        {/* 2. Disabled Thinking Toggle */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <span
                              style={{
                                fontSize: 9.5,
                                padding: "1px 5px",
                                borderRadius: 3,
                                backgroundColor: "#f1f5f9",
                                color: "#64748b",
                                fontWeight: 700,
                              }}
                            >
                              Locked
                            </span>
                          </div>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "7px 10px",
                              borderRadius: 6,
                              border: "1.5px solid var(--border-default, #cbd5e1)",
                              backgroundColor: "#f8fafc",
                              cursor: "not-allowed",
                              opacity: 0.7,
                            }}
                            title="Tính năng Thinking bị khóa trên tài khoản Perplexity miễn phí"
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <BrainIcon size={14} color="#94a3b8" />
                              <div>
                                <div style={{ fontSize: 11.5, fontWeight: 700, color: "var(--text-muted, #64748b)" }}>
                                  Thinking
                                </div>
                                <div style={{ fontSize: 9.5, color: "var(--text-muted, #94a3b8)" }}>
                                  Suy luận đa bước
                                </div>
                              </div>
                            </div>
                            <span
                              style={{
                                fontSize: 9.5,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 10,
                                backgroundColor: "#e2e8f0",
                                color: "#94a3b8",
                              }}
                            >
                              TẮT (KHÓA)
                            </span>
                          </div>
                          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                            Chế độ Thinking yêu cầu tài khoản Perplexity Pro
                          </span>
                        </div>
                      </div>
                    ) : isKimi ? (
                      /* Kimi: Row 1 = Model & Reasoning, Row 2 = Deep Research Toggle */
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                          flexGrow: 1,
                        }}
                      >
                        {/* Row 1: Model & Reasoning */}
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: 10,
                          }}
                        >
                          {/* 1. Model Selector */}
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: "var(--text-secondary)",
                                  letterSpacing: "0.4px",
                                }}
                              >
                                Mô hình Kimi
                              </label>
                              <span
                                style={{
                                  fontSize: 9.5,
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  backgroundColor: isDeepResearch && currentModelId === "instant" ? "#fef3c7" : "var(--brand-blue)",
                                  color: isDeepResearch && currentModelId === "instant" ? "#b45309" : "#ffffff",
                                  fontWeight: 700,
                                }}
                              >
                                {isDeepResearch && currentModelId === "instant" ? "Disabled" : (currentModel?.badge || "Active")}
                              </span>
                            </div>
                            <select
                              disabled={models.length <= 1}
                              value={currentModelId}
                              onChange={(e) => {
                                const targetM = models.find((m) => m.id === e.target.value);
                                if (targetM?.disabled || (isDeepResearch && e.target.value === "instant")) return;
                                onUpdateSelection?.(p.id, { model_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: "1px solid var(--border-default, #cbd5e1)",
                                backgroundColor: "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: "var(--text-primary, #0f172a)",
                                cursor: "pointer",
                                outline: "none",
                              }}
                              title="Chọn mô hình Kimi"
                            >
                              {models.map((m) => {
                                const isInstantDisabled = isDeepResearch && m.id === "instant";
                                return (
                                  <option key={m.id} value={m.id} disabled={m.disabled || isInstantDisabled}>
                                    {m.label} {isInstantDisabled ? "— (Deep Research không hỗ trợ)" : m.badge ? `[${m.badge}]` : ""}
                                  </option>
                                );
                              })}
                            </select>
                            <span style={{ fontSize: 10.5, color: isDeepResearch && currentModelId === "instant" ? "#b45309" : "var(--text-muted)", lineHeight: 1.25 }}>
                              {isDeepResearch && currentModelId === "instant"
                                ? "Deep Research không hỗ trợ Instant (chuyển sang K3 hoặc K2.8)"
                                : (currentModel?.description || "Mô hình Kimi")}
                            </span>
                          </div>

                          {/* 2. Reasoning Picker */}
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: "var(--text-secondary)",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 4,
                                }}
                              >
                                <BrainIcon size={12} color="var(--brand-blue)" />
                                <span>Thinking effort</span>
                              </label>
                              {currentThinking?.badge && (
                                <span
                                  style={{
                                    fontSize: 9.5,
                                    padding: "1px 5px",
                                    borderRadius: 3,
                                    backgroundColor: "#eff6ff",
                                    color: "var(--brand-blue)",
                                    fontWeight: 700,
                                  }}
                                >
                                  {currentThinking.badge}
                                </span>
                              )}
                            </div>
                            <select
                              disabled={thinkingLevels.length <= 1}
                              value={currentThinkingId}
                              onChange={(e) => {
                                onUpdateSelection?.(p.id, { thinking_level_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: "1px solid var(--border-default, #cbd5e1)",
                                backgroundColor: thinkingLevels.length <= 1 ? "#f8fafc" : "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: thinkingLevels.length <= 1 ? "#64748b" : "var(--text-primary, #0f172a)",
                                cursor: thinkingLevels.length <= 1 ? "not-allowed" : "pointer",
                                outline: "none",
                              }}
                            >
                              {thinkingLevels.map((t) => (
                                <option key={t.id} value={t.id} disabled={t.disabled}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                            <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                              {currentThinking?.description || "2 mức suy luận trong menu mô hình"}
                            </span>
                          </div>
                        </div>

                        {/* Row 2: Deep Research Toggle */}
                        <div
                          onClick={() => {
                            const nextDr = !isDeepResearch;
                            const updates: Partial<ProviderSelectionConfig> = {
                              deep_research: nextDr,
                              ...(nextDr && (currentModelId === "instant" || !currentModelId || currentModelId === "default") ? { model_id: "k3" } : {}),
                            };
                            onUpdateSelection?.(p.id, updates);
                          }}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 12px",
                            borderRadius: 6,
                            border: `1.5px solid ${isDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt tính năng Deep Research của Kimi"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <SparklesIcon size={16} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
                            <div>
                              <div style={{ fontSize: 12, fontWeight: 700, color: isDeepResearch ? "#7c3aed" : "var(--text-primary, #0f172a)" }}>
                                Deep Research
                              </div>
                              <div style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)" }}>
                                Nghiên cứu và tìm kiếm thông tin chuyên sâu (Không hỗ trợ Instant, chuyển sang K3)
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: "2px 8px",
                              borderRadius: 10,
                              backgroundColor: isDeepResearch ? "#7c3aed" : "#e2e8f0",
                              color: isDeepResearch ? "#ffffff" : "#64748b",
                              flexShrink: 0,
                            }}
                          >
                            {isDeepResearch ? "BẬT" : "TẮT"}
                          </span>
                        </div>
                      </div>
                    ) : isQwen ? (
                      /* Qwen: Row 1 = Model & Reasoning (Reasoning disabled & locked to Auto when Deep Research is ON), Row 2 = Web Search, Deep Research & Research Mode */
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                          flexGrow: 1,
                        }}
                      >
                        {/* Row 1: Model & Reasoning */}
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: 10,
                          }}
                        >
                          {/* 1. Model Selector */}
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: "var(--text-secondary)",
                                  letterSpacing: "0.4px",
                                }}
                              >
                                Mô hình Qwen
                              </label>
                              <span
                                style={{
                                  fontSize: 9.5,
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  backgroundColor: "var(--brand-blue)",
                                  color: "#ffffff",
                                  fontWeight: 700,
                                }}
                              >
                                {currentModel?.badge || "Active"}
                              </span>
                            </div>
                            <select
                              disabled={models.length <= 1}
                              value={currentModelId}
                              onChange={(e) => {
                                const targetM = models.find((m) => m.id === e.target.value);
                                if (targetM?.disabled) return;
                                onUpdateSelection?.(p.id, { model_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: "1px solid var(--border-default, #cbd5e1)",
                                backgroundColor: "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: "var(--text-primary, #0f172a)",
                                cursor: "pointer",
                                outline: "none",
                              }}
                              title="Chọn mô hình Qwen"
                            >
                              {models.map((m) => (
                                <option key={m.id} value={m.id} disabled={m.disabled}>
                                  {m.label} {m.disabled ? "— (Upgrade)" : m.badge ? `[${m.badge}]` : ""}
                                </option>
                              ))}
                            </select>
                            <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                              {currentModel?.description || "Mô hình Qwen"}
                            </span>
                          </div>

                          {/* 2. Reasoning Picker */}
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: isDeepResearch ? "#7c3aed" : "var(--text-secondary)",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 4,
                                }}
                              >
                                <BrainIcon size={12} color={isDeepResearch ? "#7c3aed" : "var(--brand-blue)"} />
                                <span>Mức suy luận (Reasoning)</span>
                              </label>
                              <span
                                style={{
                                  fontSize: 9.5,
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  backgroundColor: isDeepResearch ? "#f5f3ff" : "#eff6ff",
                                  color: isDeepResearch ? "#7c3aed" : "var(--brand-blue)",
                                  fontWeight: 700,
                                }}
                              >
                                {isDeepResearch ? "Auto" : (currentThinking?.badge || "Auto")}
                              </span>
                            </div>
                            <select
                              disabled={isDeepResearch || thinkingLevels.length <= 1}
                              value={isDeepResearch ? "auto" : currentThinkingId}
                              onChange={(e) => {
                                if (isDeepResearch) return;
                                onUpdateSelection?.(p.id, { thinking_level_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: `1px solid ${isDeepResearch ? "#c4b5fd" : "var(--border-default, #cbd5e1)"}`,
                                backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: isDeepResearch ? "#7c3aed" : "var(--text-primary, #0f172a)",
                                cursor: isDeepResearch ? "not-allowed" : "pointer",
                                outline: "none",
                                opacity: isDeepResearch ? 0.75 : 1,
                              }}
                              title={isDeepResearch ? "Deep Research không cho phép thay đổi mức suy luận (khóa về Auto)" : "Chọn mức độ suy luận"}
                            >
                              {isDeepResearch ? (
                                <option value="auto">Auto</option>
                              ) : (
                                thinkingLevels.map((t) => (
                                  <option key={t.id} value={t.id} disabled={t.disabled}>
                                    {t.label}
                                  </option>
                                ))
                              )}
                            </select>
                            <span style={{ fontSize: 10.5, color: isDeepResearch ? "#7c3aed" : "var(--text-muted)", lineHeight: 1.25 }}>
                              {isDeepResearch ? "Deep Research không cho phép chỉnh mức độ suy luận (mặc định Auto)" : (currentThinking?.description || "3 mức suy luận Qwen")}
                            </span>
                          </div>
                        </div>

                        {/* Row 2: Toggles (Web Search, Deep Research, and Research Mode when Deep Research is ON) */}
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "repeat(2, 1fr)",
                            gridAutoRows: "repeat(2, 1fr)",
                            gap: 8,
                          }}
                        >
                          {/* 1. Web Search Toggle */}
                          <div
                            onClick={() => onUpdateSelection?.(p.id, { web_search: !isWebSearch })}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "8px 10px",
                              borderRadius: 6,
                              border: `1.5px solid ${isWebSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                              backgroundColor: isWebSearch ? "#ecfdf5" : "#ffffff",
                              cursor: "pointer",
                              transition: "all 0.15s ease",
                            }}
                            title="Bật/Tắt tìm kiếm Web trên Qwen (+ menu)"
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                              <SearchIcon size={14} color={isWebSearch ? "#059669" : "#64748b"} />
                              <div style={{ minWidth: 0 }}>
                                <div style={{ fontSize: 11.5, fontWeight: 700, color: isWebSearch ? "#059669" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                  Web Search
                                </div>
                                <div style={{ fontSize: 9.5, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                  Tra cứu trực tuyến
                                </div>
                              </div>
                            </div>
                            <span
                              style={{
                                fontSize: 9.5,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 10,
                                backgroundColor: isWebSearch ? "#059669" : "#e2e8f0",
                                color: isWebSearch ? "#ffffff" : "#64748b",
                                marginLeft: 4,
                                flexShrink: 0,
                              }}
                            >
                              {isWebSearch ? "BẬT" : "TẮT"}
                            </span>
                          </div>

                          {/* 2. Deep Research Toggle */}
                          <div
                            onClick={() => {
                              const nextDr = !isDeepResearch;
                              const updates: Partial<ProviderSelectionConfig> = {
                                deep_research: nextDr,
                                ...(nextDr
                                  ? {
                                    thinking_level_id: "auto",
                                  }
                                  : {}),
                              };
                              onUpdateSelection?.(p.id, updates);
                            }}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "8px 10px",
                              borderRadius: 6,
                              border: `1.5px solid ${isDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                              backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
                              cursor: "pointer",
                              transition: "all 0.15s ease",
                            }}
                            title="Bật/Tắt tính năng Deep Research của Qwen (+ menu)"
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                              <SparklesIcon size={14} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
                              <div style={{ minWidth: 0 }}>
                                <div style={{ fontSize: 11.5, fontWeight: 700, color: isDeepResearch ? "#7c3aed" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                  Deep Research
                                </div>
                                <div style={{ fontSize: 9.5, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                  Nghiên cứu sâu
                                </div>
                              </div>
                            </div>
                            <span
                              style={{
                                fontSize: 9.5,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 10,
                                backgroundColor: isDeepResearch ? "#7c3aed" : "#e2e8f0",
                                color: isDeepResearch ? "#ffffff" : "#64748b",
                                marginLeft: 4,
                                flexShrink: 0,
                              }}
                            >
                              {isDeepResearch ? "BẬT" : "TẮT"}
                            </span>
                          </div>

                          {/* 2.1 Research Mode Toggle (when Deep Research is ON) */}
                          {isDeepResearch && (
                            <div
                              onClick={() => {
                                const nextMode = isResearchAdvanced ? "normal" : "advanced";
                                onUpdateSelection?.(p.id, { research_mode: nextMode });
                              }}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                padding: "8px 10px",
                                borderRadius: 6,
                                border: `1.5px solid ${isResearchAdvanced ? "#9333ea" : "var(--border-default, #cbd5e1)"}`,
                                backgroundColor: isResearchAdvanced ? "#f3e8ff" : "#ffffff",
                                cursor: "pointer",
                                transition: "all 0.15s ease",
                              }}
                              title={isResearchAdvanced
                                ? "Advanced - Devoting extra time to a deeper analysis"
                                : "Normal - Fast, reliable responses for quick tasks"}
                            >
                              <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                                <SparklesIcon size={14} color={isResearchAdvanced ? "#9333ea" : "#64748b"} />
                                <div style={{ minWidth: 0 }}>
                                  <div style={{ fontSize: 11.5, fontWeight: 700, color: isResearchAdvanced ? "#9333ea" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                    {isResearchAdvanced ? "Advanced" : "Normal"}
                                  </div>
                                  <div style={{ fontSize: 9, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={isResearchAdvanced ? "Devoting extra time to a deeper analysis" : "Fast, reliable responses for quick tasks"}>
                                    {isResearchAdvanced ? "Extra time deeper analysis" : "Fast & reliable"}
                                  </div>
                                </div>
                              </div>
                              <span
                                style={{
                                  fontSize: 9.5,
                                  fontWeight: 700,
                                  padding: "2px 6px",
                                  borderRadius: 10,
                                  backgroundColor: isResearchAdvanced ? "#9333ea" : "#e2e8f0",
                                  color: isResearchAdvanced ? "#ffffff" : "#64748b",
                                  marginLeft: 4,
                                  flexShrink: 0,
                                }}
                              >
                                {isResearchAdvanced ? "BẬT" : "TẮT"}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : isGemini ? (
                      /* Gemini: Row 1 = Model & Reasoning, Row 2 = Deep Research toggle */
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                          flexGrow: 1,
                        }}
                      >
                        {/* Row 1: Model & Reasoning */}
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: thinkingLevels.length > 0 ? "1fr 1fr" : "1fr",
                            gap: 10,
                          }}
                        >
                          {/* 1. Model Selector */}
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: "var(--text-secondary)",
                                  letterSpacing: "0.4px",
                                }}
                              >
                                Mô hình Gemini
                              </label>
                              <span
                                style={{
                                  fontSize: 9.5,
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  backgroundColor: currentModel?.disabled ? "#fef3c7" : "var(--brand-blue)",
                                  color: currentModel?.disabled ? "#b45309" : "#ffffff",
                                  fontWeight: 700,
                                }}
                              >
                                {currentModel?.badge || "Active"}
                              </span>
                            </div>
                            <select
                              disabled={models.length <= 1}
                              value={currentModelId}
                              onChange={(e) => {
                                const targetM = models.find((m) => m.id === e.target.value);
                                if (targetM?.disabled) return;
                                onUpdateSelection?.(p.id, { model_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: "1px solid var(--border-default, #cbd5e1)",
                                backgroundColor: "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: "var(--text-primary, #0f172a)",
                                cursor: "pointer",
                                outline: "none",
                              }}
                              title="Chọn mô hình Gemini"
                            >
                              {models.map((m) => (
                                <option key={m.id} value={m.id} disabled={m.disabled}>
                                  {m.label} {m.disabled ? "— (Upgrade)" : m.badge ? `[${m.badge}]` : ""}
                                </option>
                              ))}
                            </select>
                            <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                              {currentModel?.description || "Mô hình Google Gemini"}
                            </span>
                          </div>

                          {/* 2. Reasoning Picker */}
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: "var(--text-secondary)",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 4,
                                }}
                              >
                                <BrainIcon size={12} color="var(--brand-blue)" />
                                <span>Mức suy luận (Reasoning)</span>
                              </label>
                              {currentThinking?.badge && (
                                <span
                                  style={{
                                    fontSize: 9.5,
                                    padding: "1px 5px",
                                    borderRadius: 3,
                                    backgroundColor: "#eff6ff",
                                    color: "var(--brand-blue)",
                                    fontWeight: 700,
                                  }}
                                >
                                  {currentThinking.badge}
                                </span>
                              )}
                            </div>
                            <select
                              disabled={thinkingLevels.length <= 1}
                              value={currentThinkingId}
                              onChange={(e) => {
                                onUpdateSelection?.(p.id, { thinking_level_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: "1px solid var(--border-default, #cbd5e1)",
                                backgroundColor: thinkingLevels.length <= 1 ? "#f8fafc" : "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: thinkingLevels.length <= 1 ? "#64748b" : "var(--text-primary, #0f172a)",
                                cursor: thinkingLevels.length <= 1 ? "not-allowed" : "pointer",
                                outline: "none",
                              }}
                              title="Chọn mức độ suy luận"
                            >
                              {thinkingLevels.map((t) => (
                                <option key={t.id} value={t.id}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                            <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                              {currentThinking?.description || "Mức suy luận Gemini"}
                            </span>
                          </div>
                        </div>

                        {/* Row 2: Deep Research Toggle */}
                        <div
                          onClick={() => onUpdateSelection?.(p.id, { deep_research: !isDeepResearch })}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 10px",
                            borderRadius: 6,
                            border: `1.5px solid ${isDeepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt tính năng Deep Research của Gemini (+ menu)"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                            <SparklesIcon size={14} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
                            <div style={{ minWidth: 0 }}>
                              <div style={{ fontSize: 11.5, fontWeight: 700, color: isDeepResearch ? "#7c3aed" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Deep Research
                              </div>
                              <div style={{ fontSize: 9.5, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                Nghiên cứu sâu (+ menu)
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 9.5,
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: 10,
                              backgroundColor: isDeepResearch ? "#7c3aed" : "#e2e8f0",
                              color: isDeepResearch ? "#ffffff" : "#64748b",
                              marginLeft: 4,
                              flexShrink: 0,
                            }}
                          >
                            {isDeepResearch ? "BẬT" : "TẮT"}
                          </span>
                        </div>
                      </div>
                    ) : isGrok ? (
                      /* xAI Grok: Free account — no options to configure, uses all defaults */
                      <div
                        style={{
                          display: "flex",
                          flexDirection: 'column',
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          padding: "10px 14px",
                          borderRadius: 8,
                          backgroundColor: "#f8fafc",
                          border: "1px dashed var(--border-default, #cbd5e1)",
                          flexGrow: 1,
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "flex-start", flexDirection: 'column', gap: 8 }}>
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: 4,
                              backgroundColor: "#e2e8f0",
                              color: "#475569",
                            }}
                          >
                            FREE ACCOUNT
                          </span>
                          <span style={{ fontSize: 12, color: "var(--text-muted, #64748b)" }}>
                            Tài khoản miễn phí — không có cấu hình tùy chỉnh, sử dụng toàn bộ mặc định từ xAI Grok.
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            color: "var(--text-muted, #94a3b8)",
                            fontStyle: "italic",
                          }}
                        >
                          Mặc định (Default)
                        </span>
                      </div>
                    ) : isMistral ? (
                      /* Mistral Le Chat: Reasoning dropdown (Fast / Think) + Deep Research toggle (@deep-research) */
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                          flexGrow: 1,
                        }}
                      >
                        {/* Row 1: Reasoning Mode (Fast vs Think) */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <label
                              style={{
                                fontSize: 11,
                                fontWeight: 700,
                                color: "var(--text-secondary)",
                                display: "flex",
                                alignItems: "center",
                                gap: 4,
                              }}
                            >
                              <BrainIcon size={12} color="#ea580c" />
                              <span>Chế độ suy luận (Reasoning Mode)</span>
                            </label>
                            {currentThinking?.badge && (
                              <span
                                style={{
                                  fontSize: 9.5,
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  backgroundColor: "#fff7ed",
                                  color: "#ea580c",
                                  fontWeight: 700,
                                }}
                              >
                                {currentThinking.badge}
                              </span>
                            )}
                          </div>
                          <select
                            value={currentThinkingId || "fast"}
                            onChange={(e) => {
                              onUpdateSelection?.(p.id, { thinking_level_id: e.target.value });
                            }}
                            style={{
                              width: "100%",
                              padding: "6px 8px",
                              borderRadius: 6,
                              border: "1px solid var(--border-default, #cbd5e1)",
                              backgroundColor: "#ffffff",
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--text-primary, #0f172a)",
                              cursor: "pointer",
                              outline: "none",
                            }}
                            title="Chọn chế độ suy luận Mistral (Fast / Think)"
                          >
                            {thinkingLevels.map((t) => (
                              <option key={t.id} value={t.id}>
                                {t.label}
                              </option>
                            ))}
                          </select>
                          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                            {currentThinking?.description || "Fast (phản hồi nhanh) hoặc Think (suy luận sâu cho tác vụ phức tạp)"}
                          </span>
                        </div>

                        {/* Row 2: Deep Research Toggle */}
                        <div
                          onClick={() => onUpdateSelection?.(p.id, { deep_research: !isDeepResearch })}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "8px 12px",
                            borderRadius: 6,
                            border: `1.5px solid ${isDeepResearch ? "#ea580c" : "var(--border-default, #cbd5e1)"}`,
                            backgroundColor: isDeepResearch ? "#fff7ed" : "#ffffff",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          title="Bật/Tắt tính năng Deep Research của Mistral (Tự động kích hoạt skill @deep-research)"
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <SparklesIcon size={16} color={isDeepResearch ? "#ea580c" : "#64748b"} />
                            <div>
                              <div style={{ fontSize: 12, fontWeight: 700, color: isDeepResearch ? "#ea580c" : "var(--text-primary, #0f172a)" }}>
                                Deep Research
                              </div>
                              <div style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)" }}>
                                Tự động kích hoạt kỹ năng @deep-research để tìm kiếm và nghiên cứu chuyên sâu
                              </div>
                            </div>
                          </div>
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 700,
                              padding: "2px 8px",
                              borderRadius: 10,
                              backgroundColor: isDeepResearch ? "#ea580c" : "#e2e8f0",
                              color: isDeepResearch ? "#ffffff" : "#64748b",
                              flexShrink: 0,
                            }}
                          >
                            {isDeepResearch ? "BẬT" : "TẮT"}
                          </span>
                        </div>
                      </div>
                    ) : (
                      /* Other AI Providers (Claude): Row 1 = Model & Reasoning, Row 2 = Mode */
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: thinkingLevels.length > 0 ? "1fr 1fr" : "1fr",
                          gap: 10,
                          flexGrow: 1
                        }}
                      >
                        {/* 1. Model Selector */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <label
                              style={{
                                fontSize: 11,
                                fontWeight: 700,
                                color: "var(--text-secondary)",
                                letterSpacing: "0.4px",
                              }}
                            >
                              Mô hình AI (Model)
                            </label>
                            <span
                              style={{
                                fontSize: 9.5,
                                padding: "1px 5px",
                                borderRadius: 3,
                                backgroundColor: currentModel?.disabled ? "#fef3c7" : "var(--brand-blue)",
                                color: currentModel?.disabled ? "#b45309" : "#ffffff",
                                fontWeight: 700,
                              }}
                            >
                              {currentModel?.badge || "Active"}
                            </span>
                          </div>
                          <select
                            disabled={models.length <= 1}
                            value={currentModelId}
                            onChange={(e) => {
                              const targetM = models.find((m) => m.id === e.target.value);
                              if (targetM?.disabled) return;
                              onUpdateSelection?.(p.id, { model_id: e.target.value });
                            }}
                            style={{
                              width: "100%",
                              padding: "6px 8px",
                              borderRadius: 6,
                              border: "1px solid var(--border-default, #cbd5e1)",
                              backgroundColor: "#ffffff",
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--text-primary, #0f172a)",
                              cursor: "pointer",
                              outline: "none",
                            }}
                            title="Chọn mô hình AI"
                          >
                            {models.map((m) => (
                              <option key={m.id} value={m.id} disabled={m.disabled}>
                                {m.label} {m.disabled ? "— (Upgrade)" : m.badge ? `[${m.badge}]` : ""}
                              </option>
                            ))}
                          </select>
                          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                            {currentModel?.description || ""}
                          </span>
                        </div>

                        {/* 2. Reasoning Picker */}
                        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <label
                              style={{
                                fontSize: 11,
                                fontWeight: 700,
                                color: "var(--text-secondary)",
                                display: "flex",
                                alignItems: "center",
                                gap: 4,
                              }}
                            >
                              <BrainIcon size={12} color="var(--brand-blue)" />
                              <span>Mức suy luận (Reasoning)</span>
                            </label>
                            {currentThinking?.badge && (
                              <span
                                style={{
                                  fontSize: 9.5,
                                  padding: "1px 5px",
                                  borderRadius: 3,
                                  backgroundColor: "#eff6ff",
                                  color: "var(--brand-blue)",
                                  fontWeight: 700,
                                }}
                              >
                                {currentThinking.badge}
                              </span>
                            )}
                          </div>
                          <select
                            disabled={thinkingLevels.length <= 1}
                            value={currentThinkingId}
                            onChange={(e) => {
                              onUpdateSelection?.(p.id, { thinking_level_id: e.target.value });
                            }}
                            style={{
                              width: "100%",
                              padding: "6px 8px",
                              borderRadius: 6,
                              border: "1px solid var(--border-default, #cbd5e1)",
                              backgroundColor: thinkingLevels.length <= 1 ? "#f8fafc" : "#ffffff",
                              fontSize: 12,
                              fontWeight: 600,
                              color: thinkingLevels.length <= 1 ? "#64748b" : "var(--text-primary, #0f172a)",
                              cursor: thinkingLevels.length <= 1 ? "not-allowed" : "pointer",
                              outline: "none",
                            }}
                            title="Chọn mức độ suy luận"
                          >
                            {thinkingLevels.map((t) => (
                              <option key={t.id} value={t.id}>
                                {t.label}
                              </option>
                            ))}
                          </select>
                          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                            {currentThinking?.description || ""}
                          </span>
                        </div>

                        {/* 3. Mode Picker (if applicable) */}
                        {modes.length > 0 && (
                          <div style={{ display: "flex", flexDirection: "column", gap: 3, gridColumn: thinkingLevels.length > 0 ? "1 / -1" : undefined }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                              <label
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: "var(--text-secondary)",
                                  letterSpacing: "0.4px",
                                }}
                              >
                                Chế độ (Mode)
                              </label>
                              {currentMode?.badge && (
                                <span
                                  style={{
                                    fontSize: 9.5,
                                    padding: "1px 5px",
                                    borderRadius: 3,
                                    backgroundColor: "#eff6ff",
                                    color: "var(--brand-blue)",
                                    fontWeight: 700,
                                  }}
                                >
                                  {currentMode.badge}
                                </span>
                              )}
                            </div>
                            <select
                              value={currentModeId}
                              onChange={(e) => {
                                onUpdateSelection?.(p.id, { mode_id: e.target.value });
                              }}
                              style={{
                                width: "100%",
                                padding: "6px 8px",
                                borderRadius: 6,
                                border: "1px solid var(--border-default, #cbd5e1)",
                                backgroundColor: "#ffffff",
                                fontSize: 12,
                                fontWeight: 600,
                                color: "var(--text-primary, #0f172a)",
                                cursor: "pointer",
                                outline: "none",
                              }}
                            >
                              {modes.map((m) => (
                                <option
                                  key={m.id}
                                  value={m.id}
                                >
                                  {m.label}
                                </option>
                              ))}
                            </select>
                            <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                              {currentMode?.description || ""}
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* 3. Supported Data Types & Sync Time */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: 6,
                        paddingTop: 6,
                        borderTop: "1px dashed #e2e8f0",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <span style={{ fontSize: 10.5, fontWeight: 600, color: "var(--text-muted)" }}>
                          Hỗ trợ:
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            padding: "2px 5px",
                            borderRadius: 4,
                            backgroundColor: dataTypes?.image ? "#f0fdf4" : "#f1f5f9",
                            color: dataTypes?.image ? "#15803d" : "#94a3b8",
                            fontWeight: 600,
                            border: `1px solid ${dataTypes?.image ? "#bbf7d0" : "#e2e8f0"}`,
                          }}
                          title={dataTypes?.image ? "Hỗ trợ tải ảnh phân tích" : "Không hỗ trợ tải ảnh"}
                        >
                          📷 Ảnh
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            padding: "2px 5px",
                            borderRadius: 4,
                            backgroundColor: dataTypes?.file ? "#f0fdf4" : "#f1f5f9",
                            color: dataTypes?.file ? "#15803d" : "#94a3b8",
                            fontWeight: 600,
                            border: `1px solid ${dataTypes?.file ? "#bbf7d0" : "#e2e8f0"}`,
                          }}
                          title={dataTypes?.file ? `Hỗ trợ tệp đính kèm (${dataTypes?.max_file_size_mb || 50}MB)` : "Không hỗ trợ tệp"}
                        >
                          📄 Tệp
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            padding: "2px 5px",
                            borderRadius: 4,
                            backgroundColor: voice?.supported ? "#eff6ff" : "#f1f5f9",
                            color: voice?.supported ? "#2563eb" : "#94a3b8",
                            fontWeight: 600,
                            border: `1px solid ${voice?.supported ? "#bfdbfe" : "#e2e8f0"}`,
                          }}
                          title={voice?.supported ? `Hỗ trợ giọng nói (${voice?.mode})` : "Không hỗ trợ giọng nói"}
                        >
                          🎙️ Giọng nói
                        </span>
                      </div>

                      <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                        {caps?.synced_at
                          ? `Cập nhật: ${new Date(caps.synced_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                          : "Mặc định"}
                      </span>
                    </div>
                  </div>

                  {/* Card Actions: Sync DOM + Open Browser */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginTop: 2,
                      gap: 8,
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSyncProvider?.(p.id);
                      }}
                      disabled={isSyncingThis || isSyncingAll}
                      style={{
                        padding: "4px 10px",
                        borderRadius: 5,
                        border: "1px solid #bfdbfe",
                        backgroundColor: isSyncingThis ? "#eff6ff" : "#ffffff",
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--brand-blue)",
                        cursor: isSyncingThis || isSyncingAll ? "not-allowed" : "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 5,
                        transition: "all 0.15s ease",
                      }}
                      title={`Quét lại DOM của ${p.name} để cập nhật mô hình, suy luận và chế độ`}
                    >
                      <RefreshIcon
                        size={12}
                        color="var(--brand-blue)"
                        style={isSyncingThis ? { animation: "spin 1s linear infinite" } : undefined}
                      />
                      <span>{isSyncingThis ? "Đang quét DOM..." : "🔄 Đồng bộ DOM"}</span>
                    </button>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        openProviderBrowser(p.id);
                      }}
                      style={{
                        padding: "4px 10px",
                        borderRadius: 5,
                        border: "1px solid #e2e8f0",
                        backgroundColor: "#ffffff",
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--text-secondary)",
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                      title={`Mở trình duyệt thực tế của ${p.name} để đăng nhập hoặc kiểm tra hồ sơ`}
                    >
                      <span>🌐</span>
                      <span>Mở trình duyệt</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Modal Footer with Apply Button */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: 12,
              paddingTop: 12,
              borderTop: "1px solid var(--border-default)",
            }}
          >
            <button
              type="button"
              className="btn-new-chat-outline"
              onClick={onClose}
              style={{ padding: "8px 16px" }}
            >
              Hủy
            </button>
            <button
              type="button"
              className="btn-composer-send"
              onClick={handleApply}
              disabled={tempSelected.length === 0}
              style={{
                padding: "8px 20px",
                opacity: tempSelected.length === 0 ? 0.45 : 1,
                cursor: tempSelected.length === 0 ? "not-allowed" : "pointer",
              }}
              title={tempSelected.length === 0 ? "Vui lòng chọn ít nhất 1 nhà cung cấp" : undefined}
            >
              <span>Áp dụng{tempSelected.length > 0 ? ` (${tempSelected.length} Models)` : ""}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
