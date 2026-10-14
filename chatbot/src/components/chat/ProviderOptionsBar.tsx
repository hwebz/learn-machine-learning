"use client";

import React, { useState, useRef, useEffect } from "react";
import { ProviderLiveCapabilities, ProviderSelectionConfig, OptionItem } from "../../types/capabilities";
import { BrainIcon, RefreshIcon, ChevronRightIcon, ModelBadgeLogo } from "../icons/Icons";

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
  const models = capabilities?.available_models || [];
  const thinkingLevels = capabilities?.thinking_levels || [];

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

  const modes = capabilities?.modes && capabilities.modes.length > 0
    ? capabilities.modes
    : isCopilot
    ? fallbackCopilotModes
    : [];
  const dataTypes = capabilities?.supported_data_types;
  const voice = capabilities?.voice_chat;

  const currentModel = models.find((m) => m.id === selection.model_id) || models[0];
  const currentThinking = thinkingLevels.find((t) => t.id === selection.thinking_level_id) || thinkingLevels[0];
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
      {/* Left controls: Model, Thinking, Mode */}
      <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: 4 }}>
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              textTransform: "uppercase",
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
                Auto
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
                  return (
                    <div
                      key={m.id}
                      onClick={() => {
                        onUpdateSelection({ model_id: m.id });
                        setIsModelOpen(false);
                      }}
                      style={{
                        padding: "6px 8px",
                        borderRadius: 6,
                        backgroundColor: isSelected ? "var(--brand-blue-light, #eff6ff)" : "transparent",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        gap: 2,
                        transition: "background-color 0.1s",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 12, fontWeight: isSelected ? 700 : 500, color: isSelected ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)" }}>
                          {m.label}
                        </span>
                        {m.badge && (
                          <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#e0e7ff", color: "#3730a3", fontWeight: 600 }}>
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
              disabled={isCopilot}
              onClick={() => !isCopilot && setIsThinkingOpen(!isThinkingOpen)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 8px",
                borderRadius: "var(--radius-sm, 6px)",
                border: "1px solid var(--border-subtle, #cbd5e1)",
                backgroundColor: isCopilot ? "#f8fafc" : (isThinkingOpen ? "var(--brand-blue-light, #eff6ff)" : "transparent"),
                fontSize: 12,
                fontWeight: 600,
                color: isCopilot ? "#64748b" : "var(--text-primary, #0f172a)",
                cursor: isCopilot ? "not-allowed" : "pointer",
              }}
              title={isCopilot ? "Copilot: Mức suy luận được quản lý qua menu Chế độ (Mode)" : "Mức độ suy luận (Thinking Level)"}
            >
              <BrainIcon size={13} color={isCopilot ? "#94a3b8" : "var(--brand-blue, #2563eb)"} />
              <span>{isCopilot ? "Auto (Tự động)" : (currentThinking?.label || "Suy luận")}</span>
              {!isCopilot && <span style={{ fontSize: 10, color: "var(--text-muted, #94a3b8)" }}>▼</span>}
            </button>

            {!isCopilot && isThinkingOpen && (
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
                        onUpdateSelection({ thinking_level_id: t.id });
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
