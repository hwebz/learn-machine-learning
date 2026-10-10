"use client";

import React, { useState, useEffect } from "react";
import { ProviderInfo } from "../../types/chat";
import { checkBackendHealth } from "../../lib/api";
import { BrainIcon, ModelBadgeLogo } from "../icons/Icons";

interface ProviderModalProps {
  isOpen: boolean;
  onClose: () => void;
  providers: ProviderInfo[];
  selectedProviderIds: string[];
  onToggleProvider: (id: string) => void;
  onSelectMultipleProviders: (ids: string[]) => void;
}

export function ProviderModal({
  isOpen,
  onClose,
  providers,
  selectedProviderIds,
  onToggleProvider,
  onSelectMultipleProviders,
}: ProviderModalProps) {
  const [backendStatus, setBackendStatus] = useState<{ online: boolean; data?: any }>({
    online: false,
  });
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [tempSelected, setTempSelected] = useState<string[]>(selectedProviderIds);

  useEffect(() => {
    if (isOpen) {
      setTempSelected(selectedProviderIds);
      setLoadingHealth(true);
      checkBackendHealth().then((res) => {
        setBackendStatus(res);
        setLoadingHealth(false);
      });
    }
  }, [isOpen, selectedProviderIds]);

  if (!isOpen) return null;

  const handleToggle = (id: string) => {
    if (tempSelected.includes(id)) {
      if (tempSelected.length > 1) {
        setTempSelected(tempSelected.filter((p) => p !== id));
      }
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
    onSelectMultipleProviders(tempSelected);
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" style={{ maxWidth: 840 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>
              AI Model & Provider Library (Multi-Model Matrix)
            </h2>
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 2 }}>
              Chọn đồng thời một hoặc nhiều providers để nghiên cứu và đối chiếu câu trả lời
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
            </div>
          </div>

          {/* Providers Grid with Checkboxes */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
              maxHeight: 380,
              overflowY: "auto",
              paddingRight: 4,
            }}
          >
            {providers.map((p) => {
              const isSelected = tempSelected.includes(p.id);

              return (
                <div
                  key={p.id}
                  onClick={() => handleToggle(p.id)}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "var(--radius-lg)",
                    border: `1.5px solid ${isSelected ? "var(--brand-blue)" : "var(--border-default)"}`,
                    backgroundColor: isSelected ? "var(--brand-blue-light)" : "#ffffff",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    transition: "all var(--transition-fast)",
                    boxShadow: isSelected ? "0 2px 8px rgba(37, 99, 235, 0.12)" : "var(--shadow-sm)",
                    position: "relative",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    {/* Checkbox indicator */}
                    <div
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: 4,
                        border: `2px solid ${isSelected ? "var(--brand-blue)" : "#cbd5e1"}`,
                        backgroundColor: isSelected ? "var(--brand-blue)" : "#ffffff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#ffffff",
                        fontSize: 11,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {isSelected ? "✓" : ""}
                    </div>

                    <ModelBadgeLogo type={p.iconType} size={30} />
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
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
                              padding: "2px 5px",
                              borderRadius: 4,
                              border: "1px solid #bfdbfe",
                            }}
                          >
                            <BrainIcon size={10} color="var(--brand-blue)" />
                            {p.deepModeLabel?.split(" ")[0] || "Deep"}
                          </span>
                        )}
                      </div>
                      <span style={{ fontSize: 11.5, color: "var(--text-muted)", display: "block" }}>
                        {p.modelName}
                      </span>
                    </div>
                  </div>

                  <p
                    style={{
                      fontSize: 11.5,
                      color: "var(--text-secondary)",
                      lineHeight: 1.35,
                      margin: 0,
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {p.shortDesc}
                  </p>
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
              style={{ padding: "8px 20px" }}
            >
              <span>Áp dụng ({tempSelected.length} Models)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
