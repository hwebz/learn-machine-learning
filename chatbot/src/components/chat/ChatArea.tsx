"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { ChatSession, DepthMode, ProviderInfo, StepLog } from "../../types/chat";
import { SUGGESTED_PROMPTS } from "../../lib/constants";
import { MarkdownContent } from "./MarkdownContent";
import {
  PlusIcon,
  SettingsIcon,
  SidebarCollapseIcon,
  FactCheckIcon,
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
  BrainIcon,
  ModelBadgeLogo,
  ArrowUpCircleIcon,
  ArrowDownCircleIcon,
  ExternalLinkIcon,
} from "../icons/Icons";

interface ChatAreaProps {
  session: ChatSession;
  providers: ProviderInfo[];
  selectedProvider: ProviderInfo;
  selectedProviders: ProviderInfo[];
  onSelectProvider: (providerId: string) => void;
  onToggleProvider: (providerId: string) => void;
  onToggleDepth: (depth: DepthMode) => void;
  onSendMessage: (content: string) => void;
  onNewChat: () => void;
  onToggleRightSidebar: () => void;
  isGenerating: boolean;
  onOpenProvidersModal: () => void;
  activeSteps?: StepLog[];
}

export function ChatArea({
  session,
  providers,
  selectedProvider,
  selectedProviders,
  onSelectProvider,
  onToggleProvider,
  onToggleDepth,
  onSendMessage,
  onNewChat,
  onToggleRightSidebar,
  isGenerating,
  onOpenProvidersModal,
  activeSteps = [],
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
          <h1 className="chat-title">{session.title}</h1>

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
                      <span
                        key={p.id}
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: "50%",
                          backgroundColor: p.color,
                        }}
                      />
                    ))}
                  </span>
                  <span>{selectedCount} Models Selected</span>
                </>
              ) : (
                <>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: selectedProvider.color,
                    }}
                  />
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
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            backgroundColor: p.color,
                            flexShrink: 0,
                          }}
                        />
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
          <button className="btn-new-chat-outline" onClick={onNewChat}>
            <PlusIcon size={14} />
            <span>New chat</span>
          </button>
          <button
            className="icon-btn"
            title="Model and System Settings"
            onClick={onOpenProvidersModal}
            aria-label="Settings"
          >
            <SettingsIcon size={16} />
          </button>
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
                Nghiên cứu đa mô hình cùng lúc với <strong>{selectedCount}</strong> providers đang kích hoạt (
                {selectedProviders.map((p) => p.name).join(", ")}). Nhập câu hỏi bên dưới hoặc chọn gợi ý nghiên cứu:
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
                  }}
                >
                  AI
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
                          padding: "1px 6px",
                          borderRadius: 4,
                          backgroundColor: "#f1f5f9",
                          color: pInfo?.color || "var(--text-secondary)",
                          border: "1px solid #e2e8f0",
                        }}
                      >
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
                <div className="assistant-card-top-bar">
                  <button className="tool-badge-btn" title="Kiểm tra đối chiếu thực tế">
                    <FactCheckIcon size={13} />
                    <span>Fact check</span>
                  </button>
                  <button
                    className="tool-badge-btn"
                    title="Sao chép nội dung"
                    onClick={() => copyToClipboard(msg.content, msg.id)}
                  >
                    <ShareIcon size={13} />
                    <span>Chia sẻ</span>
                  </button>
                </div>

                {/* Real-time Thinking Process & Pipeline Steps Accordion */}
                {msg.steps && msg.steps.length > 0 && (
                  <div
                    style={{
                      backgroundColor: "#f8fafc",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid #e2e8f0",
                      padding: "10px 14px",
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--brand-blue)",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <BrainIcon size={14} color="var(--brand-blue)" />
                        <span>Real-time Thinking Steps ({msg.steps.length})</span>
                      </div>
                      <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>
                        SSE Pipeline Log
                      </span>
                    </div>

                    {(() => {
                      // Extract latest thinking steps once to avoid duplicating under every step
                      const latestThinkingStep = [...msg.steps].reverse().find(
                        (s) =>
                          (s.thinkingSteps && s.thinkingSteps.length > 0) ||
                          (s.data?.thinking_steps && s.data.thinking_steps.length > 0) ||
                          s.thinkingText ||
                          s.data?.thinking_text
                      );
                      const rawSteps = latestThinkingStep?.thinkingSteps || latestThinkingStep?.data?.thinking_steps || [];
                      const seenStepKeys = new Set<string>();
                      const uniqueThinkingSteps = rawSteps.filter((step: any) => {
                        const k = `${(step.title || "").trim()}::${(step.description || "").trim()}`;
                        if (seenStepKeys.has(k)) return false;
                        seenStepKeys.add(k);
                        return true;
                      });
                      const thoughtContent = latestThinkingStep?.thinkingText || latestThinkingStep?.data?.thinking_text || "";

                      // Deduplicate pipeline log messages:
                      // If structured thinking steps are present, exclude individual thinking_progress updates to avoid duplicating steps
                      const allSteps = msg.steps || [];
                      const distinctSteps = allSteps.filter((st, sidx) => {
                        if (
                          uniqueThinkingSteps.length > 0 &&
                          (st.step === "thinking_progress" || st.isThinking || /đang suy luận/i.test(st.message))
                        ) {
                          return false;
                        }
                        if (sidx === 0) return true;
                        return st.message !== allSteps[sidx - 1]?.message;
                      });

                      return (
                        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
                          {/* Consolidated Thinking Process */}
                          {uniqueThinkingSteps.length > 0 ? (
                            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 4 }}>
                              <div style={{ fontSize: 11.5, fontWeight: 700, color: "var(--brand-blue)" }}>
                                ✦ Các bước suy luận & tìm kiếm ({uniqueThinkingSteps.length}):
                              </div>
                              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                {uniqueThinkingSteps.map((stepItem: any, stIdx: number) => (
                                  <details
                                    key={stIdx}
                                    style={{
                                      fontSize: 11.5,
                                      backgroundColor: "#ffffff",
                                      padding: "6px 10px",
                                      borderRadius: 6,
                                      border: "1px solid #e2e8f0",
                                    }}
                                  >
                                    <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--text-primary)" }}>
                                      <span style={{ color: "#059669", marginRight: 6 }}>✓</span>
                                      <span style={{ color: "var(--brand-blue)" }}>{stepItem.title}</span>
                                      {stepItem.description ? (
                                        <span style={{ color: "var(--text-secondary)", fontWeight: 400, marginLeft: 6 }}>
                                          — {stepItem.description.slice(0, 75)}{stepItem.description.length > 75 ? "..." : ""}
                                        </span>
                                      ) : null}
                                    </summary>
                                    {stepItem.description && (
                                      <div
                                        style={{
                                          marginTop: 6,
                                          whiteSpace: "pre-wrap",
                                          fontFamily: "var(--font-geist-mono, monospace)",
                                          maxHeight: 160,
                                          overflowY: "auto",
                                          lineHeight: 1.5,
                                          fontSize: 11,
                                          color: "var(--text-secondary)",
                                          backgroundColor: "#f8fafc",
                                          padding: "6px 8px",
                                          borderRadius: 4,
                                        }}
                                      >
                                        {stepItem.description}
                                      </div>
                                    )}
                                  </details>
                                ))}
                              </div>
                            </div>
                          ) : (
                            thoughtContent && (
                              <details
                                style={{
                                  fontSize: 11.5,
                                  color: "var(--text-secondary)",
                                  backgroundColor: "#ffffff",
                                  padding: "6px 10px",
                                  borderRadius: 6,
                                  border: "1px solid #e2e8f0",
                                  marginBottom: 4,
                                }}
                              >
                                <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--brand-blue)" }}>
                                  Xem nội dung suy luận chi tiết ({thoughtContent.length} ký tự)
                                </summary>
                                <div
                                  style={{
                                    marginTop: 4,
                                    whiteSpace: "pre-wrap",
                                    fontFamily: "var(--font-geist-mono, monospace)",
                                    maxHeight: 140,
                                    overflowY: "auto",
                                    lineHeight: 1.5,
                                    fontSize: 11,
                                    color: "var(--text-secondary)",
                                    backgroundColor: "#f8fafc",
                                    padding: "6px 8px",
                                    borderRadius: 4,
                                  }}
                                >
                                  {thoughtContent}
                                </div>
                              </details>
                            )
                          )}

                          {/* Pipeline Step Log List (Clean without repeating thinking tree) */}
                          {distinctSteps.length > 0 && (
                            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                              {distinctSteps.map((st, sidx) => (
                                <div
                                  key={sidx}
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8,
                                    fontSize: 12,
                                    color: "var(--text-secondary)",
                                  }}
                                >
                                  <span style={{ color: "#059669", fontWeight: 700 }}>✓</span>
                                  <span style={{ flex: 1 }}>{st.message}</span>
                                  <span style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{st.timestamp}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

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
                        const displayTitle = src.title && src.title !== src.url ? src.title : domain;
                        return (
                          <a
                            key={sIdx}
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="message-source-chip"
                            title={`${src.title || src.url}\n${src.url}`}
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
                      title="Chia sẻ"
                      onClick={() => copyToClipboard(msg.content, msg.id)}
                    >
                      <ShareIcon size={15} />
                    </button>
                    <button className="icon-btn" title="Đánh dấu">
                      <BookmarkIcon size={15} />
                    </button>
                    <button className="icon-btn" title="Tùy chọn khác">
                      <MoreHorizontalIcon size={15} />
                    </button>
                  </div>

                  <span className="card-footer-token">
                    {msg.tokens ? `${msg.tokens} tokens` : ""}
                    {msg.latencySeconds ? ` · ${msg.latencySeconds}s` : ""}
                  </span>
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
                }}
              >
                AI
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

              {/* Real-time Thinking Process & DOM Citations Display */}
              {(() => {
                const latestThinkingStep = [...activeSteps].reverse().find(
                  (s) =>
                    (s.thinkingSteps && s.thinkingSteps.length > 0) ||
                    (s.data?.thinking_steps && s.data.thinking_steps.length > 0) ||
                    s.thinkingText ||
                    s.data?.thinking_text ||
                    s.isThinking ||
                    s.data?.is_thinking
                );
                const rawCurrentSteps = latestThinkingStep?.thinkingSteps || latestThinkingStep?.data?.thinking_steps || [];
                const seenCurrentKeys = new Set<string>();
                const currentThinkingSteps = rawCurrentSteps.filter((step: any) => {
                  const k = `${(step.title || "").trim()}::${(step.description || "").trim()}`;
                  if (seenCurrentKeys.has(k)) return false;
                  seenCurrentKeys.add(k);
                  return true;
                });
                const currentThinkingText = latestThinkingStep?.thinkingText || latestThinkingStep?.data?.thinking_text || "";
                const activeThinkingProvider = latestThinkingStep?.provider || latestThinkingStep?.data?.provider || "";
                const hasThinkingData = currentThinkingSteps.length > 0 || Boolean(currentThinkingText);

                const liveCitationsList: any[] = [];
                const seenCitationUrls = new Set<string>();
                for (const st of activeSteps) {
                  const stepCitations: any[] = st.citations || st.data?.citations || [];
                  for (const c of stepCitations) {
                    if (c && c.url && !seenCitationUrls.has(c.url)) {
                      seenCitationUrls.add(c.url);
                      liveCitationsList.push(c);
                    }
                  }
                }

                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: "4px 0" }}>
                    {/* Live Thinking Process Content Card */}
                    {hasThinkingData && (
                      <div
                        style={{
                          backgroundColor: "#f8fafc",
                          borderRadius: "var(--radius-md)",
                          border: "1.5px solid #93c5fd",
                          padding: "12px 14px",
                          display: "flex",
                          flexDirection: "column",
                          gap: 8,
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            fontSize: 12.5,
                            fontWeight: 700,
                            color: "var(--brand-blue)",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                            <BrainIcon size={16} color="var(--brand-blue)" />
                            <span>
                              Tiến trình suy luận (Thinking Process) — {activeThinkingProvider ? activeThinkingProvider.toUpperCase() : "Live Chatbot"}
                            </span>
                          </div>
                          <span
                            style={{
                              fontSize: 11,
                              color: "#059669",
                              backgroundColor: "#ecfdf5",
                              padding: "2px 8px",
                              borderRadius: 12,
                              border: "1px solid #a7f3d0",
                              display: "flex",
                              alignItems: "center",
                              gap: 4,
                            }}
                          >
                            <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#059669" }} />
                            Live DOM
                          </span>
                        </div>

                        {/* If structured steps are available (e.g. Qwen status cards: Searching web, Reading sources, etc.) */}
                        {currentThinkingSteps.length > 0 ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 2 }}>
                            {currentThinkingSteps.map((stepItem: any, sIdx: number) => {
                              const isStepRunning = stepItem.status === "running";
                              return (
                                <div
                                  key={sIdx}
                                  style={{
                                    backgroundColor: "#ffffff",
                                    borderRadius: 6,
                                    border: isStepRunning ? "1px solid #93c5fd" : "1px solid #e2e8f0",
                                    padding: "8px 12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 4,
                                  }}
                                >
                                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>
                                      {isStepRunning ? (
                                        <div
                                          style={{
                                            width: 10,
                                            height: 10,
                                            border: "2px solid #3b82f6",
                                            borderTopColor: "transparent",
                                            borderRadius: "50%",
                                            animation: "spin 0.8s linear infinite",
                                          }}
                                        />
                                      ) : (
                                        <span style={{ color: "#059669", fontWeight: 700 }}>✓</span>
                                      )}
                                      <span>{stepItem.title}</span>
                                    </div>
                                    <span
                                      style={{
                                        fontSize: 10.5,
                                        padding: "1px 6px",
                                        borderRadius: 10,
                                        backgroundColor: isStepRunning ? "#eff6ff" : "#f0fdf4",
                                        color: isStepRunning ? "#1d4ed8" : "#15803d",
                                        fontWeight: 500,
                                      }}
                                    >
                                      {isStepRunning ? "Đang xử lý..." : "Hoàn thành"}
                                    </span>
                                  </div>
                                  {stepItem.description && (
                                    <div
                                      style={{
                                        fontSize: 11.5,
                                        lineHeight: 1.5,
                                        color: "var(--text-secondary)",
                                        backgroundColor: "#f8fafc",
                                        padding: "6px 8px",
                                        borderRadius: 4,
                                        whiteSpace: "pre-wrap",
                                        fontFamily: "var(--font-geist-mono, monospace)",
                                        maxHeight: 140,
                                        overflowY: "auto",
                                      }}
                                    >
                                      {stepItem.description}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          currentThinkingText && (
                            <div
                              style={{
                                fontSize: 12,
                                lineHeight: 1.6,
                                color: "var(--text-secondary)",
                                backgroundColor: "#ffffff",
                                padding: "10px 12px",
                                borderRadius: 6,
                                border: "1px solid #e2e8f0",
                                maxHeight: 160,
                                overflowY: "auto",
                                whiteSpace: "pre-wrap",
                                fontFamily: "var(--font-geist-mono, monospace)",
                              }}
                            >
                              {currentThinkingText}
                            </div>
                          )
                        )}

                        {liveCitationsList.length > 0 && (
                          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 2 }}>
                            <div style={{ fontSize: 11.5, fontWeight: 600, color: "var(--text-primary)" }}>
                              ✦ Nguồn trích dẫn tìm thấy từ DOM ({liveCitationsList.length}):
                            </div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                              {liveCitationsList.map((c, cIdx) => (
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
                      </div>
                    )}

                    {/* Dynamic Step Logs Feed */}
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {(() => {
                        const distinctActive = activeSteps.filter((st, i) => {
                          if (
                            currentThinkingSteps.length > 0 &&
                            (st.step === "thinking_progress" || st.isThinking || /đang suy luận/i.test(st.message))
                          ) {
                            return false;
                          }
                          if (i === 0) return true;
                          return st.message !== activeSteps[i - 1].message;
                        });
                        return distinctActive.length > 0 ? (
                          distinctActive.map((st, idx) => {
                            const isLatest = idx === distinctActive.length - 1;
                            return (
                              <div
                                key={idx}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 10,
                                  fontSize: 12.5,
                                  color: isLatest ? "var(--text-primary)" : "var(--text-secondary)",
                                  fontWeight: isLatest ? 600 : 400,
                                  padding: "4px 8px",
                                  borderRadius: 6,
                                  backgroundColor: isLatest ? "var(--brand-blue-light)" : "transparent",
                                }}
                              >
                                {isLatest ? (
                                  <div
                                    style={{
                                      width: 12,
                                      height: 12,
                                      border: "2px solid #3b82f6",
                                      borderTopColor: "transparent",
                                      borderRadius: "50%",
                                      animation: "spin 0.8s linear infinite",
                                    }}
                                  />
                                ) : (
                                  <span style={{ color: "#059669", fontWeight: 700 }}>✓</span>
                                )}
                                <span style={{ flex: 1 }}>{st.message}</span>
                                <span style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{st.timestamp}</span>
                              </div>
                            );
                          })
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
                        );
                      })()}
                    </div>
                  </div>
                );
              })()}
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
              <button
                className="icon-btn"
                title="Multi-Provider Matrix"
                onClick={onOpenProvidersModal}
                aria-label="Multi-Provider Matrix"
              >
                <GridIcon size={17} />
              </button>
            </div>

            <button
              className="btn-composer-send"
              onClick={handleSend}
              disabled={!inputText.trim() || isGenerating}
            >
              <SendIcon size={14} />
              <span>Gửi câu hỏi</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
