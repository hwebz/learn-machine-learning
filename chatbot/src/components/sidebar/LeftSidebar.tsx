"use client";

import React, { useState, useRef, useEffect } from "react";
import { ChatSession } from "../../types/chat";
import {
  SearchIcon,
  ChatIcon,
  LibraryIcon,
  AppsIcon,
  SettingsIcon,
  PlusIcon,
  RefreshIcon,
  PinIcon,
  EditIcon,
  TrashIcon,
  CheckIcon,
  CloseIcon,
  ExternalLinkIcon,
} from "../icons/Icons";

interface LeftSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onNewAgent: () => void;
  onOpenProvidersModal: () => void;
  onOpenJobsModal: () => void;
  onOpenSettingsModal?: () => void;
  onRefreshHistory?: () => void;
  isLoadingHistory?: boolean;
  onTogglePin: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
}

function getSessionProviderConversations(session: ChatSession): { provider: string; role?: string; url: string }[] {
  const result: { provider: string; role?: string; url: string }[] = [];
  const seenUrls = new Set<string>();

  const add = (prov: string, url?: string | null, role?: string) => {
    if (url && typeof url === "string" && url.startsWith("http") && !seenUrls.has(url)) {
      seenUrls.add(url);
      result.push({ provider: prov, role, url });
    }
  };

  if (session.orchestrator_conversation_url) {
    add(session.orchestrator_provider || "Orchestrator", session.orchestrator_conversation_url, "Master Orchestrator");
  }
  if (session.lead_conversation_url) {
    add(session.lead_provider || "Lead", session.lead_conversation_url, "Lead Synthesizer");
  }
  if (session.provider_conversations) {
    for (const [p, u] of Object.entries(session.provider_conversations)) {
      add(p, u, "Nhà cung cấp");
    }
  }

  for (const msg of session.messages || []) {
    if (msg.orchestrator_conversation_url) {
      add(msg.orchestrator_provider || "Orchestrator", msg.orchestrator_conversation_url, "Master Orchestrator");
    }
    if (msg.lead_conversation_url) {
      add(msg.lead_provider || "Lead", msg.lead_conversation_url, "Lead Synthesizer");
    }
    if (msg.provider_conversations) {
      for (const [p, u] of Object.entries(msg.provider_conversations)) {
        add(p, u, "Nhà cung cấp");
      }
    }
    if (msg.provider_runs) {
      const runs = Array.isArray(msg.provider_runs) ? msg.provider_runs : Object.values(msg.provider_runs);
      for (const r of runs) {
        if (r?.conversation_url) {
          add(r.provider || "Nhà cung cấp", r.conversation_url, r.role || "Tác nhân");
        }
      }
    }
    if (msg.steps) {
      for (const st of msg.steps) {
        const url = st.conversationUrl || (st.data as any)?.conversation_url;
        if (url) {
          add(st.provider || (st.data as any)?.provider || "Nhà cung cấp", url);
        }
      }
    }
  }

  return result;
}

export function LeftSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onNewAgent,
  onOpenProvidersModal,
  onOpenJobsModal,
  onOpenSettingsModal,
  onRefreshHistory,
  isLoadingHistory = false,
  onTogglePin,
  onRenameSession,
  onDeleteSession,
}: LeftSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNav, setActiveNav] = useState<"chats" | "library" | "apps">("chats");
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [confirmDeleteSession, setConfirmDeleteSession] = useState<ChatSession | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingSessionId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingSessionId]);

  const handleStartRename = (session: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditingTitle(session.title);
  };

  const handleSaveRename = (id: string, e?: React.MouseEvent | React.KeyboardEvent) => {
    if (e) e.stopPropagation();
    if (editingTitle.trim()) {
      onRenameSession(id, editingTitle.trim());
    }
    setEditingSessionId(null);
  };

  const handleCancelRename = (e?: React.MouseEvent | React.KeyboardEvent) => {
    if (e) e.stopPropagation();
    setEditingSessionId(null);
  };

  const handleKeyDown = (id: string, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSaveRename(id, e);
    } else if (e.key === "Escape") {
      handleCancelRename(e);
    }
  };

  const filteredSessions = sessions
    .filter((s) => s.messages && s.messages.length > 0)
    .filter((s) => s.title.toLowerCase().includes(searchQuery.toLowerCase()));

  // Grouping logic: Today, Yesterday, 7 days ago
  const getSessionTimeGroup = (session: ChatSession): "today" | "yesterday" | "last7days" => {
    let ts = session.createdTimestamp;
    if (!ts && session.createdAt) {
      const parsed = Date.parse(session.createdAt);
      if (!isNaN(parsed)) {
        ts = parsed;
      }
    }

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfYesterday = startOfToday - 86400000;

    if (ts) {
      if (ts >= startOfToday) return "today";
      if (ts >= startOfYesterday) return "yesterday";
      return "last7days";
    }

    const lower = (session.createdAt || "").toLowerCase();
    if (lower.includes("hôm nay") || lower.includes("today") || lower.includes("vừa xong") || lower.includes("just now")) {
      return "today";
    }
    if (lower.includes("hôm qua") || lower.includes("yesterday")) {
      return "yesterday";
    }
    return "last7days";
  };

  const pinnedSessions = filteredSessions.filter((s) => s.pinned);
  const unpinnedSessions = filteredSessions.filter((s) => !s.pinned);

  const todaySessions = unpinnedSessions.filter((s) => getSessionTimeGroup(s) === "today");
  const yesterdaySessions = unpinnedSessions.filter((s) => getSessionTimeGroup(s) === "yesterday");
  const last7DaysSessions = unpinnedSessions.filter((s) => getSessionTimeGroup(s) === "last7days");

  const renderSessionItem = (session: ChatSession) => {
    const isActive = session.id === activeSessionId;
    const isEditing = editingSessionId === session.id;
    const providerCount = session.selectedProviders?.length || 1;
    const isRunning =
      session.status === "running" ||
      session.status === "queued" ||
      session.status === "orchestrating" ||
      session.status === "researching" ||
      session.status === "leading";

    if (isEditing) {
      return (
        <div
          key={session.id}
          className="sidebar-chat-item-editing"
          onClick={(e) => e.stopPropagation()}
        >
          <input
            ref={inputRef}
            type="text"
            className="sidebar-inline-edit-input"
            value={editingTitle}
            onChange={(e) => setEditingTitle(e.target.value)}
            onKeyDown={(e) => handleKeyDown(session.id, e)}
          />
          <div style={{ display: "flex", gap: 3 }}>
            <button
              className="action-icon-btn"
              onClick={(e) => handleSaveRename(session.id, e)}
              title="Lưu (Enter)"
            >
              <CheckIcon size={13} color="#059669" />
            </button>
            <button
              className="action-icon-btn"
              onClick={(e) => handleCancelRename(e)}
              title="Hủy (Esc)"
            >
              <CloseIcon size={13} color="#ef4444" />
            </button>
          </div>
        </div>
      );
    }

    return (
      <div
        key={session.id}
        className={`sidebar-chat-item-row ${isActive ? "active" : ""}`}
        onClick={() => onSelectSession(session.id)}
        title={session.title}
      >
        <div className="sidebar-chat-item-left">
          {isRunning ? (
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                backgroundColor: "var(--brand-blue)",
                boxShadow: "0 0 6px var(--brand-blue)",
                flexShrink: 0,
              }}
              title="Đang nghiên cứu..."
            />
          ) : session.pinned ? (
            <PinIcon size={12} color="var(--brand-blue)" filled={true} />
          ) : session.status === "cancelled" ? (
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "#94a3b8",
                flexShrink: 0,
              }}
              title="Đã dừng nghiên cứu"
            />
          ) : session.status === "failed" ? (
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "#ef4444",
                flexShrink: 0,
              }}
              title="Nghiên cứu thất bại"
            />
          ) : null}
          {session.job_type === "agent" && (
            <span
              style={{
                fontSize: 9.5,
                fontWeight: 700,
                color: "#8b5cf6",
                background: "rgba(139, 92, 246, 0.15)",
                padding: "1px 5px",
                borderRadius: 4,
                flexShrink: 0,
                display: "inline-flex",
                alignItems: "center",
                gap: 2,
              }}
              title={`Deep Research Agent (Tone: ${session.tone || 'standard'})`}
            >
              🤖 Agent
            </span>
          )}
          <span className="sidebar-chat-title">{session.title}</span>
        </div>

        {/* Action icons appear on hover */}
        <div className="sidebar-chat-item-actions">
          <button
            type="button"
            className={`action-icon-btn ${session.pinned ? "active-pin" : ""}`}
            onClick={(e) => {
              e.stopPropagation();
              onTogglePin(session.id);
            }}
            title={session.pinned ? "Bỏ ghim (Unpin)" : "Ghim lên đầu (Pin)"}
          >
            <PinIcon size={13} color={session.pinned ? "var(--brand-blue)" : "currentColor"} filled={session.pinned} />
          </button>

          <button
            type="button"
            className="action-icon-btn"
            onClick={(e) => handleStartRename(session, e)}
            title="Đổi tên (Rename)"
          >
            <EditIcon size={13} />
          </button>

          <button
            type="button"
            className="action-icon-btn delete-btn"
            onClick={(e) => {
              e.stopPropagation();
              setConfirmDeleteSession(session);
            }}
            title="Xóa phiên (Delete)"
          >
            <TrashIcon size={13} />
          </button>
        </div>

        {/* Model badge */}
        <span className="sidebar-model-badge">
          {providerCount}M
        </span>
      </div>
    );
  };

  return (
    <aside className="left-sidebar">
      {/* User Profile Bar */}
      <div className="user-profile-bar">
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "linear-gradient(135deg, var(--brand-blue) 0%, #7c3aed 100%)",
            color: "#ffffff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 12.5,
            boxShadow: "var(--shadow-xs)",
            flexShrink: 0,
          }}
        >
          AR
        </div>
        <div className="user-info">
          <span className="user-name">AI Researcher</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Multi-Provider Hub</span>
        </div>
        <div className="user-actions">
          <button
            className="icon-btn"
            title="Cài đặt hệ thống (Settings)"
            onClick={onOpenSettingsModal || onOpenProvidersModal}
            aria-label="Settings"
          >
            <SettingsIcon size={16} />
          </button>
          <button
            className="icon-btn"
            title="Đồng bộ lịch sử từ Backend"
            onClick={onRefreshHistory}
            aria-label="Refresh History"
          >
            <span style={{ display: "inline-flex", animation: isLoadingHistory ? "spin 1s linear infinite" : "none" }}>
              <RefreshIcon size={15} />
            </span>
          </button>
        </div>
      </div>

      {/* Search Input */}
      <div className="search-box-wrapper">
        <div className="search-box">
          <SearchIcon size={15} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Tìm kiếm lịch sử chat..."
            className="search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="nav-menu">
        <button
          className="nav-item"
          onClick={() => {
            setActiveNav("chats");
            onNewChat();
          }}
          title="Tạo phiên nghiên cứu mới (New Chat)"
        >
          <PlusIcon size={16} />
          <span>New Chat</span>
        </button>

        <button
          className="nav-item nav-agent-item"
          onClick={() => {
            setActiveNav("chats");
            onNewAgent();
          }}
          title="Khởi chạy tác nhân điều phối đa mô hình (Deep Research Orchestrator)"
          style={{
            background: "linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.12) 100%)",
            border: "1px solid rgba(139, 92, 246, 0.3)",
            color: "#a855f7",
            fontWeight: 600,
          }}
        >
          <span style={{ fontSize: 16 }}>🤖</span>
          <span style={{
            background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            fontWeight: 700,
          }}>
            New Agent
          </span>
          <span style={{
            fontSize: 9,
            marginLeft: "auto",
            padding: "1px 5px",
            borderRadius: 4,
            background: "rgba(139, 92, 246, 0.18)",
            color: "#8b5cf6",
            fontWeight: 700,
          }}>
            AUTO
          </span>
        </button>

        <button
          className={`nav-item ${activeNav === "library" ? "active" : ""}`}
          onClick={() => {
            setActiveNav("library");
            onOpenProvidersModal();
          }}
        >
          <LibraryIcon size={16} />
          <span>Library</span>
        </button>

        <button
          className={`nav-item ${activeNav === "apps" ? "active" : ""}`}
          onClick={() => {
            setActiveNav("apps");
            onOpenJobsModal();
          }}
        >
          <AppsIcon size={16} />
          <span>Live Jobs</span>
        </button>
      </nav>

      {/* Grouped Chat History List */}
      <div className="sidebar-scroll-area">
        {/* 1. PINNED SESSIONS */}
        {pinnedSessions.length > 0 && (
          <div className="sidebar-chat-list">
            <div className="sidebar-section-title">
              <span>PINNED</span>
              <span className="section-count-badge">{pinnedSessions.length}</span>
            </div>
            {pinnedSessions.map((s) => renderSessionItem(s))}
          </div>
        )}

        {/* 2. TODAY GROUP */}
        {todaySessions.length > 0 && (
          <div className="sidebar-chat-list">
            <div className="sidebar-section-title">
              <span>TODAY</span>
              <span className="section-count-badge">{todaySessions.length}</span>
            </div>
            {todaySessions.map((s) => renderSessionItem(s))}
          </div>
        )}

        {/* 3. YESTERDAY GROUP */}
        {yesterdaySessions.length > 0 && (
          <div className="sidebar-chat-list">
            <div className="sidebar-section-title">
              <span>YESTERDAY</span>
              <span className="section-count-badge">{yesterdaySessions.length}</span>
            </div>
            {yesterdaySessions.map((s) => renderSessionItem(s))}
          </div>
        )}

        {/* 4. 7 DAYS AGO GROUP */}
        {last7DaysSessions.length > 0 && (
          <div className="sidebar-chat-list">
            <div className="sidebar-section-title">
              <span>7 DAYS AGO</span>
              <span className="section-count-badge">{last7DaysSessions.length}</span>
            </div>
            {last7DaysSessions.map((s) => renderSessionItem(s))}
          </div>
        )}

        {/* Empty state when no sessions match */}
        {filteredSessions.length === 0 && (
          <div style={{ fontSize: "12px", color: "var(--text-muted)", padding: "16px 12px", textAlign: "center" }}>
            Không tìm thấy phiên chat nào
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal Dialog */}
      {confirmDeleteSession && (
        <div className="modal-backdrop" onClick={() => setConfirmDeleteSession(null)}>
          <div
            className="modal-dialog"
            style={{ maxWidth: 420 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    backgroundColor: "#fee2e2",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#dc2626",
                    flexShrink: 0,
                  }}
                >
                  <TrashIcon size={16} color="#dc2626" />
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                  Xóa cuộc trò chuyện?
                </h3>
              </div>
              <button className="icon-btn" onClick={() => setConfirmDeleteSession(null)} aria-label="Đóng">
                ✕
              </button>
            </div>

            <div className="modal-body" style={{ padding: "16px 24px" }}>
              <p style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
                Bạn có chắc chắn muốn xóa cuộc trò chuyện <strong>"{confirmDeleteSession.title}"</strong> không? Phiên nghiên cứu này sẽ bị xóa khỏi lịch sử cả trên ứng dụng và backend.
              </p>

              {(() => {
                const relatedChats = getSessionProviderConversations(confirmDeleteSession);
                if (relatedChats.length === 0) return null;
                return (
                  <div
                    style={{
                      marginTop: 14,
                      padding: "10px 12px",
                      background: "var(--bg-surface)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-md)",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: "var(--text-primary)",
                        marginBottom: 6,
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <ExternalLinkIcon size={13} color="var(--brand-blue)" />
                      <span>{relatedChats.length} phiên chat liên quan trên nhà cung cấp sẽ tự động bị xóa:</span>
                    </div>
                    <ul
                      style={{
                        margin: 0,
                        paddingLeft: 16,
                        fontSize: 11.5,
                        color: "var(--text-secondary)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                      }}
                    >
                      {relatedChats.map((c, idx) => (
                        <li key={idx}>
                          <strong style={{ textTransform: "capitalize", color: "var(--text-primary)" }}>
                            {c.provider}
                          </strong>
                          {c.role ? ` (${c.role})` : ""}:{" "}
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: "var(--brand-blue)",
                              textDecoration: "underline",
                              wordBreak: "break-all",
                            }}
                          >
                            {c.url}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })()}
            </div>

            <div
              style={{
                padding: "14px 24px 18px 24px",
                display: "flex",
                justifyContent: "flex-end",
                gap: 10,
                borderTop: "1px solid var(--border-subtle)",
              }}
            >
              <button
                type="button"
                className="btn-new-chat-outline"
                onClick={() => setConfirmDeleteSession(null)}
                style={{ padding: "7px 14px", fontSize: 13 }}
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={() => {
                  onDeleteSession(confirmDeleteSession.id);
                  setConfirmDeleteSession(null);
                }}
                style={{
                  backgroundColor: "#dc2626",
                  color: "#ffffff",
                  padding: "7px 16px",
                  borderRadius: "var(--radius-md)",
                  fontSize: 13,
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  boxShadow: "0 2px 6px rgba(220, 38, 38, 0.25)",
                }}
              >
                <TrashIcon size={14} color="#ffffff" />
                <span>Xác nhận xóa</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
