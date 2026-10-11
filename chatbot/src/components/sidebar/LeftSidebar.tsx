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
} from "../icons/Icons";

interface LeftSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onOpenProvidersModal: () => void;
  onOpenJobsModal: () => void;
  onRefreshHistory?: () => void;
  isLoadingHistory?: boolean;
  onTogglePin: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
}

export function LeftSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onOpenProvidersModal,
  onOpenJobsModal,
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

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
    const isRunning = session.status === "running" || session.status === "queued";

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
            />
          ) : session.pinned ? (
            <PinIcon size={12} color="var(--brand-blue)" filled={true} />
          ) : null}
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
            title="AI Model Library"
            onClick={onOpenProvidersModal}
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
            <div style={{ animation: isLoadingHistory ? "spin 1s linear infinite" : "none" }}>
              <RefreshIcon size={15} />
            </div>
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
          <span className="shortcut-kbd">⌘ K</span>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="nav-menu">
        <button
          className={`nav-item ${activeNav === "chats" ? "active" : ""}`}
          onClick={() => setActiveNav("chats")}
        >
          <ChatIcon size={16} />
          <span>Chats ({sessions.length})</span>
          <span className="nav-item-kbd">⌘ 1</span>
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
          <span className="nav-item-kbd">⌘ 2</span>
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
          <span className="nav-item-kbd">⌘ 3</span>
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

      {/* Bottom Start New Chat Button */}
      <div className="sidebar-bottom">
        <button className="btn-start-chat" onClick={onNewChat}>
          <PlusIcon size={16} />
          <span>Bắt đầu phiên nghiên cứu mới</span>
        </button>
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
