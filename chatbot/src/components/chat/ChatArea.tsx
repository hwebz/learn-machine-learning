"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { ChatSession, DepthMode, ProviderInfo, StepLog, ThinkingStep, SourceLink, Message } from "../../types/chat";
import { SUGGESTED_PROMPTS } from "../../lib/constants";
import { extractProviderResponse } from "../../lib/providerResponse";
import { MarkdownContent } from "./MarkdownContent";
import { ProviderActionBanner } from "./ProviderActionBanner";
import { detectAllProvidersNeedingAction } from "../../lib/providerAction";
import {
  PlusIcon,
  SettingsIcon,
  SidebarCollapseIcon,
  ShareIcon,
  RefreshIcon,
  CopyIcon,
  BookmarkIcon,
  MoreHorizontalIcon,
  LibraryIcon,
  PaperclipIcon,
  ImageIcon,
  MicIcon,
  GridIcon,
  SendIcon,
  StopIcon,
  BrainIcon,
  ChevronRightIcon,
  ModelBadgeLogo,
  ArrowUpCircleIcon,
  ArrowDownCircleIcon,
  ExternalLinkIcon,
} from "../icons/Icons";

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

function isThinkingEvent(st: StepLog): boolean {
  if (st.step === "thinking_progress") return true;
  if (st.isThinking || st.data?.is_thinking) return true;
  if (/đang suy luận/i.test(st.message)) return true;
  return false;
}

interface TimelineLogItem {
  kind: "log";
  key: string;
  message: string;
  timestamp: string;
  isLatest?: boolean;
}

interface TimelineThinkingItem {
  kind: "thinking";
  key: string;
  provider: string;
  steps: ThinkingStep[];
  text?: string;
  citations: SourceLink[];
  isRunning: boolean;
  timestamp: string;
}

type TimelineItem = TimelineLogItem | TimelineThinkingItem;

function buildChronologicalTimeline(
  steps: StepLog[],
  isLive: boolean,
  message?: Message
): TimelineItem[] {
  if (!steps || steps.length === 0) return [];

  // 1. Identify all providers in order of appearance
  const providersOrder: string[] = [];
  for (const st of steps) {
    const p = extractProvider(st);
    if (p && !providersOrder.includes(p)) {
      providersOrder.push(p);
    }
  }
  if (providersOrder.length === 0) {
    providersOrder.push("");
  }

  // 2. Pre-aggregate thinking details per provider
  const providerDataMap = new Map<
    string,
    {
      thinkingSteps: ThinkingStep[];
      thinkingText: string;
      citations: SourceLink[];
      hasThinking: boolean;
      isRunning: boolean;
    }
  >();

  for (const p of providersOrder) {
    const pSteps = steps.filter((st) => {
      const sp = extractProvider(st);
      return sp === p || (providersOrder.length === 1 && !sp);
    });

    const stepMap = new Map<string, ThinkingStep>();
    for (const st of pSteps) {
      const raw = st.thinkingSteps || st.data?.thinking_steps || [];
      for (const item of raw) {
        if (!item || !item.title) continue;
        const normKey = item.title.trim().toLowerCase();
        const existing = stepMap.get(normKey);
        if (!existing) {
          stepMap.set(normKey, { ...item });
        } else {
          existing.status = item.status || existing.status;
          if (item.description && item.description.trim()) {
            existing.description = item.description;
          }
        }
      }
    }
    const accumulatedSteps = Array.from(stepMap.values());

    const citMap = new Map<string, SourceLink>();
    for (const st of pSteps) {
      const rawCits = st.citations || st.data?.citations || [];
      for (const c of rawCits) {
        if (c && c.url && !citMap.has(c.url)) {
          citMap.set(c.url, {
            title: c.title || c.url,
            url: c.url,
            domain: c.domain,
          });
        }
      }
    }
    const accumulatedCitations = Array.from(citMap.values());

    let accumulatedText = "";
    for (const st of [...pSteps].reverse()) {
      const t = st.thinkingText || st.data?.thinking_text;
      if (t && typeof t === "string" && t.trim().length > 0) {
        accumulatedText = t;
        break;
      }
    }

    const isProviderFinished = pSteps.some(
      (st) =>
        st.step === "response_valid" ||
        st.step === "response_partial" ||
        st.step === "completed" ||
        st.step === "failed" ||
        st.status === "completed" ||
        (st.data && (st.data.status === "ok" || st.data.status === "partial" || Boolean(st.data.response_markdown))) ||
        /hoàn thành|phản hồi hợp lệ|kết quả một phần|thất bại|đã trả về|response_valid/i.test(st.message)
    );
    const isRunning = isLive && !isProviderFinished;

    if (!isRunning) {
      for (const s of accumulatedSteps) {
        s.status = "completed";
      }
    } else {
      const lastRunningIdx = accumulatedSteps.map((s) => s.status).lastIndexOf("running");
      if (lastRunningIdx >= 0) {
        for (let idx = 0; idx < lastRunningIdx; idx++) {
          accumulatedSteps[idx].status = "completed";
        }
      }
    }

    const providerResp = extractProviderResponse(p, pSteps, message);
    if (providerResp) {
      const filtered = accumulatedSteps.filter(
        (s) => !s.title.toLowerCase().includes("response generated")
      );
      filtered.push({
        title: "Response generated",
        description: providerResp,
        status: "completed",
      });
      accumulatedSteps.length = 0;
      accumulatedSteps.push(...filtered);
    }

    const hasThinking =
      accumulatedSteps.length > 0 ||
      Boolean(accumulatedText) ||
      accumulatedCitations.length > 0 ||
      (isLive && pSteps.some(isThinkingEvent));

    providerDataMap.set(p, {
      thinkingSteps: accumulatedSteps,
      thinkingText: accumulatedText,
      citations: accumulatedCitations,
      hasThinking,
      isRunning,
    });
  }

  // 3. Assemble chronological timeline
  const timeline: TimelineItem[] = [];
  const placedThinking = new Set<string>();
  let lastLogMessage = "";

  for (let i = 0; i < steps.length; i++) {
    const st = steps[i];
    const p = extractProvider(st);
    const pData =
      providerDataMap.get(p) ||
      (providersOrder.length === 1 ? providerDataMap.get(providersOrder[0]) : undefined);

    // If pure thinking event, skip adding as log line and insert thinking item if not yet placed
    if (isThinkingEvent(st)) {
      if (pData && pData.hasThinking && !placedThinking.has(p)) {
        timeline.push({
          kind: "thinking",
          key: `thinking-${p || "default"}-${i}`,
          provider: p,
          steps: pData.thinkingSteps,
          text: pData.thinkingText,
          citations: pData.citations,
          isRunning: pData.isRunning,
          timestamp: st.timestamp,
        });
        placedThinking.add(p);
      }
      continue;
    }

    // If generating step and thinking block has not been placed yet, insert thinking before generating
    if (
      pData &&
      pData.hasThinking &&
      !placedThinking.has(p) &&
      (st.step === "generating" || /đang đợi.*sinh câu trả lời/i.test(st.message))
    ) {
      timeline.push({
        kind: "thinking",
        key: `thinking-${p || "default"}-${i}`,
        provider: p,
        steps: pData.thinkingSteps,
        text: pData.thinkingText,
        citations: pData.citations,
        isRunning: pData.isRunning,
        timestamp: st.timestamp,
      });
      placedThinking.add(p);
    }

    // Normal pipeline log line (deduplicating consecutive identical messages)
    if (st.message && st.message !== lastLogMessage) {
      timeline.push({
        kind: "log",
        key: st.id || `log-${i}-${st.message}`,
        message: st.message,
        timestamp: st.timestamp,
      });
      lastLogMessage = st.message;
    }

    // If submitting step and thinking block has not been placed yet, insert thinking right after submitting
    if (
      pData &&
      pData.hasThinking &&
      !placedThinking.has(p) &&
      (st.step === "submitting" || /đã gửi câu hỏi/i.test(st.message))
    ) {
      timeline.push({
        kind: "thinking",
        key: `thinking-${p || "default"}-${i}`,
        provider: p,
        steps: pData.thinkingSteps,
        text: pData.thinkingText,
        citations: pData.citations,
        isRunning: pData.isRunning,
        timestamp: st.timestamp,
      });
      placedThinking.add(p);
    }
  }

  // 4. Fallback: Place any unplaced provider thinking block
  for (const [prov, data] of providerDataMap.entries()) {
    if (data.hasThinking && !placedThinking.has(prov)) {
      timeline.push({
        kind: "thinking",
        key: `thinking-${prov || "default"}-end`,
        provider: prov,
        steps: data.thinkingSteps,
        text: data.thinkingText,
        citations: data.citations,
        isRunning: data.isRunning,
        timestamp: "",
      });
      placedThinking.add(prov);
    }
  }

  // Mark latest item for live spinner
  if (isLive && timeline.length > 0) {
    const lastItem = timeline[timeline.length - 1];
    if (lastItem.kind === "log") {
      lastItem.isLatest = true;
    }
  }

  return timeline;
}

function ProviderThinkingHeader({
  item,
  isLive,
  onClick,
}: {
  item: TimelineThinkingItem;
  isLive: boolean;
  onClick?: () => void;
}) {
  const stepCount = item.steps.length || (item.text ? 1 : 0);
  const providerLabel = item.provider ? item.provider.toUpperCase() : "";

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      className="provider-thinking-header-btn"
      style={{
        backgroundColor: item.isRunning ? "#f0f7ff" : "#ffffff",
        borderRadius: 8,
        border: item.isRunning ? "1.5px solid #93c5fd" : "1px solid #cbd5e1",
        margin: "3px 0",
        padding: "8px 12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        cursor: "pointer",
        userSelect: "none",
        outline: "none",
        boxShadow: item.isRunning
          ? "0 2px 6px rgba(59, 130, 246, 0.08)"
          : "0 1px 2px rgba(0, 0, 0, 0.03)",
        transition: "all 0.15s ease",
      }}
      title="Nhấn để xem chi tiết các bước suy luận trên thanh bên phải"
    >
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <BrainIcon size={14} color="var(--brand-blue)" />
        <span style={{ color: "var(--brand-blue)", fontWeight: 700, fontSize: 12 }}>
          ✦ Các bước suy luận & tìm kiếm ({stepCount}){providerLabel ? ` — ${providerLabel}` : ""}:
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {isLive && item.isRunning ? (
          <span
            style={{
              fontSize: 10.5,
              color: "#059669",
              backgroundColor: "#ecfdf5",
              padding: "2px 8px",
              borderRadius: 12,
              border: "1px solid #a7f3d0",
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              fontWeight: 600,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "#059669",
              }}
            />
            Live DOM
          </span>
        ) : null}
        <span
          style={{
            fontSize: 11,
            color: "var(--brand-blue)",
            fontWeight: 600,
            display: "inline-flex",
            alignItems: "center",
            gap: 3,
            backgroundColor: "#eff6ff",
            padding: "3px 8px",
            borderRadius: 6,
            border: "1px solid #bfdbfe",
          }}
        >
          <span>Xem chi tiết</span>
          <ChevronRightIcon size={12} color="var(--brand-blue)" />
        </span>
      </div>
    </div>
  );
}

function ChronologicalTimeline({
  steps,
  isLive = false,
  message,
  onSelectThinking,
}: {
  steps: StepLog[];
  isLive?: boolean;
  message?: Message;
  onSelectThinking?: (provider?: string, message?: Message) => void;
}) {
  const items = buildChronologicalTimeline(steps, isLive, message);

  if (items.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {items.map((item) => {
        if (item.kind === "thinking") {
          return (
            <ProviderThinkingHeader
              key={item.key}
              item={item}
              isLive={isLive}
              onClick={() => onSelectThinking?.(item.provider, message)}
            />
          );
        }

        return (
          <div
            key={item.key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color: item.isLatest ? "var(--text-primary)" : "var(--text-secondary)",
              fontWeight: item.isLatest ? 600 : 400,
              padding: "2px 4px",
              borderRadius: 4,
              backgroundColor: item.isLatest ? "var(--brand-blue-light)" : "transparent",
            }}
          >
            {item.isLatest ? (
              <div
                style={{
                  width: 11,
                  height: 11,
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
            <span style={{ flex: 1 }}>{item.message}</span>
            {item.timestamp && (
              <span style={{ fontSize: 10.5, color: "var(--text-muted)" }}>
                {item.timestamp}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

interface ChatAreaProps {
  session: ChatSession;
  providers: ProviderInfo[];
  selectedProvider: ProviderInfo;
  selectedProviders: ProviderInfo[];
  onToggleProvider: (providerId: string) => void;
  onToggleDepth: (depth: DepthMode) => void;
  onSendMessage: (content: string) => void;
  onToggleRightSidebar: () => void;
  isGenerating: boolean;
  onOpenProvidersModal: () => void;
  activeSteps?: StepLog[];
  onSelectThinking?: (provider?: string, message?: Message) => void;
  onStopResearch?: () => void;
  onRetryProvider?: (provider: string, jobId?: string) => void;
}

export function ChatArea({
  session,
  providers,
  selectedProvider,
  selectedProviders,
  onToggleProvider,
  onToggleDepth,
  onSendMessage,
  onToggleRightSidebar,
  isGenerating,
  onOpenProvidersModal,
  activeSteps = [],
  onSelectThinking,
  onStopResearch,
  onRetryProvider,
}: ChatAreaProps) {
  const [inputText, setInputText] = useState("");
  const [isCopied, setIsCopied] = useState<string | null>(null);
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [canScrollTop, setCanScrollTop] = useState(false);
  const [canScrollBottom, setCanScrollBottom] = useState(false);
  const [showScrollNav, setShowScrollNav] = useState(false);

  const checkScrollState = useCallback(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const isScrollable = scrollHeight > clientHeight + 30;
    setShowScrollNav(isScrollable);
    setCanScrollTop(scrollTop > 40);
    setCanScrollBottom(scrollHeight - scrollTop - clientHeight > 40);
  }, []);

  useEffect(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    checkScrollState();
    el.addEventListener("scroll", checkScrollState, { passive: true });
    window.addEventListener("resize", checkScrollState);
    return () => {
      el.removeEventListener("scroll", checkScrollState);
      window.removeEventListener("resize", checkScrollState);
    };
  }, [checkScrollState, session.messages, isGenerating, activeSteps]);

  const scrollToTop = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    }
  };

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    } else {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session.messages, isGenerating]);

  // Adjust textarea height automatically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [inputText]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!inputText.trim() || isGenerating) return;
    onSendMessage(inputText.trim());
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setIsCopied(id);
    setTimeout(() => setIsCopied(null), 2000);
  };

  const selectedCount = selectedProviders.length;

  return (
    <main className="main-chat-area">
      {/* Top Header Bar */}
      <header className="chat-header">
        <div className="chat-title-group">
          {/* <h1 className="chat-title">{session.title}</h1> */}

          {/* Model Selector Pill / Multi-Model Dropdown */}
          <div style={{ position: "relative" }}>
            <button
              className="model-badge-trigger"
              onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
              title="Chọn mô hình / Thêm nhiều nhà cung cấp"
            >
              {selectedCount > 1 ? (
                <>
                  <span style={{ display: "inline-flex", gap: 3, alignItems: "center" }}>
                    {selectedProviders.slice(0, 3).map((p) => (
                      <ModelBadgeLogo key={p.id} type={p.iconType} size={15} />
                    ))}
                  </span>
                  <span>{selectedCount} Models Selected</span>
                </>
              ) : (
                <>
                  <ModelBadgeLogo type={selectedProvider.iconType} size={16} />
                  <span>{selectedProvider.name.split(" ")[0]}</span>
                </>
              )}
              <span style={{ fontSize: 10, color: "var(--text-muted)" }}>▼</span>
            </button>

            {isModelDropdownOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "115%",
                  left: 0,
                  width: 310,
                  backgroundColor: "#ffffff",
                  borderRadius: "var(--radius-lg)",
                  boxShadow: "var(--shadow-lg)",
                  border: "1px solid var(--border-default)",
                  zIndex: 50,
                  padding: "8px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "4px 8px",
                    borderBottom: "1px solid var(--border-subtle)",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)" }}>
                    ACTIVE MODELS ({selectedCount}/{providers.length})
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setIsModelDropdownOpen(false);
                      onOpenProvidersModal();
                    }}
                    style={{
                      border: "none",
                      background: "none",
                      fontSize: 11,
                      color: "var(--brand-blue)",
                      fontWeight: 600,
                      cursor: "pointer",
                      padding: 0,
                    }}
                  >
                    Mở thư viện ↗
                  </button>
                </div>

                <div style={{ maxHeight: 280, overflowY: "auto", display: "flex", flexDirection: "column", gap: "2px" }}>
                  {providers.map((p) => {
                    const isChecked = selectedProviders.some((sp) => sp.id === p.id);
                    return (
                      <div
                        key={p.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 8px",
                          borderRadius: "var(--radius-sm)",
                          fontSize: 12.5,
                          backgroundColor: isChecked ? "var(--brand-blue-light)" : "transparent",
                          cursor: "pointer",
                        }}
                        onClick={() => onToggleProvider(p.id)}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => onToggleProvider(p.id)}
                          style={{ cursor: "pointer", accentColor: "var(--brand-blue)" }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <ModelBadgeLogo type={p.iconType} size={18} />
                        <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
                          <span style={{ fontWeight: isChecked ? 600 : 400, color: "var(--text-primary)" }}>
                            {p.name}
                          </span>
                          <span style={{ fontSize: 10.5, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {p.modelName}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Depth Mode Switcher (Standard vs Think Deeper) */}
          <div className="depth-pill-toggle" title="Chuyển đổi mức độ suy luận / Thinking Effort">
            <button
              className={`depth-pill-btn ${session.depth === "standard" ? "active" : ""}`}
              onClick={() => onToggleDepth("standard")}
            >
              Standard
            </button>
            <button
              className={`depth-pill-btn ${session.depth === "deep" ? "active" : ""}`}
              onClick={() => onToggleDepth("deep")}
            >
              <BrainIcon size={12} color={session.depth === "deep" ? "var(--brand-blue)" : "currentColor"} />
              Think Deeper
            </button>
          </div>
        </div>

        {/* Right Header Actions */}
        <div className="chat-header-actions">
          <button
            className="icon-btn"
            title="Inspect Details / Citations"
            onClick={onToggleRightSidebar}
            aria-label="Toggle Details Panel"
          >
            <SidebarCollapseIcon size={16} />
          </button>
        </div>
      </header>

      {/* Message Stream */}
      <div ref={messagesContainerRef} className="messages-scroll-container">
        {/* Empty State / Welcome Screen when session has no messages */}
        {session.messages.length === 0 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "40px 20px",
              textAlign: "center",
              gap: 20,
              maxWidth: 680,
              margin: "0 auto",
            }}
          >
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: "50%",
                background: "linear-gradient(135deg, var(--brand-blue) 0%, #7c3aed 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
                boxShadow: "0 8px 24px rgba(37, 99, 235, 0.25)",
              }}
            >
              <BrainIcon size={32} color="#ffffff" />
            </div>

            <div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
                AI Deep Research Hub
              </h2>
              <p style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                Nghiên cứu bằng việc sử dụng đa mô hình cùng lúc. Nhập câu hỏi bên dưới hoặc chọn gợi ý nghiên cứu:
              </p>
            </div>

            {/* Suggested Prompts Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
                width: "100%",
                marginTop: 10,
              }}
            >
              {SUGGESTED_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendMessage(prompt)}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-default)",
                    backgroundColor: "#ffffff",
                    textAlign: "left",
                    fontSize: 12.5,
                    color: "var(--text-primary)",
                    lineHeight: 1.4,
                    cursor: "pointer",
                    boxShadow: "var(--shadow-xs)",
                    transition: "all var(--transition-fast)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "var(--brand-blue)";
                    e.currentTarget.style.backgroundColor = "var(--brand-blue-light)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "var(--border-default)";
                    e.currentTarget.style.backgroundColor = "#ffffff";
                  }}
                >
                  <span style={{ color: "var(--brand-blue)", fontWeight: 700, marginRight: 6 }}>✦</span>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {session.messages.map((msg) => (
          <div key={msg.id} className="message-item animate-fade-in">
            {/* Message Author Header */}
            <div className="message-header">
              {msg.role === "user" ? (
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
                    color: "#ffffff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    fontSize: 12,
                    boxShadow: "var(--shadow-xs)",
                  }}
                >
                  U
                </div>
              ) : (
                <div
                  className="author-avatar-badge"
                  style={{
                    background:
                      selectedProvider.avatarBg ||
                      "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <ModelBadgeLogo type={selectedProvider.iconType} size={18} />
                </div>
              )}
              <span className="author-name">{msg.authorName}</span>
              <span className="message-timestamp">{msg.timestamp}</span>

              {/* Multi-provider badges if this message combined multiple models */}
              {msg.providers && msg.providers.length > 0 && (
                <div style={{ display: "flex", gap: 4, marginLeft: 8 }}>
                  {msg.providers.map((pId) => {
                    const pInfo = providers.find((p) => p.id === pId);
                    return (
                      <span
                        key={pId}
                        style={{
                          fontSize: 10,
                          fontWeight: 600,
                          padding: "2px 7px",
                          borderRadius: 4,
                          backgroundColor: "#f1f5f9",
                          color: pInfo?.color || "var(--text-secondary)",
                          border: "1px solid #e2e8f0",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        <ModelBadgeLogo type={pInfo?.iconType || pId} size={12} />
                        {pInfo?.name || pId}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Message Body */}
            {msg.role === "user" ? (
              <div className="message-bubble-user">{msg.content}</div>
            ) : (
              <div className="message-card-assistant">
                {/* Assistant Top Tool Badges */}

                {/* Real-time Thinking Process & Pipeline Steps Accordion */}
                {msg.steps && msg.steps.length > 0 && (
                  <details
                    className="message-steps-accordion"
                    style={{
                      backgroundColor: "#f8fafc",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid #e2e8f0",
                      padding: "10px 14px",
                      display: "flex",
                      flexDirection: "column"
                    }}
                  >
                    <summary
                      style={{
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--brand-blue)",
                        userSelect: "none",
                        outline: "none",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <BrainIcon size={14} color="var(--brand-blue)" />
                        <span>Real-time Thinking Steps ({msg.steps.length})</span>
                      </div>
                      <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>
                        SSE Pipeline Log
                      </span>
                    </summary>

                    <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
                      <ChronologicalTimeline
                        steps={msg.steps}
                        isLive={false}
                        message={msg}
                        onSelectThinking={onSelectThinking}
                      />
                    </div>
                  </details>
                )}

                {/* Action Required Banner for providers needing login/manual action */}
                {(() => {
                  const neededActions = detectAllProvidersNeedingAction(msg);
                  if (neededActions.length === 0) return null;
                  return (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "6px 0 10px 0" }}>
                      {neededActions.map((act) => (
                        <ProviderActionBanner
                          key={act.provider}
                          provider={act.provider}
                          reason={act.reason}
                          kind={act.kind}
                          jobId={session.jobId || session.id}
                          onContinue={(prov) => onRetryProvider?.(prov, session.jobId || session.id)}
                        />
                      ))}
                    </div>
                  );
                })()}

                {/* Main Content Body with Full Markdown & Syntax Highlighter */}
                <div className="message-content-body">
                  <MarkdownContent content={msg.content} />
                </div>

                {/* Citations & Source Links Section */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="message-sources-section">
                    <div className="message-sources-header">
                      <div className="message-sources-title">
                        <span style={{ fontSize: 13, marginRight: 5 }}>📚</span>
                        <span>Nguồn trích dẫn & Tham khảo ({msg.sources.length})</span>
                      </div>
                    </div>
                    <div className="message-sources-grid">
                      {msg.sources.map((src, sIdx) => {
                        let domain = "";
                        try {
                          domain = src.domain || (src.url ? new URL(src.url).hostname.replace(/^www\./, "") : "");
                        } catch {
                          domain = src.url || "source";
                        }
                        const rawTitle = src.title && src.title !== src.url ? src.title : domain;
                        const displayTitle = rawTitle.replace(/^\[[a-zA-Z0-9_\-:]+\]\s*/, "");
                        const loopKey = (src as any).id || src.url || `source-${sIdx}`;
                        return (
                          <a
                            key={loopKey}
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="message-source-chip"
                            title={`${displayTitle}\n${src.url}`}
                          >
                            <span className="message-source-index">{sIdx + 1}</span>
                            <span className="message-source-domain">{domain}</span>
                            <span className="message-source-title">{displayTitle}</span>
                            <ExternalLinkIcon size={12} color="var(--text-muted)" />
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Assistant Footer Row */}
                <div className="assistant-card-footer">
                  <div className="card-footer-icons">
                    <button
                      className="icon-btn"
                      title="Chạy lại nghiên cứu"
                      onClick={() => onSendMessage(session.messages[0]?.content || "Research more")}
                    >
                      <RefreshIcon size={15} />
                    </button>
                    <button
                      className="icon-btn"
                      title={isCopied === msg.id ? "Đã sao chép!" : "Sao chép câu trả lời"}
                      onClick={() => copyToClipboard(msg.content, msg.id)}
                    >
                      <CopyIcon size={15} />
                    </button>
                    <button
                      className="icon-btn"
                      title={isCopied === `share-${msg.id}` ? "Đã sao chép liên kết hội thoại!" : "Chia sẻ liên kết hội thoại (/chat/...)"}
                      onClick={() => {
                        const targetId = session.jobId || session.id;
                        const shareUrl = typeof window !== "undefined"
                          ? `${window.location.origin}/chat/${targetId}`
                          : `/chat/${targetId}`;
                        navigator.clipboard.writeText(shareUrl);
                        setIsCopied(`share-${msg.id}`);
                        setTimeout(() => setIsCopied(null), 2500);
                      }}
                    >
                      <ShareIcon size={15} color={isCopied === `share-${msg.id}` ? "var(--brand-blue)" : "currentColor"} />
                    </button>
                    <button className="icon-btn" title="Đánh dấu">
                      <BookmarkIcon size={15} />
                    </button>
                    <button className="icon-btn" title="Tùy chọn khác">
                      <MoreHorizontalIcon size={15} />
                    </button>
                  </div>

                  {(!!msg.tokens || !!msg.latencySeconds) && (
                    <span className="card-footer-token">
                      {msg.tokens ? `${msg.tokens} tokens` : ""}
                      {msg.latencySeconds ? ` · ${msg.latencySeconds}s` : ""}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Loading Indicator when bot is generating/thinking */}
        {isGenerating && (
          <div className="message-item animate-fade-in">
            <div className="message-header">
              <div
                className="author-avatar-badge"
                style={{
                  background: selectedProvider.avatarBg,
                  animation: "pulseGlow 1.5s infinite",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <ModelBadgeLogo type={selectedProvider.iconType} size={18} />
              </div>
              <span className="author-name">
                Multi-Model Engine ({selectedProviders.map((p) => p.name).join(", ")})
              </span>
            </div>
            <div
              className="message-card-assistant"
              style={{
                backgroundColor: "#ffffff",
                border: "1.5px solid #bfdbfe",
                boxShadow: "0 4px 12px rgba(37, 99, 235, 0.08)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid #f1f5f9",
                  paddingBottom: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <BrainIcon size={16} color="var(--brand-blue)" />
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--brand-blue)" }}>
                    {session.depth === "deep" ? "Deep Reasoning Pipeline Đang Chạy..." : "Đang xử lý song song..."}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      border: "2px solid #bfdbfe",
                      borderTopColor: "var(--brand-blue)",
                      borderRadius: "50%",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span style={{ fontSize: 11, fontWeight: 600, color: "var(--brand-blue)" }}>
                    SSE Live Stream
                  </span>
                </div>
              </div>

              {/* Live Action Required Banner if any provider is blocked during generation */}
              {(() => {
                const liveNeededActions = detectAllProvidersNeedingAction(undefined, activeSteps);
                if (liveNeededActions.length === 0) return null;
                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "6px 0 8px 0" }}>
                    {liveNeededActions.map((act) => (
                      <ProviderActionBanner
                        key={act.provider}
                        provider={act.provider}
                        reason={act.reason}
                        kind={act.kind}
                        jobId={session.jobId || session.id}
                        onContinue={(prov) => onRetryProvider?.(prov, session.jobId || session.id)}
                      />
                    ))}
                  </div>
                );
              })()}

              {/* Real-time Chronological Timeline Feed */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6, padding: "4px 0" }}>
                {activeSteps.length > 0 ? (
                  <ChronologicalTimeline steps={activeSteps} isLive={true} onSelectThinking={onSelectThinking} />
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}>
                    <div
                      style={{
                        width: 14,
                        height: 14,
                        border: "2px solid #cbd5e1",
                        borderTopColor: "var(--brand-blue)",
                        borderRadius: "50%",
                        animation: "spin 1s linear infinite",
                      }}
                    />
                    <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                      Khởi tạo phiên nghiên cứu và kết nối tới {selectedCount} trình duyệt...
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Scroll Navigation: Scroll to Top / Bottom */}
      {showScrollNav && (
        <div className="chat-scroll-nav">
          <button
            type="button"
            className={`scroll-nav-btn ${!canScrollTop ? "disabled" : ""}`}
            onClick={scrollToTop}
            disabled={!canScrollTop}
            title="Cuộn lên đầu trang (Scroll to top)"
            aria-label="Scroll to top"
          >
            <ArrowUpCircleIcon size={20} />
          </button>
          <button
            type="button"
            className={`scroll-nav-btn ${!canScrollBottom ? "disabled" : ""}`}
            onClick={scrollToBottom}
            disabled={!canScrollBottom}
            title="Cuộn xuống cuối trang (Scroll to bottom)"
            aria-label="Scroll to bottom"
          >
            <ArrowDownCircleIcon size={20} />
          </button>
        </div>
      )}

      {/* Floating Composer Card */}
      <div className="composer-floating-container">
        <div className="composer-card">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder={`Đặt câu hỏi nghiên cứu tới ${selectedCount} mô hình AI (${selectedProviders.map((p) => p.name.split(" ")[0]).join(", ")})...`}
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
          />

          <div className="composer-bottom-row">
            <div className="composer-left-actions">
              <button
                className="btn-composer-pill"
                onClick={onOpenProvidersModal}
                title="Mở Thư viện AI Models"
              >
                <LibraryIcon size={15} />
                <span>{selectedCount} Models</span>
              </button>

              <button className="icon-btn" title="Đính kèm tệp" aria-label="Đính kèm tệp">
                <PaperclipIcon size={17} />
              </button>
              <button className="icon-btn" title="Tải ảnh lên" aria-label="Tải ảnh lên">
                <ImageIcon size={17} />
              </button>
              <button className="icon-btn" title="Nhập liệu giọng nói" aria-label="Nhập liệu giọng nói">
                <MicIcon size={17} />
              </button>
            </div>

            {isGenerating ? (
              <button
                className="btn-composer-send btn-composer-stop"
                onClick={onStopResearch}
                type="button"
                title="Dừng phiên nghiên cứu ngay"
              >
                <StopIcon size={14} />
                <span>Dừng</span>
              </button>
            ) : (
              <button
                className="btn-composer-send"
                onClick={handleSend}
                disabled={!inputText.trim()}
                type="button"
                title="Gửi câu hỏi"
              >
                <SendIcon size={14} />
                <span>Gửi câu hỏi</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
