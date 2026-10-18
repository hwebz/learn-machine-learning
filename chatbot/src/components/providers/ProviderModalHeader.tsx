"use client";

import React from "react";

interface ProviderModalHeaderProps {
  onClose: () => void;
  backendStatus: { online: boolean; data?: any };
  loadingHealth: boolean;
}

export function ProviderModalHeader({
  onClose,
  backendStatus,
  loadingHealth,
}: ProviderModalHeaderProps) {
  return (
    <>
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

      {/* Backend Status Alert */}
      <div
        style={{
          padding: '15px 25px 0'
        }}
      >
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
            marginBottom: 10,
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
      </div>
    </>
  );
}
