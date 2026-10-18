import React, { useMemo } from "react";
import { ProviderInfo } from "../../types/chat";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";
import { BrainIcon, RefreshIcon, SearchIcon, SparklesIcon } from "../icons/Icons";
import {
  formatSyncTime,
  getProviderModels,
  getProviderThinkingLevels,
  getProviderModes,
} from "../../lib/providerOptionsHelper";

interface ProviderFinetuneSectionProps {
  role: "orchestrator" | "lead";
  provider: ProviderInfo;
  caps?: ProviderLiveCapabilities;
  model: string;
  setModel: (val: string) => void;
  thinkingLevel: string;
  setThinkingLevel: (val: string) => void;
  thinking: boolean;
  setThinking: (val: boolean) => void;
  deepThinking: boolean;
  setDeepThinking: (val: boolean) => void;
  webSearch: boolean;
  setWebSearch: (val: boolean) => void;
  deepResearch: boolean;
  setDeepResearch: (val: boolean) => void;
  researchMode: string;
  setResearchMode: (val: string) => void;
  mode: string;
  setMode: (val: string) => void;
  onUpdateSelection?: (providerId: string, updates: Partial<ProviderSelectionConfig>) => void;
  onSync?: () => Promise<void>;
  isSyncing?: boolean;
  syncMessage?: string | null;
  loadingProvider?: string | null;
}

function ProviderFinetuneSectionComponent({
  role,
  provider,
  caps,
  model,
  setModel,
  thinkingLevel,
  setThinkingLevel,
  thinking,
  setThinking,
  deepThinking,
  setDeepThinking,
  webSearch,
  setWebSearch,
  deepResearch,
  setDeepResearch,
  researchMode,
  setResearchMode,
  mode,
  setMode,
  onUpdateSelection,
  onSync,
  isSyncing = false,
  syncMessage,
  loadingProvider,
}: ProviderFinetuneSectionProps) {
  const pid = provider.id.toLowerCase();
  const titleColor = role === "orchestrator" ? "var(--brand-blue, #2563eb)" : "#10a37f";
  const roleLabel = role === "orchestrator" ? "Cấu hình Orchestrator" : "Cấu hình Lead Provider";

  const availableModels = useMemo(() => {
    return getProviderModels(pid, caps, deepResearch, provider.modelName);
  }, [pid, caps, deepResearch, provider.modelName]);

  const thinkingLevels = useMemo(() => {
    return getProviderThinkingLevels(pid, caps);
  }, [pid, caps]);

  const availableModes = useMemo(() => {
    return getProviderModes(pid, caps);
  }, [pid, caps]);

  const isProviderLoading = isSyncing || loadingProvider === pid;

  return (
    <div className="agent-provider-finetune">
      <div className="agent-finetune-header">
        <div className="agent-finetune-title">
          <BrainIcon size={14} color={titleColor} />
          <span>{roleLabel} (<strong>{provider.name}</strong>):</span>
          {caps?.is_live_dom ? (
            <span className="agent-dom-badge live" title="Đã đồng bộ trực tiếp từ DOM của trình duyệt">
              LIVE DOM
            </span>
          ) : (
            <span className="agent-dom-badge cached" title="Cấu hình bộ đệm / mặc định. Bấm 'Đồng bộ DOM' để quét trực tiếp từ trình duyệt">
              CACHED
            </span>
          )}
          {caps?.synced_at && (
            <span className="agent-synced-time">
              (Cập nhật: {formatSyncTime(caps.synced_at)})
            </span>
          )}
        </div>

        {onSync && (
          <button
            type="button"
            className="agent-resync-btn"
            onClick={onSync}
            disabled={isProviderLoading}
            title={`Quét lại DOM của ${provider.name} để lấy cấu hình mới nhất`}
          >
            <RefreshIcon size={12} className={isProviderLoading ? "spin" : ""} />
            <span>{isProviderLoading ? "Đang quét DOM..." : "Đồng bộ DOM"}</span>
          </button>
        )}
      </div>

      {syncMessage && (
        <div className={`agent-sync-feedback ${syncMessage.startsWith("Lỗi") ? "error" : "success"}`}>
          {syncMessage}
        </div>
      )}

      <div className="agent-finetune-options">
        {pid === "deepseek" ? (
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%" }}>
            {/* DeepThink (R1) Toggle */}
            <button
              type="button"
              onClick={() => {
                const nextVal = !deepThinking;
                setDeepThinking(nextVal);
                onUpdateSelection?.(pid, { deep_thinking: nextVal });
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1.5px solid ${deepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                backgroundColor: deepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: deepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt mô hình suy luận sâu DeepSeek-R1 (Chain of Thought)"
            >
              <BrainIcon size={14} color={deepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
              <span>DeepThink (R1)</span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 10,
                  backgroundColor: deepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                  color: deepThinking ? "#ffffff" : "#64748b",
                }}
              >
                {deepThinking ? "BẬT" : "TẮT"}
              </span>
            </button>

            {/* Web Search Toggle */}
            <button
              type="button"
              onClick={() => {
                const nextVal = !webSearch;
                setWebSearch(nextVal);
                onUpdateSelection?.(pid, { web_search: nextVal });
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1.5px solid ${webSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                backgroundColor: webSearch ? "#ecfdf5" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: webSearch ? "#059669" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt tính năng tìm kiếm Web thời gian thực của DeepSeek"
            >
              <SearchIcon size={14} color={webSearch ? "#059669" : "#64748b"} />
              <span>Tìm kiếm Web</span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 10,
                  backgroundColor: webSearch ? "#059669" : "#e2e8f0",
                  color: webSearch ? "#ffffff" : "#64748b",
                }}
              >
                {webSearch ? "BẬT" : "TẮT"}
              </span>
            </button>
          </div>
        ) : pid === "chatgpt" ? (
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%" }}>
            {/* Web Search Toggle */}
            <button
              type="button"
              onClick={() => {
                const nextVal = !webSearch;
                setWebSearch(nextVal);
                onUpdateSelection?.(pid, { web_search: nextVal });
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1.5px solid ${webSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                backgroundColor: webSearch ? "#ecfdf5" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: webSearch ? "#059669" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt tìm kiếm Web thời gian thực của ChatGPT"
            >
              <SearchIcon size={14} color={webSearch ? "#059669" : "#64748b"} />
              <span>Web Search</span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 10,
                  backgroundColor: webSearch ? "#059669" : "#e2e8f0",
                  color: webSearch ? "#ffffff" : "#64748b",
                }}
              >
                {webSearch ? "BẬT" : "TẮT"}
              </span>
            </button>

            {/* Deep Research Toggle */}
            <button
              type="button"
              onClick={() => {
                const nextVal = !deepResearch;
                setDeepResearch(nextVal);
                onUpdateSelection?.(pid, { deep_research: nextVal });
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1.5px solid ${deepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                backgroundColor: deepResearch ? "#f5f3ff" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: deepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt chế độ Deep Research của ChatGPT"
            >
              <SparklesIcon size={14} color={deepResearch ? "#7c3aed" : "#64748b"} />
              <span>Deep Research</span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 10,
                  backgroundColor: deepResearch ? "#7c3aed" : "#e2e8f0",
                  color: deepResearch ? "#ffffff" : "#64748b",
                }}
              >
                {deepResearch ? "BẬT" : "TẮT"}
              </span>
            </button>

            {/* Thinking Toggle */}
            <button
              type="button"
              onClick={() => {
                const nextVal = !deepThinking;
                setDeepThinking(nextVal);
                onUpdateSelection?.(pid, { deep_thinking: nextVal });
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1.5px solid ${deepThinking ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                backgroundColor: deepThinking ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: deepThinking ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt chế độ Thinking của ChatGPT"
            >
              <BrainIcon size={14} color={deepThinking ? "var(--brand-blue, #2563eb)" : "#64748b"} />
              <span>Thinking</span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 10,
                  backgroundColor: deepThinking ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                  color: deepThinking ? "#ffffff" : "#64748b",
                }}
              >
                {deepThinking ? "BẬT" : "TẮT"}
              </span>
            </button>
          </div>
        ) : pid === "meta" ? (
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", width: "100%" }}>
            <button
              type="button"
              onClick={() => {
                const nextThinking = thinkingLevel === "thinking" ? "instant" : "thinking";
                setThinkingLevel(nextThinking);
                setThinking(nextThinking === "thinking");
                setDeepThinking(nextThinking === "thinking");
                onUpdateSelection?.(pid, {
                  thinking_level_id: nextThinking,
                  deep_thinking: nextThinking === "thinking",
                });
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 14px",
                borderRadius: "var(--radius-sm, 6px)",
                border: `1.5px solid ${thinkingLevel === "thinking" ? "var(--brand-blue, #2563eb)" : "var(--border-default, #cbd5e1)"}`,
                backgroundColor: thinkingLevel === "thinking" ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                fontSize: 12,
                fontWeight: 600,
                color: thinkingLevel === "thinking" ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              title="Bật/Tắt chế độ Thinking của Meta AI (Thinking vs Instant)"
            >
              <BrainIcon size={14} color={thinkingLevel === "thinking" ? "var(--brand-blue, #2563eb)" : "#64748b"} />
              <span>Thinking Mode: <strong>{thinkingLevel === "thinking" ? "Thinking" : "Instant"}</strong></span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 10,
                  backgroundColor: thinkingLevel === "thinking" ? "var(--brand-blue, #2563eb)" : "#e2e8f0",
                  color: thinkingLevel === "thinking" ? "#ffffff" : "#64748b",
                }}
              >
                {thinkingLevel === "thinking" ? "THINKING" : "INSTANT"}
              </span>
            </button>
            <span style={{ fontSize: 12, color: "var(--text-muted, #64748b)", fontStyle: "italic" }}>
              (Meta AI DOM: Toggle trực tiếp giữa Thinking và Instant, không có dropdown chọn model)
            </span>
          </div>
        ) : (
          <>
            {/* 1. Model Selector */}
            {availableModels.length > 0 && (
              <label className="agent-option-inline">
                <span>Mô hình:</span>
                <select
                  value={model}
                  onChange={(e) => {
                    const targetM = availableModels.find((m) => m.id === e.target.value);
                    if (targetM?.disabled) return;
                    const val = e.target.value;
                    setModel(val);
                    onUpdateSelection?.(pid, { model_id: val });
                  }}
                  className="agent-select"
                >
                  {availableModels.map((m) => (
                    <option key={m.id} value={m.id} disabled={m.disabled}>
                      {m.label} {m.disabled ? "— [Upgrade]" : m.badge ? `[${m.badge}]` : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {/* 2. Reasoning Effort or Thinking Toggle */}
            {thinkingLevels.length > 0 ? (
              <label className="agent-option-inline">
                <span>Reasoning Effort:</span>
                <select
                  disabled={pid === "qwen" && deepResearch}
                  value={pid === "qwen" && deepResearch ? "auto" : thinkingLevel}
                  onChange={(e) => {
                    if (pid === "qwen" && deepResearch) return;
                    const val = e.target.value;
                    setThinkingLevel(val);
                    onUpdateSelection?.(pid, { thinking_level_id: val });
                  }}
                  className="agent-select"
                  style={pid === "qwen" && deepResearch ? { opacity: 0.7, cursor: "not-allowed" } : undefined}
                >
                  {pid === "qwen" && deepResearch ? (
                    <option value="auto">Auto</option>
                  ) : (
                    thinkingLevels.map((lvl) => (
                      <option key={lvl.id} value={lvl.id}>
                        {lvl.label} {lvl.badge ? `[${lvl.badge}]` : ""}
                      </option>
                    ))
                  )}
                </select>
              </label>
            ) : pid === "copilot" || pid === "chatgpt" || pid === "grok" ? (
              pid === "grok" ? (
                <span style={{ fontSize: 12, color: "var(--text-muted, #64748b)", fontStyle: "italic" }}>
                  Tài khoản miễn phí — sử dụng cấu hình mặc định từ xAI Grok.
                </span>
              ) : null
            ) : pid === "perplexity" ? (
              <button
                type="button"
                disabled
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: "1.5px solid var(--border-default, #cbd5e1)",
                  backgroundColor: "#f8fafc",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--text-muted, #94a3b8)",
                  cursor: "not-allowed",
                  opacity: 0.7,
                }}
                title="Tính năng Thinking bị khóa trên tài khoản Perplexity miễn phí"
              >
                <BrainIcon size={14} color="#94a3b8" />
                <span>Thinking</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: "#e2e8f0",
                    color: "#94a3b8",
                  }}
                >
                  TẮT (KHÓA)
                </span>
              </button>
            ) : (
              <label className="agent-checkbox-inline">
                <input
                  type="checkbox"
                  checked={thinking}
                  onChange={(e) => setThinking(e.target.checked)}
                />
                <span>Kích hoạt Thinking / Deep Reasoning Mode</span>
              </label>
            )}

            {/* Kimi Deep Research Toggle */}
            {pid === "kimi" && (
              <button
                type="button"
                onClick={() => {
                  const nextVal = !deepResearch;
                  setDeepResearch(nextVal);
                  if (nextVal && (model === "instant" || !model || model === "default")) {
                    setModel("k3");
                    onUpdateSelection?.(pid, { deep_research: nextVal, model_id: "k3" });
                  } else {
                    onUpdateSelection?.(pid, { deep_research: nextVal });
                  }
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1.5px solid ${deepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                  backgroundColor: deepResearch ? "#f5f3ff" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: deepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title="Bật/Tắt chế độ Deep Research của Moonshot Kimi"
              >
                <SparklesIcon size={14} color={deepResearch ? "#7c3aed" : "#64748b"} />
                <span>Deep Research</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: deepResearch ? "#7c3aed" : "#e2e8f0",
                    color: deepResearch ? "#ffffff" : "#64748b",
                  }}
                >
                  {deepResearch ? "BẬT" : "TẮT"}
                </span>
              </button>
            )}

            {/* Qwen Web Search Toggle */}
            {pid === "qwen" && (
              <button
                type="button"
                onClick={() => {
                  const nextVal = !webSearch;
                  setWebSearch(nextVal);
                  onUpdateSelection?.(pid, { web_search: nextVal });
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1.5px solid ${webSearch ? "#059669" : "var(--border-default, #cbd5e1)"}`,
                  backgroundColor: webSearch ? "#ecfdf5" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: webSearch ? "#059669" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title="Bật/Tắt tính năng tìm kiếm Web trên Qwen (+ Web search)"
              >
                <SearchIcon size={14} color={webSearch ? "#059669" : "#64748b"} />
                <span>Web Search</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: webSearch ? "#059669" : "#e2e8f0",
                    color: webSearch ? "#ffffff" : "#64748b",
                  }}
                >
                  {webSearch ? "BẬT" : "TẮT"}
                </span>
              </button>
            )}

            {/* Qwen Deep Research Toggle */}
            {pid === "qwen" && (
              <button
                type="button"
                onClick={() => {
                  const nextVal = !deepResearch;
                  setDeepResearch(nextVal);
                  const updates: Partial<ProviderSelectionConfig> = { deep_research: nextVal };
                  if (nextVal) {
                    setThinkingLevel("auto");
                    updates.thinking_level_id = "auto";
                  }
                  onUpdateSelection?.(pid, updates);
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1.5px solid ${deepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                  backgroundColor: deepResearch ? "#f5f3ff" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: deepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title="Bật/Tắt chế độ Deep Research của Qwen (+ Deep Research)"
              >
                <SparklesIcon size={14} color={deepResearch ? "#7c3aed" : "#64748b"} />
                <span>Deep Research</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: deepResearch ? "#7c3aed" : "#e2e8f0",
                    color: deepResearch ? "#ffffff" : "#64748b",
                  }}
                >
                  {deepResearch ? "BẬT" : "TẮT"}
                </span>
              </button>
            )}

            {/* Qwen Research Mode Toggle (when Deep Research is ON) */}
            {pid === "qwen" && deepResearch && (
              <button
                type="button"
                onClick={() => {
                  const nextMode = researchMode === "advanced" ? "normal" : "advanced";
                  setResearchMode(nextMode);
                  onUpdateSelection?.(pid, { research_mode: nextMode });
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1.5px solid ${researchMode === "advanced" ? "#9333ea" : "var(--border-default, #cbd5e1)"}`,
                  backgroundColor: researchMode === "advanced" ? "#f3e8ff" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: researchMode === "advanced" ? "#9333ea" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title={researchMode === "advanced"
                  ? "Advanced - Devoting extra time to a deeper analysis"
                  : "Normal - Fast, reliable responses for quick tasks"}
              >
                <SparklesIcon size={14} color={researchMode === "advanced" ? "#9333ea" : "#64748b"} />
                <span>{researchMode === "advanced" ? "Advanced" : "Normal"}</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: researchMode === "advanced" ? "#9333ea" : "#e2e8f0",
                    color: researchMode === "advanced" ? "#ffffff" : "#64748b",
                  }}
                >
                  {researchMode === "advanced" ? "BẬT" : "TẮT"}
                </span>
              </button>
            )}

            {/* Gemini Deep Research Toggle */}
            {pid === "gemini" && (
              <button
                type="button"
                onClick={() => {
                  const nextVal = !deepResearch;
                  setDeepResearch(nextVal);
                  onUpdateSelection?.(pid, { deep_research: nextVal });
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1.5px solid ${deepResearch ? "#7c3aed" : "var(--border-default, #cbd5e1)"}`,
                  backgroundColor: deepResearch ? "#f5f3ff" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: deepResearch ? "#7c3aed" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title="Bật/Tắt tính năng Deep Research của Gemini (+ menu)"
              >
                <SparklesIcon size={14} color={deepResearch ? "#7c3aed" : "#64748b"} />
                <span>Deep Research</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: deepResearch ? "#7c3aed" : "#e2e8f0",
                    color: deepResearch ? "#ffffff" : "#64748b",
                  }}
                >
                  {deepResearch ? "BẬT" : "TẮT"}
                </span>
              </button>
            )}

            {/* Mistral Deep Research Toggle */}
            {pid === "mistral" && (
              <button
                type="button"
                onClick={() => {
                  const nextVal = !deepResearch;
                  setDeepResearch(nextVal);
                  onUpdateSelection?.(pid, { deep_research: nextVal });
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1.5px solid ${deepResearch ? "#ea580c" : "var(--border-default, #cbd5e1)"}`,
                  backgroundColor: deepResearch ? "#fff7ed" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: deepResearch ? "#ea580c" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title="Bật/Tắt chế độ Deep Research trên Mistral (tự động gõ @deep-research)"
              >
                <SparklesIcon size={14} color={deepResearch ? "#ea580c" : "#64748b"} />
                <span>Deep Research</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: deepResearch ? "#ea580c" : "#e2e8f0",
                    color: deepResearch ? "#ffffff" : "#64748b",
                  }}
                >
                  {deepResearch ? "BẬT" : "TẮT"}
                </span>
              </button>
            )}

            {/* MiniMax Deep Research Toggle */}
            {pid === "minimax" && (
              <button
                type="button"
                onClick={() => {
                  const nextVal = !deepResearch;
                  setDeepResearch(nextVal);
                  onUpdateSelection?.(pid, { deep_research: nextVal });
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  borderRadius: "var(--radius-sm, 6px)",
                  border: `1.5px solid ${deepResearch ? "#e2167e" : "var(--border-default, #cbd5e1)"}`,
                  backgroundColor: deepResearch ? "#fdf2f8" : "#ffffff",
                  fontSize: 12,
                  fontWeight: 600,
                  color: deepResearch ? "#e2167e" : "var(--text-secondary, #475569)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                title="Bật/Tắt chế độ Deep Research trên MiniMax (+ button -> Skills -> deep-research)"
              >
                <SparklesIcon size={14} color={deepResearch ? "#e2167e" : "#64748b"} />
                <span>Deep Research</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "1px 6px",
                    borderRadius: 10,
                    backgroundColor: deepResearch ? "#e2167e" : "#e2e8f0",
                    color: deepResearch ? "#ffffff" : "#64748b",
                  }}
                >
                  {deepResearch ? "BẬT" : "TẮT"}
                </span>
              </button>
            )}

            {/* 3. Mode Selector */}
            {availableModes.length > 0 && (
              <label className="agent-option-inline">
                <span>Chế độ (Mode):</span>
                <select
                  value={mode}
                  onChange={(e) => {
                    setMode(e.target.value);
                    onUpdateSelection?.(pid, { mode_id: e.target.value });
                  }}
                  className="agent-select"
                >
                  {availableModes.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label} {m.badge ? `[${m.badge}]` : ""}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export const ProviderFinetuneSection = React.memo(ProviderFinetuneSectionComponent);
