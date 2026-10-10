"use client";

import React, { useState } from "react";
import { ChatSession } from "../../types/chat";
import {
  SearchIcon,
  ChatIcon,
  LibraryIcon,
  AppsIcon,
  SettingsIcon,
  SidebarCollapseIcon,
  PlusIcon,
  RefreshIcon,
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
}: LeftSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNav, setActiveNav] = useState<"chats" | "library" | "apps">("chats");

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pinnedSessions = filteredSessions.filter((s) => s.pinned);
  const historySessions = filteredSessions.filter((s) => !s.pinned);

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

      {/* Pinned & Chat History List */}
      <div className="sidebar-scroll-area">
        {pinnedSessions.length > 0 && (
          <div className="sidebar-chat-list">
            <div className="sidebar-section-title">GHIM / TIÊU BIỂU</div>
            {pinnedSessions.map((session) => {
              const isActive = session.id === activeSessionId;
              const providerCount = session.selectedProviders?.length || 1;

              return (
                <button
                  key={session.id}
                  className={`sidebar-chat-item ${isActive ? "active" : ""}`}
                  onClick={() => onSelectSession(session.id)}
                  title={session.title}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {session.title}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: isActive ? "var(--brand-blue)" : "var(--text-muted)",
                      backgroundColor: isActive ? "#ffffff" : "#f1f5f9",
                      padding: "1px 5px",
                      borderRadius: 4,
                      flexShrink: 0,
                    }}
                  >
                    {providerCount}M
                  </span>
                </button>
              );
            })}
          </div>
        )}

        <div className="sidebar-chat-list">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              paddingRight: 8,
            }}
          >
            <div className="sidebar-section-title">LỊCH SỬ PHIÊN NGHIÊN CỨU</div>
            {isLoadingHistory && (
              <span style={{ fontSize: 10, color: "var(--brand-blue)" }}>Đang tải...</span>
            )}
          </div>

          {historySessions.map((session) => {
            const isActive = session.id === activeSessionId;
            const providerCount = session.selectedProviders?.length || 1;
            const isRunning = session.status === "running" || session.status === "queued";

            return (
              <button
                key={session.id}
                className={`sidebar-chat-item ${isActive ? "active" : ""}`}
                onClick={() => onSelectSession(session.id)}
                title={session.title}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                  {isRunning && (
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        backgroundColor: "var(--brand-blue)",
                        boxShadow: "0 0 6px var(--brand-blue)",
                        flexShrink: 0,
                      }}
                    />
                  )}
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {session.title}
                  </span>
                </div>

                <span
                  style={{
                    fontSize: 10,
                    color: isActive ? "var(--brand-blue)" : "var(--text-muted)",
                    backgroundColor: isActive ? "#ffffff" : "#f1f5f9",
                    padding: "1px 5px",
                    borderRadius: 4,
                    flexShrink: 0,
                  }}
                >
                  {providerCount}M
                </span>
              </button>
            );
          })}

          {historySessions.length === 0 && (
            <div style={{ fontSize: "12px", color: "var(--text-muted)", padding: "8px 12px", textAlign: "center" }}>
              Chưa có phiên chat nào
            </div>
          )}
        </div>
      </div>

      {/* Bottom Start New Chat Button */}
      <div className="sidebar-bottom">
        <button className="btn-start-chat" onClick={onNewChat}>
          <PlusIcon size={16} />
          <span>Bắt đầu phiên nghiên cứu mới</span>
        </button>
      </div>
    </aside>
  );
}
