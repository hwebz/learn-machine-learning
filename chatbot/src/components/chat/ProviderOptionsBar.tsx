"use client";

import React, { useState, useRef, useEffect } from "react";
import { ProviderLiveCapabilities, ProviderSelectionConfig, OptionItem } from "../../types/capabilities";
import { BrainIcon, RefreshIcon, ChevronRightIcon, ModelBadgeLogo, SearchIcon, SparklesIcon } from "../icons/Icons";

interface ProviderOptionsBarProps {
  providerName: string;
  providerId: string;
  capabilities: ProviderLiveCapabilities | null;
  selection: ProviderSelectionConfig;
  isLoading: boolean;
  isSyncingAll?: boolean;
  onUpdateSelection: (updates: Partial<ProviderSelectionConfig>) => void;
  onSyncProvider: () => void;
  onSyncAll?: () => void;
}

export function ProviderOptionsBar({
  providerName,
  providerId,
  capabilities,
  selection,
  isLoading,
  isSyncingAll,
  onUpdateSelection,
  onSyncProvider,
  onSyncAll,
}: ProviderOptionsBarProps) {
  const [isModelOpen, setIsModelOpen] = useState(false);
  const [isThinkingOpen, setIsThinkingOpen] = useState(false);
  const [isModeOpen, setIsModeOpen] = useState(false);

  const modelRef = useRef<HTMLDivElement>(null);
  const thinkingRef = useRef<HTMLDivElement>(null);
  const modeRef = useRef<HTMLDivElement>(null);

  // Close popovers when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (modelRef.current && !modelRef.current.contains(e.target as Node)) {
        setIsModelOpen(false);
      }
      if (thinkingRef.current && !thinkingRef.current.contains(e.target as Node)) {
        setIsThinkingOpen(false);
      }
      if (modeRef.current && !modeRef.current.contains(e.target as Node)) {
        setIsModeOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isCopilot = providerId === "copilot";
  const isChatGPT = providerId === "chatgpt";
  const isDeepSeek = providerId === "deepseek";
  const isClaude = providerId === "claude";
  const isPerplexity = providerId === "perplexity";
  const isKimi = providerId === "kimi";
  const isGemini = providerId === "gemini";

  const isDeepThinking = selection.deep_thinking ?? capabilities?.deep_thinking ?? false;
  const isWebSearch = selection.web_search ?? capabilities?.web_search ?? true;
  const isDeepResearch = selection.deep_research ?? capabilities?.deep_research ?? false;
  const researchMode = selection.research_mode ?? capabilities?.research_mode ?? "normal";
  const isResearchAdvanced = researchMode === "advanced";

  const claudeFallbackModels: OptionItem[] = [
    { id: "claude-sonnet-5.5", label: "Sonnet 5.5", description: "Cân bằng hoàn hảo giữa trí tuệ và tốc độ", selected: true, badge: "Sonnet", disabled: false },
    { id: "claude-haiku-5.5", label: "Haiku 5.5", description: "Phản hồi nhanh nhất cho tác vụ ngắn gọn", selected: false, badge: "Haiku", disabled: false },
    { id: "claude-opus-5.5", label: "Opus 5.5", description: "Dành cho tài khoản Pro (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
    { id: "claude-fable-5.1", label: "Fable 5.1", description: "Dành cho các thử thách khó khăn nhất (Yêu cầu nâng cấp gói)", selected: false, badge: "Upgrade", disabled: true },
  ];

  const perplexityFallbackModels: OptionItem[] = [
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

  const kimiFallbackModels: OptionItem[] = [
    { id: "instant", label: "Instant", description: "Fast chat, quick replies (Phản hồi nhanh)", selected: true, disabled: false, badge: "Instant" },
    { id: "k3", label: "K3", description: "Chat & Agent, flagship all-rounder (Toàn diện, suy luận mạnh)", selected: false, disabled: false, badge: "K3" },
    { id: "k2.8", label: "K2.8", description: "Preview · Well-rounded and efficient for everyday tasks", selected: false, disabled: false, badge: "Preview" },
  ];

  const kimiFallbackThinking: OptionItem[] = [
    { id: "standard", label: "Standard", description: "Suy luận tiêu chuẩn, phản hồi cân bằng", selected: false, disabled: false, badge: "Standard" },
    { id: "high", label: "High", description: "Suy luận chuyên sâu cao nhất", selected: true, disabled: false, badge: "High" },
  ];

  const models: OptionItem[] = isDeepSeek || isCopilot || isChatGPT
    ? []
    : isClaude
      ? (capabilities?.available_models && capabilities.available_models.length > 0 && !capabilities.available_models.some((m) => m.id === "default")
        ? capabilities.available_models.map((m) => {
          const isUpgrade = m.id === "claude-opus-5.5" || m.id === "claude-fable-5.1" || m.disabled || m.metadata?.upgrade;
          return {
            ...m,
            disabled: isUpgrade,
            badge: isUpgrade ? "Upgrade" : m.badge,
          };
        })
        : claudeFallbackModels)
      : isPerplexity
        ? (capabilities?.available_models && capabilities.available_models.length > 0 && !capabilities.available_models.some((m) => m.id === "default")
          ? capabilities.available_models.map((m) => ({
            ...m,
            disabled: m.id !== "auto",
            badge: m.id === "auto" ? "Auto" : (m.badge || "Pro"),
          }))
          : perplexityFallbackModels)
        : isKimi
          ? (capabilities?.available_models && capabilities.available_models.length > 0 && !capabilities.available_models.some((m) => m.id === "default")
            ? capabilities.available_models
            : kimiFallbackModels).map((m) => {
              const isInstantDisabled = isDeepResearch && m.id === "instant";
              return {
                ...m,
                disabled: isInstantDisabled || m.disabled,
                badge: isInstantDisabled ? "Không hỗ trợ DR" : m.badge,
              };
            })
          : capabilities?.available_models && capabilities.available_models.length > 0
            ? capabilities.available_models
            : providerId === "gemini"
              ? [
                { id: "gemini-3.8-flash", label: "3.8 Flash", description: "Trợ giúp toàn diện", selected: true, badge: "Flash" },
                { id: "gemini-3.5-flash-lite", label: "3.5 Flash-Lite", description: "Câu trả lời nhanh nhất", selected: false, badge: "Lite" },
                { id: "gemini-3.1-pro", label: "3.1 Pro", description: "Suy luận nâng cao", selected: false, badge: "Pro" },
                { id: "gemini-4-argon", label: "4 Argon", description: "Nhiệm vụ phức tạp", selected: false, badge: "Argon" },
              ]
              : providerId === "qwen"
                ? [
                  { id: "qwen-3.8-max", label: "Qwen3.8-Max (Flagship)", description: "Mô hình cờ đầu thế hệ mới nhất", selected: true, badge: "Max" },
                  { id: "qwen-3.7-plus", label: "Qwen3.7-Plus (High Performance)", description: "Mô hình hiệu năng cao", selected: false, badge: "Plus" },
                  { id: "qwen-3.8-omni-flash", label: "Qwen3.8-Omni-Flash (Multimodal)", description: "Mô hình đa phương tiện tự nhiên", selected: false, badge: "Omni" },
                ]
                : [];

  const thinkingLevels: OptionItem[] = isDeepSeek || isCopilot || isChatGPT || isPerplexity
    ? []
    : isClaude
      ? (capabilities?.thinking_levels && capabilities.thinking_levels.length > 0 && !capabilities.thinking_levels.some((t) => t.id === "auto")
        ? capabilities.thinking_levels
        : [
          { id: "medium", label: "Medium (Recommended)", description: "Khuyên dùng - Cân bằng độ sâu và giới hạn sử dụng", selected: true, badge: "Med" },
          { id: "low", label: "Low", description: "Thấp - Phản hồi nhanh và tiết kiệm giới hạn", selected: false, badge: "Low" },
          { id: "high", label: "High", description: "Cao - Phân tích đa bước kỹ lưỡng cho bài toán hóc búa", selected: false, badge: "High" },
          { id: "extra", label: "Extra", description: "Rất cao - Suy luận chuyên sâu cho nghiên cứu phức tạp", selected: false, badge: "Extra" },
          { id: "max", label: "Max", description: "Tối đa - 8x hoặc nhiều hơn mức sử dụng giới hạn", selected: false, badge: "Max" },
        ])
      : isKimi
        ? (capabilities?.thinking_levels && capabilities.thinking_levels.length > 0 && !capabilities.thinking_levels.some((t) => t.id === "auto")
          ? capabilities.thinking_levels
          : kimiFallbackThinking)
        : capabilities?.thinking_levels && capabilities.thinking_levels.length > 0
          ? capabilities.thinking_levels
          : providerId === "gemini"
            ? [
              { id: "low", label: "Thấp (Nhanh chóng & hiệu quả)", description: "Nhanh chóng và hiệu quả", selected: true, badge: "Low" },
              { id: "medium", label: "Trung bình (Độ sâu cân bằng)", description: "Độ sâu cân bằng", selected: false, badge: "Med" },
              { id: "high", label: "Cao (Cực kỳ kỹ lưỡng)", description: "Cực kỳ kỹ lưỡng", selected: false, badge: "High" },
            ]
            : providerId === "qwen"
              ? [
                { id: "auto", label: "Auto (Tự động cân bằng)", description: "Tự động điều chỉnh mức độ suy luận", selected: true, badge: "Auto" },
                { id: "thinking", label: "Thinking (Suy luận sâu đa bước)", description: "Kích hoạt chuỗi tư duy mở rộng", selected: false, badge: "Think" },
                { id: "fast", label: "Fast (Phản hồi nhanh)", description: "Bỏ qua tư duy đa bước", selected: false, badge: "Fast" },
              ]
              : [];

  const fallbackCopilotModes: OptionItem[] = [
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
  ];

  const modes = (providerId === "gemini" || providerId === "qwen" || providerId === "claude" || providerId === "deepseek" || providerId === "chatgpt" || providerId === "perplexity" || providerId === "kimi")
    ? []
    : capabilities?.modes && capabilities.modes.length > 0
      ? capabilities.modes
      : isCopilot
        ? fallbackCopilotModes
        : [];
  const dataTypes = capabilities?.supported_data_types;
  const voice = capabilities?.voice_chat;

  const selectableModels = models.filter((m) => !m.disabled);
  const currentModel = isPerplexity
    ? (models.find((m) => m.id === "auto") || models[0])
    : (models.find((m) => m.id === selection.model_id && !m.disabled) || selectableModels[0] || models[0]);
  const isQwen = providerId === "qwen";
  const currentThinking = (isQwen && isDeepResearch)
    ? { id: "auto", label: "Auto", badge: "Khóa", description: "Deep Research tự động điều chỉnh mức độ suy luận (mặc định Auto)" }
    : isClaude
      ? (thinkingLevels.find((t) => t.id === selection.thinking_level_id && t.id !== "auto") || thinkingLevels.find((t) => t.id === "medium") || thinkingLevels[0])
      : (thinkingLevels.find((t) => t.id === selection.thinking_level_id) || thinkingLevels[0]);
  const currentMode = modes.find((m) => m.id === selection.mode_id) || modes[0];

  const formatSyncTime = (ts?: string) => {
    if (!ts) return "Chưa đồng bộ";
    try {
      const date = new Date(ts);
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "Vừa xong";
    }
  };

  return (
    <div
      className="provider-options-bar"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 8,
        padding: "6px 12px",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--bg-card, #ffffff)",
        border: "1px solid var(--border-default, #e2e8f0)",
        marginBottom: 8,
        boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
      }}
    >
      {/* Left controls: Model, Thinking, Mode, or DeepSeek Toggles */}
      <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: 4 }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.5px",
              color: "var(--text-muted, #64748b)",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <ModelBadgeLogo type={providerId} size={14} />
            {providerName}
          </span>
          {capabilities?.is_live_dom ? (
            <span
              style={{
                fontSize: 9.5,
                fontWeight: 700,
                color: "#16a34a",
                backgroundColor: "#dcfce7",
                padding: "1px 5px",
                borderRadius: 4,
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
                padding: "1px 5px",
                borderRadius: 4,
              }}
              title="Tùy chọn mặc định — bấm nút Đồng bộ DOM để quét trực tiếp"
            >
              CACHED
            </span>
          )}
        </div>

        {/* DeepSeek 2 Toggles: DeepThink (R1) and Web Search */}
        {isDeepSeek && (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {/* 1. DeepThink Toggle */}
            <button
              type="button"
              onClick={() => onUpdateSelection({ deep_thinking: !isDeepThinking })}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isDeepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt mô hình suy luận sâu DeepSeek-R1 (Chain of Thought)"
            >
              <BrainIcon size={13} color={isDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
              <span>DeepThink (R1)</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isDeepThinking ? "var(--brand-blue, #2563eb)" : "#f1f5f9",
                  color: isDeepThinking ? "#ffffff" : "#64748b",
                  fontWeight: 700,
                }}
              >
                {isDeepThinking ? "ON" : "OFF"}
              </span>
            </button>

            {/* 2. Web Search Toggle */}
            <button
              type="button"
              onClick={() => onUpdateSelection({ web_search: !isWebSearch })}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isWebSearch ? "#059669" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isWebSearch ? "#ecfdf5" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: isWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt tính năng tìm kiếm Web thời gian thực của DeepSeek"
            >
              <SearchIcon size={12} color={isWebSearch ? "#059669" : "#64748b"} />
              <span>Search (Web)</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isWebSearch ? "#059669" : "#f1f5f9",
                  color: isWebSearch ? "#ffffff" : "#64748b",
                  fontWeight: 700,
                }}
              >
                {isWebSearch ? "ON" : "OFF"}
              </span>
            </button>
          </div>
        )}

        {/* ChatGPT 3 Toggles: Web Search, Deep Research, Thinking */}
        {isChatGPT && (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {/* 1. Web Search Toggle */}
            <button
              type="button"
              onClick={() => onUpdateSelection({ web_search: !isWebSearch })}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isWebSearch ? "#059669" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isWebSearch ? "#ecfdf5" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: isWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt tính năng tìm kiếm Web thời gian thực (+ Web search)"
            >
              <SearchIcon size={12} color={isWebSearch ? "#059669" : "#64748b"} />
              <span>Web Search</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isWebSearch ? "#059669" : "#f1f5f9",
                  color: isWebSearch ? "#ffffff" : "#64748b",
                  fontWeight: 700,
                }}
              >
                {isWebSearch ? "ON" : "OFF"}
              </span>
            </button>

            {/* 2. Deep Research Toggle */}
            <button
              type="button"
              onClick={() => onUpdateSelection({ deep_research: !isDeepResearch })}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isDeepResearch ? "#7c3aed" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: isDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt tính năng Deep Research (+ Deep research)"
            >
              <SparklesIcon size={13} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
              <span>Deep Research</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isDeepResearch ? "#7c3aed" : "#f1f5f9",
                  color: isDeepResearch ? "#ffffff" : "#64748b",
                  fontWeight: 700,
                }}
              >
                {isDeepResearch ? "ON" : "OFF"}
              </span>
            </button>

            {/* 3. Thinking Toggle */}
            <button
              type="button"
              onClick={() => onUpdateSelection({ deep_thinking: !isDeepThinking })}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isDeepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt chế độ suy luận chuyên sâu (Nút Think)"
            >
              <BrainIcon size={13} color={isDeepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
              <span>Thinking</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isDeepThinking ? "var(--brand-blue, #2563eb)" : "#f1f5f9",
                  color: isDeepThinking ? "#ffffff" : "#64748b",
                  fontWeight: 700,
                }}
              >
                {isDeepThinking ? "ON" : "OFF"}
              </span>
            </button>
          </div>
        )}

        {/* Perplexity Disabled Thinking Toggle */}
        {isPerplexity && (
          <button
            type="button"
            disabled
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              padding: "4px 9px",
              borderRadius: "var(--radius-sm, 6px)",
              border: "1px solid var(--border-subtle, #cbd5e1)",
              backgroundColor: "#f8fafc",
              fontSize: 12,
              fontWeight: 600,
              color: "var(--text-muted, #94a3b8)",
              cursor: "not-allowed",
              opacity: 0.7,
            }}
            title="Tính năng Thinking bị khóa trên tài khoản Perplexity miễn phí"
          >
            <BrainIcon size={13} color="#94a3b8" />
            <span>Thinking</span>
            <span
              style={{
                fontSize: 9.5,
                padding: "1px 4px",
                borderRadius: 3,
                backgroundColor: "#e2e8f0",
                color: "#94a3b8",
                fontWeight: 700,
              }}
            >
              OFF (LOCKED)
            </span>
          </button>
        )}

        {/* 1. Model Selector Dropdown */}
        {models.length > 0 && (
          <div ref={modelRef} style={{ position: "relative" }}>
            <button
              type="button"
              disabled={isCopilot}
              onClick={() => !isCopilot && setIsModelOpen(!isModelOpen)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: "1px solid var(--border-subtle, #cbd5e1)",
                backgroundColor: isCopilot ? "#f8fafc" : (isModelOpen ? "var(--brand-blue-light, #eff6ff)" : "transparent"),
                fontSize: 12,
                fontWeight: 600,
                color: isCopilot ? "#64748b" : "var(--text-primary, #0f172a)",
                cursor: isCopilot ? "not-allowed" : "pointer",
                transition: "all 0.15s ease",
              }}
              title={isCopilot ? "Copilot: Mô hình được quản lý qua menu Chế độ (Mode)" : "Chọn mô hình AI (Model Selector)"}
            >
              <span>{isCopilot ? "Auto (Mặc định)" : (currentModel?.label || "Chọn Model")}</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isCopilot ? "#e2e8f0" : "var(--brand-blue, #2563eb)",
                  color: isCopilot ? "#475569" : "#ffffff",
                  fontWeight: 700,
                }}
              >
                {currentModel?.badge || (isCopilot ? "Auto" : "Active")}
              </span>
              {!isCopilot && <span style={{ fontSize: 10, color: "var(--text-muted, #94a3b8)" }}>▼</span>}
            </button>

            {!isCopilot && isModelOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  marginTop: 4,
                  width: 260,
                  backgroundColor: "#ffffff",
                  border: "1px solid var(--border-default, #e2e8f0)",
                  borderRadius: "var(--radius-md, 8px)",
                  boxShadow: "0 8px 20px rgba(0,0,0,0.1)",
                  zIndex: 60,
                  padding: 4,
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                }}
              >
                <div style={{ padding: "4px 8px", fontSize: 11, fontWeight: 700, color: "var(--text-muted, #64748b)", borderBottom: "1px solid #f1f5f9" }}>
                  MÔ HÌNH KHẢ DỤNG ({models.length})
                </div>
                {models.map((m) => {
                  const isSelected = m.id === currentModel?.id;
                  const isDisabled = m.disabled;
                  return (
                    <div
                      key={m.id}
                      onClick={() => {
                        if (isDisabled) return;
                        if (providerId === "deepseek") {
                          if (m.id === "deepseek-r1") {
                            onUpdateSelection({ model_id: m.id, thinking_level_id: "deepthink" });
                          } else {
                            onUpdateSelection({ model_id: m.id, thinking_level_id: "standard" });
                          }
                        } else {
                          onUpdateSelection({ model_id: m.id });
                        }
                        setIsModelOpen(false);
                      }}
                      style={{
                        padding: "6px 8px",
                        borderRadius: 6,
                        backgroundColor: isSelected ? "var(--brand-blue-light, #eff6ff)" : "transparent",
                        cursor: isDisabled ? "not-allowed" : "pointer",
                        opacity: isDisabled ? 0.6 : 1,
                        display: "flex",
                        flexDirection: "column",
                        gap: 2,
                        transition: "background-color 0.1s",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 12, fontWeight: isSelected ? 700 : 500, color: isDisabled ? "var(--text-muted, #94a3b8)" : isSelected ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)" }}>
                          {m.label}
                        </span>
                        {m.badge && (
                          <span
                            style={{
                              fontSize: 9.5,
                              padding: "1px 5px",
                              borderRadius: 3,
                              backgroundColor: isDisabled ? "#fef3c7" : "#e0e7ff",
                              color: isDisabled ? "#b45309" : "#3730a3",
                              fontWeight: 600,
                            }}
                          >
                            {m.badge}
                          </span>
                        )}
                      </div>
                      {m.description && (
                        <span style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)", lineHeight: 1.3 }}>
                          {m.description}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* 2. Thinking Level Selector */}
        {thinkingLevels.length > 0 && (
          <div ref={thinkingRef} style={{ position: "relative" }}>
            <button
              type="button"
              disabled={isCopilot || (isQwen && isDeepResearch)}
              onClick={() => !isCopilot && !(isQwen && isDeepResearch) && setIsThinkingOpen(!isThinkingOpen)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 8px",
                borderRadius: "var(--radius-sm, 6px)",
                border: "1px solid var(--border-subtle, #cbd5e1)",
                backgroundColor: (isCopilot || (isQwen && isDeepResearch)) ? "#f8fafc" : (isThinkingOpen ? "var(--brand-blue-light, #eff6ff)" : "transparent"),
                fontSize: 12,
                fontWeight: 600,
                color: (isCopilot || (isQwen && isDeepResearch)) ? "#64748b" : "var(--text-primary, #0f172a)",
                cursor: (isCopilot || (isQwen && isDeepResearch)) ? "not-allowed" : "pointer",
                opacity: (isQwen && isDeepResearch) ? 0.75 : 1,
              }}
              title={isCopilot ? "Copilot: Mức suy luận được quản lý qua menu Chế độ (Mode)" : (isQwen && isDeepResearch) ? "Deep Research không cho phép chỉnh mức độ suy luận (mặc định Auto)" : "Mức độ suy luận (Thinking Level)"}
            >
              <BrainIcon size={13} color={(isCopilot || (isQwen && isDeepResearch)) ? "#94a3b8" : "var(--brand-blue, #2563eb)"} />
              <span>{isCopilot ? "Auto" : (isQwen && isDeepResearch) ? "Auto" : (currentThinking?.label || "Suy luận")}</span>
              {!(isCopilot || (isQwen && isDeepResearch)) && <span style={{ fontSize: 10, color: "var(--text-muted, #94a3b8)" }}>▼</span>}
            </button>

            {!isCopilot && !(isQwen && isDeepResearch) && isThinkingOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  marginTop: 4,
                  width: 220,
                  backgroundColor: "#ffffff",
                  border: "1px solid var(--border-default, #e2e8f0)",
                  borderRadius: "var(--radius-md, 8px)",
                  boxShadow: "0 8px 20px rgba(0,0,0,0.1)",
                  zIndex: 60,
                  padding: 4,
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                }}
              >
                <div style={{ padding: "4px 8px", fontSize: 11, fontWeight: 700, color: "var(--text-muted, #64748b)", borderBottom: "1px solid #f1f5f9" }}>
                  MỨC ĐỘ SUY LUẬN (THINKING EFFORT)
                </div>
                {thinkingLevels.map((t) => {
                  const isSelected = t.id === currentThinking?.id;
                  return (
                    <div
                      key={t.id}
                      onClick={() => {
                        if (providerId === "deepseek") {
                          if (t.id === "deepthink") {
                            onUpdateSelection({ thinking_level_id: t.id, model_id: "deepseek-r1" });
                          } else {
                            onUpdateSelection({ thinking_level_id: t.id, model_id: "deepseek-v3" });
                          }
                        } else {
                          onUpdateSelection({ thinking_level_id: t.id });
                        }
                        setIsThinkingOpen(false);
                      }}
                      style={{
                        padding: "6px 8px",
                        borderRadius: 6,
                        backgroundColor: isSelected ? "var(--brand-blue-light, #eff6ff)" : "transparent",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        gap: 2,
                      }}
                    >
                      <span style={{ fontSize: 12, fontWeight: isSelected ? 700 : 500, color: isSelected ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)" }}>
                        {t.label}
                      </span>
                      {t.description && (
                        <span style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)" }}>
                          {t.description}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Kimi Deep Research Toggle Button */}
        {isKimi && (
          <button
            type="button"
            onClick={() => {
              const nextDr = !isDeepResearch;
              const updates: Partial<ProviderSelectionConfig> = { deep_research: nextDr };
              if (nextDr && (currentModel?.id === "instant" || !currentModel?.id || currentModel?.id === "default")) {
                updates.model_id = "k3";
              }
              onUpdateSelection(updates);
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              padding: "4px 9px",
              borderRadius: "var(--radius-sm, 6px)",
              border: `1px solid ${isDeepResearch ? "#7c3aed" : "var(--border-subtle, #cbd5e1)"}`,
              backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
              fontSize: 12,
              fontWeight: 600,
              color: isDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            title="Bật/Tắt chế độ Deep Research trên Kimi"
          >
            <SparklesIcon size={13} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
            <span>Deep Research</span>
            <span
              style={{
                fontSize: 9.5,
                padding: "1px 4px",
                borderRadius: 3,
                backgroundColor: isDeepResearch ? "#7c3aed" : "#f1f5f9",
                color: isDeepResearch ? "#ffffff" : "#64748b",
                fontWeight: 700,
              }}
            >
              {isDeepResearch ? "ON" : "OFF"}
            </span>
          </button>
        )}

        {/* Qwen Web Search, Deep Research & Research Mode Toggles */}
        {isQwen && (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {/* 1. Web Search Toggle */}
            <button
              type="button"
              onClick={() => onUpdateSelection({ web_search: !isWebSearch })}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isWebSearch ? "#059669" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isWebSearch ? "#ecfdf5" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: isWebSearch ? "#059669" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt tính năng tìm kiếm Web trên Qwen (+ Web search)"
            >
              <SearchIcon size={12} color={isWebSearch ? "#059669" : "#64748b"} />
              <span>Web Search</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isWebSearch ? "#059669" : "#f1f5f9",
                  color: isWebSearch ? "#ffffff" : "#64748b",
                  fontWeight: 700,
                }}
              >
                {isWebSearch ? "ON" : "OFF"}
              </span>
            </button>

            {/* 2. Deep Research Toggle Button */}
            <button
              type="button"
              onClick={() => {
                const nextDr = !isDeepResearch;
                const updates: Partial<ProviderSelectionConfig> = {
                  deep_research: nextDr,
                  ...(nextDr ? { thinking_level_id: "auto" } : {}),
                };
                onUpdateSelection(updates);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isDeepResearch ? "#7c3aed" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: isDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt chế độ Deep Research trên Qwen (+ Deep Research)"
            >
              <SparklesIcon size={13} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
              <span>Deep Research</span>
              <span
                style={{
                  fontSize: 9.5,
                  padding: "1px 4px",
                  borderRadius: 3,
                  backgroundColor: isDeepResearch ? "#7c3aed" : "#f1f5f9",
                  color: isDeepResearch ? "#ffffff" : "#64748b",
                  fontWeight: 700,
                }}
              >
                {isDeepResearch ? "ON" : "OFF"}
              </span>
            </button>

            {/* 2.1 Research Mode Toggle (when Deep Research is ON) */}
            {isDeepResearch && (
              <button
                type="button"
                onClick={() => {
                  const nextMode = isResearchAdvanced ? "normal" : "advanced";
                  onUpdateSelection({ research_mode: nextMode });
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 5,
                  padding: "4px 9px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1px solid ${isResearchAdvanced ? "#9333ea" : "var(--border-subtle, #cbd5e1)"}`,
                  backgroundColor: isResearchAdvanced ? "#f3e8ff" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: isResearchAdvanced ? "#9333ea" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title={isResearchAdvanced
                  ? "Advanced: Devoting extra time to a deeper analysis"
                  : "Normal: Fast, reliable responses for quick tasks"}
              >
                <SparklesIcon size={12} color={isResearchAdvanced ? "#9333ea" : "#64748b"} />
                <span>{isResearchAdvanced ? "Advanced" : "Normal"}</span>
                <span
                  style={{
                    fontSize: 9.5,
                    padding: "1px 4px",
                    borderRadius: 3,
                    backgroundColor: isResearchAdvanced ? "#9333ea" : "#f1f5f9",
                    color: isResearchAdvanced ? "#ffffff" : "#64748b",
                    fontWeight: 700,
                  }}
                >
                  {isResearchAdvanced ? "ON" : "OFF"}
                </span>
              </button>
            )}
          </div>
        )}

        {/* Gemini Deep Research Toggle Button */}
        {isGemini && (
          <button
            type="button"
            onClick={() => onUpdateSelection({ deep_research: !isDeepResearch })}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              padding: "4px 9px",
              borderRadius: "var(--radius-sm, 6px)",
              border: `1px solid ${isDeepResearch ? "#7c3aed" : "var(--border-subtle, #cbd5e1)"}`,
              backgroundColor: isDeepResearch ? "#f5f3ff" : "#ffffff",
              fontSize: 12,
              fontWeight: 600,
              color: isDeepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            title="Bật/Tắt chế độ Deep Research trên Google Gemini (+ Deep Research)"
          >
            <SparklesIcon size={13} color={isDeepResearch ? "#7c3aed" : "#64748b"} />
            <span>Deep Research</span>
            <span
              style={{
                fontSize: 9.5,
                padding: "1px 4px",
                borderRadius: 3,
                backgroundColor: isDeepResearch ? "#7c3aed" : "#f1f5f9",
                color: isDeepResearch ? "#ffffff" : "#64748b",
                fontWeight: 700,
              }}
            >
              {isDeepResearch ? "ON" : "OFF"}
            </span>
          </button>
        )}

        {/* 3. Mode Selector */}
        {modes.length > 0 && (
          <div ref={modeRef} style={{ position: "relative" }}>
            <button
              type="button"
              onClick={() => setIsModeOpen(!isModeOpen)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 8px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1px solid ${isCopilot ? "var(--brand-blue, #2563eb)" : "var(--border-subtle, #cbd5e1)"}`,
                backgroundColor: isModeOpen ? "var(--brand-blue-light, #eff6ff)" : (isCopilot ? "rgba(37, 99, 235, 0.05)" : "transparent"),
                fontSize: 12,
                fontWeight: 600,
                color: isCopilot ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)",
                cursor: "pointer",
              }}
              title={isCopilot ? "Chọn mô hình Copilot (Auto, Quick, Think Deeper, GPT-5.6 Sol)" : "Chế độ nghiên cứu / Công cụ hỗ trợ"}
            >
              <span>{currentMode?.label || "Chế độ"}</span>
              {currentMode?.badge && (
                <span
                  style={{
                    fontSize: 9,
                    padding: "1px 4px",
                    borderRadius: 3,
                    backgroundColor: isCopilot ? "#dbeafe" : "#fef3c7",
                    color: isCopilot ? "#1d4ed8" : "#92400e",
                    fontWeight: 700,
                  }}
                >
                  {currentMode.badge}
                </span>
              )}
              <span style={{ fontSize: 10, color: isCopilot ? "var(--brand-blue, #2563eb)" : "var(--text-muted, #94a3b8)" }}>▼</span>
            </button>

            {isModeOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  marginTop: 4,
                  width: isCopilot ? 280 : 240,
                  backgroundColor: "#ffffff",
                  border: "1px solid var(--border-default, #e2e8f0)",
                  borderRadius: "var(--radius-md, 8px)",
                  boxShadow: "0 8px 20px rgba(0,0,0,0.1)",
                  zIndex: 60,
                  padding: 4,
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                }}
              >
                <div style={{ padding: "4px 8px", fontSize: 11, fontWeight: 700, color: "var(--text-muted, #64748b)", borderBottom: "1px solid #f1f5f9" }}>
                  {isCopilot ? `MÔ HÌNH COPILOT (${modes.length})` : `CHẾ ĐỘ & CÔNG CỤ (${modes.length})`}
                </div>
                {modes.map((m) => {
                  const isSelected = m.id === currentMode?.id;
                  return (
                    <div
                      key={m.id}
                      onClick={() => {
                        onUpdateSelection({ mode_id: m.id });
                        setIsModeOpen(false);
                      }}
                      style={{
                        padding: "6px 8px",
                        borderRadius: 6,
                        backgroundColor: isSelected ? "var(--brand-blue-light, #eff6ff)" : "transparent",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        gap: 2,
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 12, fontWeight: isSelected ? 700 : 500, color: isSelected ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)" }}>
                          {m.label}
                        </span>
                        {m.badge && (
                          <span
                            style={{
                              fontSize: 9,
                              padding: "1px 4px",
                              borderRadius: 3,
                              backgroundColor: isCopilot ? "#dbeafe" : "#fef3c7",
                              color: isCopilot ? "#1d4ed8" : "#92400e",
                              fontWeight: 700,
                            }}
                          >
                            {m.badge}
                          </span>
                        )}
                      </div>
                      {m.description && (
                        <span style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)", lineHeight: 1.25 }}>
                          {m.description}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right controls: Supported data types badges & Sync buttons */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {/* Supported Data Types Indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }} title="Định dạng dữ liệu mô hình hỗ trợ tải lên">
          <span style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)", fontWeight: 600 }}>
            Hỗ trợ:
          </span>
          <span
            style={{
              fontSize: 10,
              padding: "2px 6px",
              borderRadius: 4,
              backgroundColor: dataTypes?.image ? "#f0fdf4" : "#f1f5f9",
              color: dataTypes?.image ? "#15803d" : "#94a3b8",
              fontWeight: 600,
              border: `1px solid ${dataTypes?.image ? "#bbf7d0" : "#e2e8f0"}`,
            }}
            title={dataTypes?.image ? "Hỗ trợ tải ảnh" : "Không hỗ trợ tải ảnh"}
          >
            📷 Ảnh
          </span>
          <span
            style={{
              fontSize: 10,
              padding: "2px 6px",
              borderRadius: 4,
              backgroundColor: dataTypes?.file ? "#f0fdf4" : "#f1f5f9",
              color: dataTypes?.file ? "#15803d" : "#94a3b8",
              fontWeight: 600,
              border: `1px solid ${dataTypes?.file ? "#bbf7d0" : "#e2e8f0"}`,
            }}
            title={dataTypes?.file ? "Hỗ trợ tài liệu / tệp tin (PDF, TXT, Code)" : "Không hỗ trợ tệp"}
          >
            📄 Tệp
          </span>
          <span
            style={{
              fontSize: 10,
              padding: "2px 6px",
              borderRadius: 4,
              backgroundColor: voice?.supported ? "#eff6ff" : "#f1f5f9",
              color: voice?.supported ? "#1d4ed8" : "#94a3b8",
              fontWeight: 600,
              border: `1px solid ${voice?.supported ? "#bfdbfe" : "#e2e8f0"}`,
            }}
            title={voice?.supported ? "Hỗ trợ nhập liệu giọng nói (Voice-to-Text) bất đồng bộ" : "Không hỗ trợ giọng nói"}
          >
            🎙️ Giọng nói
          </span>
        </div>

        {/* Per-provider Sync button */}
        <button
          type="button"
          onClick={onSyncProvider}
          disabled={isLoading}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            padding: "3px 8px",
            borderRadius: "var(--radius-sm, 6px)",
            border: "1px solid var(--border-default, #cbd5e1)",
            backgroundColor: isLoading ? "#f1f5f9" : "#ffffff",
            fontSize: 11,
            fontWeight: 600,
            color: "var(--text-primary, #0f172a)",
            cursor: isLoading ? "not-allowed" : "pointer",
            transition: "all 0.15s ease",
          }}
          title={`Quét lại DOM của ${providerName} để làm mới tùy chọn (Lần cuối: ${formatSyncTime(capabilities?.synced_at)})`}
        >
          <RefreshIcon size={12} color={isLoading ? "var(--brand-blue, #2563eb)" : "currentColor"} />
          <span>{isLoading ? "Đang quét DOM..." : "Đồng bộ DOM"}</span>
        </button>

        {/* Global Sync All button */}
        {onSyncAll && (
          <button
            type="button"
            onClick={onSyncAll}
            disabled={isSyncingAll}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "3px 8px",
              borderRadius: "var(--radius-sm, 6px)",
              border: "1px solid #bfdbfe",
              backgroundColor: isSyncingAll ? "#eff6ff" : "var(--brand-blue-light, #f0f7ff)",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--brand-blue, #2563eb)",
              cursor: isSyncingAll ? "not-allowed" : "pointer",
            }}
            title="Đồng bộ lại toàn bộ tùy chọn từ DOM của tất cả các AI Providers"
          >
            <RefreshIcon size={12} color="var(--brand-blue, #2563eb)" />
            <span>{isSyncingAll ? "Đang quét tất cả..." : "Sync All DOM"}</span>
          </button>
        )}
      </div>
    </div>
  );
}
