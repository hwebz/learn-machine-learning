"use client";

import React from "react";
import { OptionItem, ProviderSelectionConfig } from "../../types/capabilities";
import { BrainIcon, SearchIcon, SparklesIcon } from "../icons/Icons";

interface ProviderCardOptionsProps {
  providerId: string;
  models: OptionItem[];
  currentModelId: string;
  currentModel?: OptionItem;
  thinkingLevels: OptionItem[];
  currentThinkingId: string;
  currentThinking?: OptionItem;
  modes: OptionItem[];
  currentModeId: string;
  currentMode?: OptionItem;
  isDeepThinking: boolean;
  isWebSearch: boolean;
  isDeepResearch: boolean;
  isResearchAdvanced: boolean;
  onUpdateSelection?: (providerId: string, updates: Partial<ProviderSelectionConfig>) => void;
}

export function ProviderCardOptions({
  providerId,
  models,
  currentModelId,
  currentModel,
  thinkingLevels,
  currentThinkingId,
  currentThinking,
  modes,
  currentModeId,
  currentMode,
  isDeepThinking,
  isWebSearch,
  isDeepResearch,
  isResearchAdvanced,
  onUpdateSelection,
}: ProviderCardOptionsProps) {
  // 1. DeepSeek: Exactly 2 toggles: DeepThink (R1) and Web Search
  if (providerId === "deepseek") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, flexGrow: 1 }}>
        <div
          onClick={() => onUpdateSelection?.(providerId, { deep_thinking: !isDeepThinking })}
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

        <div
          onClick={() => onUpdateSelection?.(providerId, { web_search: !isWebSearch })}
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
    );
  }

  // 2. ChatGPT: Exactly 3 toggles: Web Search, Deep Research, Thinking
  if (providerId === "chatgpt") {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gridTemplateRows: "repeat(2, 1fr)",
          gap: 8,
          flexGrow: 1,
        }}
      >
        <div
          onClick={() => onUpdateSelection?.(providerId, { web_search: !isWebSearch })}
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

        <div
          onClick={() => onUpdateSelection?.(providerId, { deep_research: !isDeepResearch })}
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

        <div
          onClick={() => onUpdateSelection?.(providerId, { deep_thinking: !isDeepThinking })}
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
    );
  }

  // 3. Copilot: Only Mode selector
  if (providerId === "copilot") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 6, flexGrow: 1 }}>
        {modes.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: "var(--brand-blue)", letterSpacing: "0.4px" }}>
                Chế độ mô hình Copilot (Mode)
              </label>
              {currentMode?.badge && (
                <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#eff6ff", color: "var(--brand-blue)", fontWeight: 700 }}>
                  {currentMode.badge}
                </span>
              )}
            </div>
            <select
              value={currentModeId}
              onChange={(e) => onUpdateSelection?.(providerId, { mode_id: e.target.value })}
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
    );
  }

  // 4. Perplexity: Column 1 = Model list (Auto selected, Pro models disabled), Column 2 = Disabled Thinking Toggle
  if (providerId === "perplexity") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, flexGrow: 1 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.4px" }}>
              Mô hình AI (Model)
            </label>
            <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "var(--brand-blue)", color: "#ffffff", fontWeight: 700 }}>
              Auto
            </span>
          </div>
          <select
            value="auto"
            onChange={() => {}}
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

        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#f1f5f9", color: "#64748b", fontWeight: 700 }}>
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
            <span style={{ fontSize: 9.5, fontWeight: 700, padding: "2px 6px", borderRadius: 10, backgroundColor: "#e2e8f0", color: "#94a3b8" }}>
              TẮT (KHÓA)
            </span>
          </div>
          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
            Chế độ Thinking yêu cầu tài khoản Perplexity Pro
          </span>
        </div>
      </div>
    );
  }

  // 5. Kimi: Row 1 = Model & Reasoning, Row 2 = Deep Research Toggle
  if (providerId === "kimi") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, flexGrow: 1 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.4px" }}>
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
                onUpdateSelection?.(providerId, { model_id: e.target.value });
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

          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
                <BrainIcon size={12} color="var(--brand-blue)" />
                <span>Thinking effort</span>
              </label>
              {currentThinking?.badge && (
                <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#eff6ff", color: "var(--brand-blue)", fontWeight: 700 }}>
                  {currentThinking.badge}
                </span>
              )}
            </div>
            <select
              disabled={thinkingLevels.length <= 1}
              value={currentThinkingId}
              onChange={(e) => onUpdateSelection?.(providerId, { thinking_level_id: e.target.value })}
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

        <div
          onClick={() => {
            const nextDr = !isDeepResearch;
            const updates: Partial<ProviderSelectionConfig> = {
              deep_research: nextDr,
              ...(nextDr && (currentModelId === "instant" || !currentModelId || currentModelId === "default") ? { model_id: "k3" } : {}),
            };
            onUpdateSelection?.(providerId, updates);
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
    );
  }

  // 6. Qwen: Row 1 = Model & Reasoning, Row 2 = Web Search, Deep Research & Research Mode
  if (providerId === "qwen") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, flexGrow: 1 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.4px" }}>
                Mô hình Qwen
              </label>
              <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "var(--brand-blue)", color: "#ffffff", fontWeight: 700 }}>
                {currentModel?.badge || "Active"}
              </span>
            </div>
            <select
              disabled={models.length <= 1}
              value={currentModelId}
              onChange={(e) => {
                const targetM = models.find((m) => m.id === e.target.value);
                if (targetM?.disabled) return;
                onUpdateSelection?.(providerId, { model_id: e.target.value });
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
                onUpdateSelection?.(providerId, { thinking_level_id: e.target.value });
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

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gridAutoRows: "repeat(2, 1fr)",
            gap: 8,
          }}
        >
          <div
            onClick={() => onUpdateSelection?.(providerId, { web_search: !isWebSearch })}
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

          <div
            onClick={() => {
              const nextDr = !isDeepResearch;
              const updates: Partial<ProviderSelectionConfig> = {
                deep_research: nextDr,
                ...(nextDr ? { thinking_level_id: "auto" } : {}),
              };
              onUpdateSelection?.(providerId, updates);
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

          {isDeepResearch && (
            <div
              onClick={() => {
                const nextMode = isResearchAdvanced ? "normal" : "advanced";
                onUpdateSelection?.(providerId, { research_mode: nextMode });
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
              title={isResearchAdvanced ? "Advanced - Devoting extra time to a deeper analysis" : "Normal - Fast, reliable responses for quick tasks"}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden" }}>
                <SparklesIcon size={14} color={isResearchAdvanced ? "#9333ea" : "#64748b"} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 11.5, fontWeight: 700, color: isResearchAdvanced ? "#9333ea" : "var(--text-primary, #0f172a)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {isResearchAdvanced ? "Advanced" : "Normal"}
                  </div>
                  <div style={{ fontSize: 9, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
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
    );
  }

  // 7. Gemini: Row 1 = Model & Reasoning, Row 2 = Deep Research toggle
  if (providerId === "gemini") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, flexGrow: 1 }}>
        <div style={{ display: "grid", gridTemplateColumns: thinkingLevels.length > 0 ? "1fr 1fr" : "1fr", gap: 10 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.4px" }}>
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
                onUpdateSelection?.(providerId, { model_id: e.target.value });
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

          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
                <BrainIcon size={12} color="var(--brand-blue)" />
                <span>Mức suy luận (Reasoning)</span>
              </label>
              {currentThinking?.badge && (
                <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#eff6ff", color: "var(--brand-blue)", fontWeight: 700 }}>
                  {currentThinking.badge}
                </span>
              )}
            </div>
            <select
              disabled={thinkingLevels.length <= 1}
              value={currentThinkingId}
              onChange={(e) => onUpdateSelection?.(providerId, { thinking_level_id: e.target.value })}
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

        <div
          onClick={() => onUpdateSelection?.(providerId, { deep_research: !isDeepResearch })}
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
    );
  }

  // 8. xAI Grok: Free account — no options to configure
  if (providerId === "grok") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          justifyContent: "space-between",
          padding: "10px 14px",
          borderRadius: 8,
          backgroundColor: "#f8fafc",
          border: "1px dashed var(--border-default, #cbd5e1)",
          flexGrow: 1,
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 6px", borderRadius: 4, backgroundColor: "#e2e8f0", color: "#475569" }}>
            FREE ACCOUNT
          </span>
          <span style={{ fontSize: 12, color: "var(--text-muted, #64748b)" }}>
            Tài khoản miễn phí — không có cấu hình tùy chỉnh, sử dụng toàn bộ mặc định từ xAI Grok.
          </span>
        </div>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted, #94a3b8)", fontStyle: "italic" }}>
          Mặc định (Default)
        </span>
      </div>
    );
  }

  // 9. Mistral Le Chat: Reasoning dropdown (Fast / Think) + Deep Research toggle (@deep-research)
  if (providerId === "mistral") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, flexGrow: 1 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
              <BrainIcon size={12} color="#ea580c" />
              <span>Chế độ suy luận (Reasoning Mode)</span>
            </label>
            {currentThinking?.badge && (
              <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#fff7ed", color: "#ea580c", fontWeight: 700 }}>
                {currentThinking.badge}
              </span>
            )}
          </div>
          <select
            value={currentThinkingId || "fast"}
            onChange={(e) => onUpdateSelection?.(providerId, { thinking_level_id: e.target.value })}
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

        <div
          onClick={() => onUpdateSelection?.(providerId, { deep_research: !isDeepResearch })}
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
    );
  }

  // 10. MiniMax Hailuo: AI Model dropdown + Deep Research toggle
  if (providerId === "minimax") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, flexGrow: 1 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.4px" }}>
              Mô hình AI (Model)
            </label>
            <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#fdf2f8", color: "#e2167e", fontWeight: 700 }}>
              {currentModel?.badge || "M3"}
            </span>
          </div>
          <select
            value={currentModelId || "m3"}
            onChange={(e) => onUpdateSelection?.(providerId, { model_id: e.target.value })}
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
            title="Chọn mô hình AI MiniMax (M3, M3.1 Flash Preview, M2.7, M2.7 HighSpeed)"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
            {currentModel?.description || "Mô hình cờ đầu toàn diện của MiniMax, xử lý tác vụ phức tạp"}
          </span>
        </div>

        <div
          onClick={() => onUpdateSelection?.(providerId, { deep_research: !isDeepResearch })}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "8px 12px",
            borderRadius: 6,
            border: `1.5px solid ${isDeepResearch ? "#e2167e" : "var(--border-default, #cbd5e1)"}`,
            backgroundColor: isDeepResearch ? "#fdf2f8" : "#ffffff",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
          title="Bật/Tắt chế độ Deep Research trên MiniMax (+ button -> Skills -> deep-research)"
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SparklesIcon size={16} color={isDeepResearch ? "#e2167e" : "#64748b"} />
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: isDeepResearch ? "#e2167e" : "var(--text-primary, #0f172a)" }}>
                Deep Research
              </div>
              <div style={{ fontSize: 10.5, color: "var(--text-muted, #64748b)" }}>
                Kích hoạt skill deep-research (+ button &rarr; Skills &rarr; deep-research)
              </div>
            </div>
          </div>
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: 10,
              backgroundColor: isDeepResearch ? "#e2167e" : "#e2e8f0",
              color: isDeepResearch ? "#ffffff" : "#64748b",
              flexShrink: 0,
            }}
          >
            {isDeepResearch ? "BẬT" : "TẮT"}
          </span>
        </div>
      </div>
    );
  }

  // 11. Meta AI: Thinking toggle (Thinking vs Instant)
  if (providerId === "meta") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, flexGrow: 1 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
              <BrainIcon size={12} color="var(--brand-blue)" />
              <span>Chế độ tư duy (Thinking Mode)</span>
            </label>
            <span
              style={{
                fontSize: 9.5,
                padding: "1px 5px",
                borderRadius: 3,
                backgroundColor: isDeepThinking ? "#eff6ff" : "#f1f5f9",
                color: isDeepThinking ? "var(--brand-blue)" : "#64748b",
                fontWeight: 700,
              }}
            >
              {isDeepThinking ? "Thinking (BẬT)" : "Instant (TẮT)"}
            </span>
          </div>
          <select
            value={isDeepThinking ? "thinking" : "instant"}
            onChange={(e) => onUpdateSelection?.(providerId, { deep_thinking: e.target.value === "thinking" })}
            style={{
              width: "100%",
              padding: "6px 8px",
              borderRadius: 6,
              border: `1.5px solid ${isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
              backgroundColor: isDeepThinking ? "#eff6ff" : "#ffffff",
              fontSize: 12,
              fontWeight: 600,
              color: isDeepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-primary, #0f172a)",
              cursor: "pointer",
              outline: "none",
            }}
            title="Chọn chế độ: Thinking (suy luận sâu) hoặc Instant (phản hồi tức thì)"
          >
            <option value="thinking">Thinking (Suy luận chuyên sâu — BẬT)</option>
            <option value="instant">Instant (Phản hồi tức thì — TẮT)</option>
          </select>
          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
            Meta AI không có dropdown chọn model. Chọn &quot;Thinking&quot; để bật suy luận đa bước hoặc &quot;Instant&quot; để phản hồi tức thì.
          </span>
        </div>
      </div>
    );
  }

  // 12. Generic / Claude / Zhipu / Others: Model selector, Reasoning picker, Mode picker
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: thinkingLevels.length > 0 ? "1fr 1fr" : "1fr",
        gap: 10,
        flexGrow: 1,
      }}
    >
      {/* 1. Model Selector */}
      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.4px" }}>
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
            onUpdateSelection?.(providerId, { model_id: e.target.value });
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
      {thinkingLevels.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
              <BrainIcon size={12} color="var(--brand-blue)" />
              <span>Mức suy luận (Reasoning)</span>
            </label>
            {currentThinking?.badge && (
              <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#eff6ff", color: "var(--brand-blue)", fontWeight: 700 }}>
                {currentThinking.badge}
              </span>
            )}
          </div>
          <select
            disabled={thinkingLevels.length <= 1}
            value={currentThinkingId}
            onChange={(e) => onUpdateSelection?.(providerId, { thinking_level_id: e.target.value })}
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
      )}

      {/* 3. Mode Picker (if applicable) */}
      {modes.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 3, gridColumn: thinkingLevels.length > 0 ? "1 / -1" : undefined }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.4px" }}>
              Chế độ (Mode)
            </label>
            {currentMode?.badge && (
              <span style={{ fontSize: 9.5, padding: "1px 5px", borderRadius: 3, backgroundColor: "#eff6ff", color: "var(--brand-blue)", fontWeight: 700 }}>
                {currentMode.badge}
              </span>
            )}
          </div>
          <select
            value={currentModeId}
            onChange={(e) => onUpdateSelection?.(providerId, { mode_id: e.target.value })}
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
          <span style={{ fontSize: 10.5, color: "var(--text-muted)", lineHeight: 1.25 }}>
            {currentMode?.description || ""}
          </span>
        </div>
      )}
    </div>
  );
}
