"use client";

import React, { useState, useEffect, useRef } from "react";
import { ProviderInfo } from "../../types/chat";
import { checkBackendHealth, openProviderBrowser } from "../../lib/api";
import { BrainIcon, ModelBadgeLogo, RefreshIcon } from "../icons/Icons";
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
              const isFreeChatGPT = p.id === "chatgpt" && isFreeAccount;

              // 1. Models: For free account, lock to Auto
              const models = isFreeChatGPT
                ? [
                    {
                      id: "none",
                      label: "Auto (Mặc định)",
                      description: "Tài khoản Free: Mặc định Auto (Tự động)",
                      selected: true,
                      badge: "Free",
                    },
                  ]
                : caps?.available_models && caps.available_models.length > 0
                ? caps.available_models
                : [
                    {
                      id: "auto",
                      label: "Auto (Tự động)",
                      description: "Tự động chọn mô hình phù hợp",
                      selected: true,
                    },
                  ];

              // 2. Reasoning: For free account, lock to Auto
              const thinkingLevels = isFreeAccount
                ? [
                    {
                      id: "auto",
                      label: "Auto (Tự động)",
                      description: "Tài khoản Free: Mặc định Auto",
                      selected: true,
                    },
                  ]
                : caps?.thinking_levels || [];

              // 3. Modes: For ChatGPT, standard or thinking (default is standard)
              const modes =
                p.id === "chatgpt"
                  ? [
                      {
                        id: "standard",
                        label: "Tiêu chuẩn (Standard)",
                        description: "Chế độ trò chuyện tiêu chuẩn nhanh chóng",
                        selected: true,
                      },
                      {
                        id: "thinking",
                        label: "Suy luận (Thinking)",
                        description: "Kích hoạt nút Think để phân tích và trả lời chi tiết",
                        selected: false,
                        badge: "Think",
                      },
                    ]
                  : caps?.modes || [];

              const dataTypes = caps?.supported_data_types;
              const voice = caps?.voice_chat;

              const currentModelId = isFreeChatGPT
                ? "none"
                : sel.model_id || caps?.selected_model_id || models[0]?.id;
              const currentModel = models.find((m) => m.id === currentModelId) || models[0];

              const currentThinkingId = isFreeAccount
                ? "auto"
                : sel.thinking_level_id || caps?.selected_thinking_level_id || thinkingLevels[0]?.id;
              const currentThinking =
                thinkingLevels.find((t) => t.id === currentThinkingId) || thinkingLevels[0];

              const currentModeId = sel.mode_id || caps?.selected_mode_id || modes[0]?.id || "standard";
              const currentMode = modes.find((m) => m.id === currentModeId) || modes[0];

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
                        {isFreeAccount ? "Auto Model (Free Tier)" : p.modelName}
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
                    }}
                  >
                    {/* Grid of Options: Row 1 = Model & Reasoning, Row 2 = Mode */}
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
                              textTransform: "uppercase",
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
                              backgroundColor: isFreeChatGPT ? "#f1f5f9" : "var(--brand-blue)",
                              color: isFreeChatGPT ? "#64748b" : "#ffffff",
                              fontWeight: 700,
                            }}
                          >
                            {isFreeChatGPT ? "Free (Auto)" : (currentModel?.badge || "Active")}
                          </span>
                        </div>
                        <select
                          disabled={isFreeChatGPT}
                          value={isFreeChatGPT ? "none" : currentModelId || "none"}
                          onChange={(e) => onUpdateSelection?.(p.id, { model_id: e.target.value })}
                          style={{
                            width: "100%",
                            padding: "6px 8px",
                            borderRadius: 6,
                            border: "1px solid var(--border-default, #cbd5e1)",
                            backgroundColor: isFreeChatGPT ? "#f8fafc" : "#ffffff",
                            fontSize: 12,
                            fontWeight: 600,
                            color: isFreeChatGPT ? "#64748b" : "var(--text-primary, #0f172a)",
                            cursor: isFreeChatGPT ? "not-allowed" : "pointer",
                            outline: "none",
                          }}
                          title={isFreeChatGPT ? "Mặc định hệ thống tự chọn (Tài khoản Free)" : "Chọn mô hình AI"}
                        >
                          {isFreeChatGPT ? (
                            <option value="none">Auto (Mặc định)</option>
                          ) : (
                            models.map((m) => (
                              <option key={m.id} value={m.id}>
                                {m.label}
                              </option>
                            ))
                          )}
                        </select>
                        <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                          {isFreeChatGPT ? "Mặc định hệ thống tự chọn (Tài khoản Free)" : (currentModel?.description || "")}
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
                          {isFreeAccount && (
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
                              Auto
                            </span>
                          )}
                        </div>
                        <select
                          disabled={isFreeAccount || thinkingLevels.length <= 1}
                          value={currentThinkingId || "auto"}
                          onChange={(e) => onUpdateSelection?.(p.id, { thinking_level_id: e.target.value })}
                          style={{
                            width: "100%",
                            padding: "6px 8px",
                            borderRadius: 6,
                            border: "1px solid var(--border-default, #cbd5e1)",
                            backgroundColor: (isFreeAccount || thinkingLevels.length <= 1) ? "#f8fafc" : "#ffffff",
                            fontSize: 12,
                            fontWeight: 600,
                            color: (isFreeAccount || thinkingLevels.length <= 1) ? "#64748b" : "var(--text-primary, #0f172a)",
                            cursor: (isFreeAccount || thinkingLevels.length <= 1) ? "not-allowed" : "pointer",
                            outline: "none",
                          }}
                          title={isFreeAccount ? "Tài khoản Free: Mặc định Auto (Tự động)" : "Chọn mức độ suy luận"}
                        >
                          {thinkingLevels.map((t) => (
                            <option key={t.id} value={t.id}>
                              {t.label}
                            </option>
                          ))}
                        </select>
                        <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
                          {isFreeAccount ? "Tài khoản Free: Mặc định Auto (Tự động)" : (currentThinking?.description || "")}
                        </span>
                      </div>

                      {/* 3. Mode Picker */}
                      {modes.length > 0 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 3, gridColumn: thinkingLevels.length > 0 ? "1 / -1" : undefined }}>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <label
                              style={{
                                fontSize: 11,
                                fontWeight: 700,
                                color: "var(--text-secondary)",
                                textTransform: "uppercase",
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
                            {currentMode?.description || "Mặc định Tiêu chuẩn (Standard)"}
                          </span>
                        </div>
                      )}
                    </div>

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
