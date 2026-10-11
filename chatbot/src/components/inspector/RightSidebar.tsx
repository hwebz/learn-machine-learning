"use client";

import React, { useState, useEffect, useRef } from "react";
import { Message, ProviderInfo, StepLog, ThinkingStep, SourceLink, DepthMode } from "../../types/chat";
import {
  ModelBadgeLogo,
  CheckCircleIcon,
  ExternalLinkIcon,
  ChevronRightIcon,
  BrainIcon,
  CopyIcon,
} from "../icons/Icons";
import { extractProviderResponse } from "../../lib/providerResponse";

function normalizeProvider(name: string): string {
  const s = name.trim().toLowerCase();
  if (s.includes("qwen")) return "qwen";
  if (s.includes("copilot")) return "copilot";
  if (s.includes("gemini")) return "gemini";
  if (s.includes("deepseek")) return "deepseek";
  if (s.includes("chatgpt") || s.includes("openai")) return "chatgpt";
  if (s.includes("grok")) return "grok";
  if (s.includes("claude")) return "claude";
  if (s.includes("perplexity")) return "perplexity";
  if (s.includes("mistral")) return "mistral";
  return s;
}

function extractProvider(st: StepLog): string {
  if (st.provider) return normalizeProvider(st.provider);
  if (st.data?.provider) return normalizeProvider(String(st.data.provider));
  const match = st.message.match(
    /\b(qwen|copilot|gemini|deepseek|chatgpt|openai|grok|perplexity|claude|mistral)\b/i
  );
  if (match) return normalizeProvider(match[1]);
  return "";
}

interface ProviderThinkingDetail {
  provider: string;
  displayName: string;
  thinkingSteps: (ThinkingStep & { timestamp?: string })[];
  thinkingText: string;
  citations: SourceLink[];
  logs: StepLog[];
  isRunning: boolean;
  timestamp: string;
}

interface RightSidebarProps {
  selectedProvider: ProviderInfo;
  selectedProviders?: ProviderInfo[];
  currentMessage?: Message;
  currentQuery?: string;
  isGenerating?: boolean;
  activeSteps?: StepLog[];
  inspectedProvider?: string;
  depth?: DepthMode;
  onSelectProvider?: (providerId: string) => void;
  onClose?: () => void;
}

export function RightSidebar({
  selectedProvider,
  selectedProviders = [],
  currentMessage,
  currentQuery = "",
  isGenerating = false,
  activeSteps = [],
  inspectedProvider,
  depth,
  onSelectProvider,
  onClose,
}: RightSidebarProps) {
  const [copiedStepIdx, setCopiedStepIdx] = useState<number | null>(null);

  const copyStepText = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedStepIdx(idx);
    setTimeout(() => setCopiedStepIdx(null), 2000);
  };

  const [sidebarWidth, setSidebarWidth] = useState<number>(500);
  const [isResizing, setIsResizing] = useState(false);
  const dragStartRef = useRef<{ startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("right_sidebar_width");
      if (saved) {
        const val = parseInt(saved, 10);
        if (!isNaN(val) && val >= 320 && val <= 1000) {
          setSidebarWidth(val);
        }
      }
    }
  }, []);

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    dragStartRef.current = {
      startX: e.clientX,
      startWidth: sidebarWidth,
    };
  };

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return;
      const delta = dragStartRef.current.startX - e.clientX;
      const minW = 340;
      const maxW = Math.min(Math.floor(window.innerWidth * 0.75), 900);
      const nextWidth = Math.max(minW, Math.min(maxW, dragStartRef.current.startWidth + delta));
      setSidebarWidth(nextWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      dragStartRef.current = null;
    };

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  useEffect(() => {
    if (!isResizing && sidebarWidth) {
      try {
        localStorage.setItem("right_sidebar_width", String(sidebarWidth));
      } catch { }
    }
  }, [isResizing, sidebarWidth]);
  // Determine which step log collection to inspect:
  // If active generation is ongoing, use activeSteps. Otherwise use currentMessage steps.
  const stepsToInspect = (isGenerating && activeSteps.length > 0)
    ? activeSteps
    : (currentMessage?.steps || activeSteps || []);

  // Pre-aggregate thinking details for all providers present
  const providersMap = new Map<string, ProviderThinkingDetail>();

  for (const st of stepsToInspect) {
    const p = extractProvider(st);
    if (!p) continue;
    if (!providersMap.has(p)) {
      providersMap.set(p, {
        provider: p,
        displayName: p.toUpperCase(),
        thinkingSteps: [],
        thinkingText: "",
        citations: [],
        logs: [],
        isRunning: false,
        timestamp: st.timestamp || "",
      });
    }
  }

  if (providersMap.size === 0 && stepsToInspect.length > 0) {
    providersMap.set("ai", {
      provider: "ai",
      displayName: "AI ENGINE",
      thinkingSteps: [],
      thinkingText: "",
      citations: [],
      logs: [],
      isRunning: isGenerating,
      timestamp: "",
    });
  }

  for (const [p, detail] of providersMap.entries()) {
    const pSteps = stepsToInspect.filter((st) => {
      const sp = extractProvider(st);
      return sp === p || (providersMap.size === 1 && !sp);
    });

    const stepMap = new Map<string, ThinkingStep & { timestamp?: string }>();
    for (const st of pSteps) {
      const raw = st.thinkingSteps || st.data?.thinking_steps || [];
      for (const item of raw) {
        if (!item || !item.title) continue;
        const key = item.title.trim().toLowerCase();
        const existing = stepMap.get(key);
        if (!existing) {
          stepMap.set(key, { ...item, timestamp: st.timestamp });
        } else {
          existing.status = item.status || existing.status;
          if (item.description && item.description.trim()) {
            existing.description = item.description;
          }
          if (st.timestamp) {
            existing.timestamp = st.timestamp;
          }
        }
      }
    }
    detail.thinkingSteps = Array.from(stepMap.values());

    const citMap = new Map<string, SourceLink>();
    for (const st of pSteps) {
      const rawCits = st.citations || st.data?.citations || [];
      for (const c of rawCits) {
        if (c && c.url && !citMap.has(c.url)) {
          citMap.set(c.url, {
            title: c.title || c.url,
            url: c.url,
            domain: c.domain,
            snippet: c.snippet,
          });
        }
      }
    }
    detail.citations = Array.from(citMap.values());

    for (const st of [...pSteps].reverse()) {
      const t = st.thinkingText || st.data?.thinking_text;
      if (t && typeof t === "string" && t.trim().length > 0) {
        detail.thinkingText = t;
        break;
      }
    }

    detail.logs = pSteps;

    const isDone = pSteps.some(
      (st) =>
        st.step === "response_valid" ||
        st.step === "response_partial" ||
        st.step === "completed" ||
        st.step === "failed" ||
        st.status === "completed" ||
        (st.data && (st.data.status === "ok" || st.data.status === "partial" || Boolean(st.data.response_markdown))) ||
        /hoàn thành|phản hồi hợp lệ|kết quả một phần|thất bại|đã trả về|response_valid/i.test(st.message)
    );
    const isResponseGenerated = !isGenerating || isDone || Boolean(currentMessage?.role === "assistant" && !isGenerating);
    detail.isRunning = Boolean(isGenerating && !isResponseGenerated);

    if (!detail.isRunning) {
      // The response has been generated: No in-progress (loading) step on the right hand side anymore!
      for (const stepItem of detail.thinkingSteps) {
        stepItem.status = "completed";
      }
    } else {
      // In Live DOM: only the latest active step should be shown as running; earlier steps are completed
      const lastRunningIdx = detail.thinkingSteps.map((s) => s.status).lastIndexOf("running");
      if (lastRunningIdx >= 0) {
        for (let idx = 0; idx < lastRunningIdx; idx++) {
          detail.thinkingSteps[idx].status = "completed";
        }
      }
    }

    const lastStepWithTime = [...pSteps].reverse().find((s) => s.timestamp);
    if (lastStepWithTime?.timestamp) {
      detail.timestamp = lastStepWithTime.timestamp;
    }

    // Always concatenate the last step for all providers in thinking steps to show the real response generated by the specific provider
    const providerResponse = extractProviderResponse(p, pSteps, currentMessage);
    if (providerResponse) {
      const filteredSteps = detail.thinkingSteps.filter(
        (s) => !s.title.toLowerCase().includes("response generated")
      );
      filteredSteps.push({
        title: "Response generated",
        description: providerResponse,
        status: "completed",
        timestamp: lastStepWithTime?.timestamp || "",
      });
      detail.thinkingSteps = filteredSteps;
    }
  }

  const providerDetailsList = Array.from(providersMap.values());

  // Determine active provider tab
  const [selectedTab, setSelectedTab] = useState<string | undefined>(
    inspectedProvider || (providerDetailsList[0]?.provider)
  );

  useEffect(() => {
    if (inspectedProvider) {
      setSelectedTab(inspectedProvider.toLowerCase());
    } else if (providerDetailsList.length > 0 && !selectedTab) {
      setSelectedTab(providerDetailsList[0].provider);
    }
  }, [inspectedProvider, providerDetailsList.length]);

  const activeDetail =
    providerDetailsList.find((p) => p.provider === selectedTab) ||
    providerDetailsList[0];

  // Collect live sources
  const liveSources: any[] = [];
  const seenUrls = new Set<string>();
  for (const st of stepsToInspect) {
    const stepCitations: any[] = st.citations || st.data?.citations || [];
    for (const c of stepCitations) {
      if (c && c.url && !seenUrls.has(c.url)) {
        seenUrls.add(c.url);
        liveSources.push({
          url: c.url,
          title: c.title || c.url,
          domain: c.domain,
          snippet: c.snippet,
        });
      }
    }
  }

  const sources =
    currentMessage?.sources && currentMessage.sources.length > 0
      ? currentMessage.sources
      : liveSources;

  const getDomainIconColor = (domain: string) => {
    if (domain.includes("google")) return { bg: "#ea4335", text: "#fff", char: "G" };
    if (domain.includes("medium")) return { bg: "#000000", text: "#fff", char: "M" };
    if (domain.includes("producthunt")) return { bg: "#da552f", text: "#fff", char: "P" };
    if (domain.includes("linkedin")) return { bg: "#0a66c2", text: "#fff", char: "in" };
    if (domain.includes("microsoft")) return { bg: "#00a4ef", text: "#fff", char: "MS" };
    if (domain.includes("github")) return { bg: "#24292e", text: "#fff", char: "GH" };
    if (domain.includes("arxiv")) return { bg: "#b31b1b", text: "#fff", char: "ax" };
    return { bg: "#64748b", text: "#fff", char: "W" };
  };

  const displayProviders = selectedProviders.length > 0 ? selectedProviders : [selectedProvider];
  const activeDepth: DepthMode = currentMessage?.depth || depth || "deep";
  const reasoningModeLabel = activeDepth === "deep" ? "Deep Thinking" : "Standard";

  return (
    <aside
      className="right-sidebar"
      style={{
        width: `${sidebarWidth}px`,
        minWidth: `${sidebarWidth}px`,
        maxWidth: `${sidebarWidth}px`,
      }}
    >
      {/* Draggable resize handle on the left edge */}
      <div
        className={`right-sidebar-resizer ${isResizing ? "resizing" : ""}`}
        onMouseDown={handleResizeStart}
        title="Kéo sang trái/phải để thay đổi độ rộng (Drag to resize)"
      />

      {/* Model Showcase Header */}
      {/* <div className="model-header-showcase">
        {displayProviders.length > 1 ? (
          <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap", justifyContent: "center" }}>
            {displayProviders.map((p) => (
              <div key={p.id} title={`${p.name}: ${p.modelName}`}>
                <ModelBadgeLogo type={p.iconType} size={38} />
              </div>
            ))}
          </div>
        ) : (
          <ModelBadgeLogo type={selectedProvider.iconType} size={54} />
        )} */}

      {/* <h2 className="model-title-text">
          {displayProviders.length > 1
            ? `${displayProviders.length} Models Selected`
            : selectedProvider.modelName}
        </h2>
        <p className="model-desc-text">
          {displayProviders.length > 1
            ? displayProviders.map((p) => p.name).join(" • ")
            : selectedProvider.shortDesc}
        </p> */}

      {/* Model Specs Grid */}
      {/* <div className="model-specs-grid">
          <div className="spec-item">
            <span className="spec-label">Reasoning Mode</span>
            <span
              className="spec-value"
              style={{
                color: activeDepth === "deep" ? "var(--brand-blue)" : "var(--text-secondary)",
                fontWeight: 700,
              }}
            >
              {reasoningModeLabel}
            </span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Active Models</span>
            <span className="spec-value">{displayProviders.length} Engines</span>
          </div>
        </div>
      </div> */}

      {/* Real-time Status / Execution Steps Pills */}
      {/* <div className="status-pills-list">
        {currentQuery && (
          <div className="status-pill-green">
            <CheckCircleIcon size={16} color="#059669" />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              Query: <strong>{currentQuery.slice(0, 32)}</strong>
            </span>
          </div>
        )}

        {isGenerating && (
          <div className="status-pill-blue">
            <div
              style={{
                width: 14,
                height: 14,
                border: "2px solid #bfdbfe",
                borderTopColor: "var(--brand-blue)",
                borderRadius: "50%",
                animation: "spin 1s linear infinite",
              }}
            />
            <span style={{ fontSize: 12 }}>
              {activeSteps[activeSteps.length - 1]?.message || "Đang nghiên cứu đa mô hình..."}
            </span>
          </div>
        )}
      </div> */}

      {/* DEDICATED THINKING STEPS & REASONING DETAIL CARD */}
      <div
        className="thinking-details-card"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <BrainIcon size={16} color="var(--brand-blue)" />
            <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--brand-blue)" }}>
              Chi tiết tiến trình suy luận
            </span>
          </div>
          {activeDetail && (
            <span
              style={{
                fontSize: 10.5,
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: 12,
                backgroundColor: activeDetail.isRunning ? "#eff6ff" : "#ecfdf5",
                color: activeDetail.isRunning ? "#1d4ed8" : "#059669",
                border: `1px solid ${activeDetail.isRunning ? "#bfdbfe" : "#a7f3d0"}`,
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              {activeDetail.isRunning ? (
                <>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#3b82f6" }} />
                  Live DOM
                </>
              ) : (
                <>
                  <span style={{ fontWeight: 700 }}>✓</span>
                  Đã hoàn thành
                </>
              )}
            </span>
          )}
        </div>

        {/* Provider Switcher Tabs if multiple providers exist */}
        {providerDetailsList.length > 1 && (
          <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 2 }}>
            {providerDetailsList.map((prov) => {
              const isSelected = (selectedTab || providerDetailsList[0].provider) === prov.provider;
              return (
                <button
                  key={prov.provider}
                  type="button"
                  onClick={() => {
                    setSelectedTab(prov.provider);
                    onSelectProvider?.(prov.provider);
                  }}
                  style={{
                    fontSize: 11.5,
                    fontWeight: 600,
                    padding: "4px 10px",
                    borderRadius: 6,
                    border: isSelected ? "1.5px solid var(--brand-blue)" : "1px solid var(--border-default)",
                    backgroundColor: isSelected ? "var(--brand-blue-light)" : "var(--bg-app)",
                    color: isSelected ? "var(--brand-blue)" : "var(--text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    whiteSpace: "nowrap",
                    transition: "all 0.15s ease",
                  }}
                >
                  <span>{prov.displayName}</span>
                  <span
                    style={{
                      fontSize: 10,
                      padding: "0 5px",
                      borderRadius: 8,
                      backgroundColor: isSelected ? "var(--brand-blue)" : "#e2e8f0",
                      color: isSelected ? "#ffffff" : "var(--text-secondary)",
                    }}
                  >
                    {prov.thinkingSteps.length}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {activeDetail ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Provider & Datetime Header Info */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 10px",
                backgroundColor: "#f8fafc",
                borderRadius: 6,
                border: "1px solid #e2e8f0",
                fontSize: 11.5,
              }}
            >
              <span style={{ fontWeight: 700, color: "var(--brand-blue)" }}>
                ✦ {activeDetail.displayName} ({activeDetail.thinkingSteps.length} bước suy luận & tìm kiếm)
              </span>
              {activeDetail.timestamp && (
                <span style={{ color: "var(--text-muted)", fontSize: 11 }}>
                  ⏱ {activeDetail.timestamp}
                </span>
              )}
            </div>

            {/* List of Detailed Thinking Steps with content and datetime */}
            {activeDetail.thinkingSteps.length > 0 ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  maxHeight: 340,
                  overflowY: "auto",
                  paddingRight: 2,
                }}
              >
                {activeDetail.thinkingSteps.map((stepItem, sIdx) => {
                  const isStepRunning = activeDetail.isRunning && stepItem.status === "running";
                  return (
                    <div
                      key={sIdx}
                      style={{
                        backgroundColor: "#ffffff",
                        borderRadius: 6,
                        border: isStepRunning ? "1.5px solid #93c5fd" : "1px solid #e2e8f0",
                        padding: "8px 10px",
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                        boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
                      }}
                    >
                      {/* Step Title, Index & Status */}
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                          {isStepRunning ? (
                            <div
                              style={{
                                width: 10,
                                height: 10,
                                border: "2px solid #3b82f6",
                                borderTopColor: "transparent",
                                borderRadius: "50%",
                                animation: "spin 0.8s linear infinite",
                                flexShrink: 0,
                              }}
                            />
                          ) : (
                            <span style={{ color: "#059669", fontWeight: 700, flexShrink: 0 }}>✓</span>
                          )}
                          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>#{sIdx + 1}</span>
                          <span style={{ color: "var(--brand-blue)" }}>{stepItem.title}</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          {stepItem.timestamp && (
                            <span style={{ fontSize: 10.5, color: "var(--text-muted)" }}>
                              {stepItem.timestamp}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Step Detailed Content */}
                      {stepItem.description && (
                        stepItem.title.toLowerCase().includes("response generated") ? (
                          <div
                            style={{
                              display: "flex",
                              flexDirection: "column",
                              gap: 6,
                              marginTop: 4,
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                padding: "4px 8px",
                                backgroundColor: "#eff6ff",
                                borderRadius: 4,
                                border: "1px solid #bfdbfe",
                              }}
                            >
                              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--brand-blue)" }}>
                                ✦ Phản hồi thực tế từ mô hình (Response Content)
                              </span>
                              <button
                                type="button"
                                onClick={() => copyStepText(stepItem.description || "", sIdx)}
                                style={{
                                  border: "none",
                                  background: "none",
                                  color: "var(--brand-blue)",
                                  fontSize: 11,
                                  fontWeight: 600,
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 4,
                                  cursor: "pointer",
                                  padding: "2px 6px",
                                  borderRadius: 4,
                                }}
                                title="Sao chép toàn bộ phản hồi"
                              >
                                <CopyIcon size={12} />
                                <span>{copiedStepIdx === sIdx ? "Đã sao chép!" : "Sao chép"}</span>
                              </button>
                            </div>
                            <div
                              style={{
                                fontSize: 12,
                                lineHeight: 1.6,
                                color: "var(--text-primary)",
                                backgroundColor: "#ffffff",
                                padding: "10px 12px",
                                borderRadius: 4,
                                whiteSpace: "pre-wrap",
                                maxHeight: 380,
                                overflowY: "auto",
                                border: "1px solid #e2e8f0",
                                borderLeft: "3.5px solid var(--brand-blue)",
                                boxShadow: "inset 0 1px 2px rgba(0,0,0,0.02)",
                              }}
                            >
                              {stepItem.description}
                            </div>
                          </div>
                        ) : (
                          <div
                            style={{
                              fontSize: 11,
                              lineHeight: 1.5,
                              color: "var(--text-secondary)",
                              backgroundColor: "#f8fafc",
                              padding: "6px 8px",
                              borderRadius: 4,
                              whiteSpace: "pre-wrap",
                              fontFamily: "var(--font-geist-mono, monospace)",
                              maxHeight: 160,
                              overflowY: "auto",
                              border: "1px solid #f1f5f9",
                            }}
                          >
                            {stepItem.description}
                          </div>
                        )
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ padding: "14px 8px", textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                Đang chờ các bước suy luận từ mô hình...
              </div>
            )}

            {/* Raw Thinking Reasoning Text if available */}
            {/* {activeDetail.thinkingText && (
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
                <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--brand-blue)" }}>
                  ✦ Nội dung suy luận chi tiết ({activeDetail.thinkingText.length} ký tự):
                </span>
                <div
                  style={{
                    fontSize: 11,
                    lineHeight: 1.5,
                    color: "var(--text-secondary)",
                    backgroundColor: "#f8fafc",
                    padding: "8px 10px",
                    borderRadius: 6,
                    border: "1px solid #e2e8f0",
                    maxHeight: 160,
                    overflowY: "auto",
                    whiteSpace: "pre-wrap",
                    fontFamily: "var(--font-geist-mono, monospace)",
                  }}
                >
                  {activeDetail.thinkingText}
                </div>
              </div>
            )} */}

            {/* Citations from DOM */}
            {activeDetail.citations.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 5, marginTop: 4 }}>
                <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--brand-blue)" }}>
                  ✦ Nguồn trích dẫn từ DOM ({activeDetail.citations.length}):
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {activeDetail.citations.map((c, cIdx) => (
                    <a
                      key={cIdx}
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        fontSize: 11,
                        padding: "3px 8px",
                        borderRadius: 4,
                        backgroundColor: "#f1f5f9",
                        color: "var(--brand-blue)",
                        border: "1px solid #cbd5e1",
                        textDecoration: "none",
                        maxWidth: 240,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={c.title || c.url}
                    >
                      🔗 {c.title || c.url}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Provider Pipeline Trace Log */}
            {activeDetail.logs.length > 0 && (
              <details
                style={{
                  fontSize: 11.5,
                  marginTop: 4,
                  backgroundColor: "#f8fafc",
                  borderRadius: 6,
                  border: "1px solid #e2e8f0",
                  padding: "6px 8px",
                }}
              >
                <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--text-muted)", fontSize: 11 }}>
                  Nhật ký thực thi ({activeDetail.logs.length} sự kiện)
                </summary>
                <div style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 6, maxHeight: 120, overflowY: "auto" }}>
                  {activeDetail.logs.map((st, idx) => (
                    <div key={idx} style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 6, alignItems: "flex-start" }}>
                      <span style={{ color: "#059669", fontWeight: 700 }}>✓</span>
                      <span style={{ flex: 1 }}>{st.message}</span>
                      {st.timestamp && <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{st.timestamp}</span>}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ) : (
          <div style={{ padding: "16px 8px", textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
            Chưa có thông tin suy luận chi tiết cho tin nhắn này.
          </div>
        )}
      </div>

      {/* Citations & Sources Card */}
      <div className="sources-card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
            Nguồn trích dẫn tổng hợp ({sources.length})
          </span>
          {sources.length > 0 && (
            <span style={{ fontSize: 11, color: "var(--accent-success)", fontWeight: 600 }}>
              Đã xác thực
            </span>
          )}
        </div>

        {sources.length > 0 ? (
          <>
            <div className="sources-card-body" style={{ maxHeight: 130, overflowY: "auto" }}>
              <ol style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 8, margin: 0 }}>
                {sources.map((src, i) => (
                  <li key={i} style={{ fontSize: 12, lineHeight: 1.4 }}>
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: "var(--text-primary)", textDecoration: "none", fontWeight: 500 }}
                    >
                      {src.title}
                    </a>
                  </li>
                ))}
              </ol>
            </div>

            {/* Domain Badges Grid */}
            <div className="sources-badges-grid">
              {sources.map((src, i) => {
                const domain = src.domain || (src.url ? new URL(src.url).hostname.replace("www.", "") : "web");
                const iconInfo = getDomainIconColor(domain);

                return (
                  <a
                    key={i}
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="domain-pill-link"
                    title={src.title}
                  >
                    <span
                      className="domain-favicon"
                      style={{ backgroundColor: iconInfo.bg, color: iconInfo.text }}
                    >
                      {iconInfo.char}
                    </span>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {domain}
                    </span>
                    <ExternalLinkIcon size={11} color="var(--text-muted)" />
                  </a>
                );
              })}
            </div>
          </>
        ) : (
          <div style={{ padding: "12px 6px", textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
            Chưa có trích dẫn nguồn cho tin nhắn hiện tại
          </div>
        )}
      </div>
    </aside>
  );
}
