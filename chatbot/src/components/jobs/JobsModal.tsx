"use client";

import React, { useState, useEffect } from "react";
import { checkBackendHealth } from "../../lib/api";

interface JobsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function JobsModal({ isOpen, onClose }: JobsModalProps) {
  const [backendHealth, setBackendHealth] = useState<any>(null);

  useEffect(() => {
    if (isOpen) {
      checkBackendHealth().then((res) => {
        if (res.online) setBackendHealth(res.data);
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>
              Live Research Jobs & Agent Orchestrator
            </h2>
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 2 }}>
              Inspect background browser tasks, SSE event feeds, and consensus synthesis
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        <div className="modal-body">
          {backendHealth ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div
                style={{
                  padding: 14,
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-app)",
                  border: "1px solid var(--border-default)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600 }}>
                  <span>Worker Pipeline:</span>
                  <span style={{ color: backendHealth.worker_running ? "#059669" : "#dc2626" }}>
                    {backendHealth.worker_running ? "● Active & Polling" : "● Stopped"}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "var(--text-secondary)" }}>
                  <span>Adapter Execution Mode:</span>
                  <span style={{ fontWeight: 600, color: "var(--brand-blue)" }}>
                    {backendHealth.adapter_mode?.toUpperCase() || "UI_BROWSER"}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "var(--text-secondary)" }}>
                  <span>Router Reachable:</span>
                  <span>{backendHealth.router_reachable ? "Yes" : "No"}</span>
                </div>
              </div>

              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase" }}>
                  Registered UI Adapters Health
                </h3>
                <div
                  style={{
                    maxHeight: 240,
                    overflowY: "auto",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                  }}
                >
                  {backendHealth.adapters &&
                    Object.entries(backendHealth.adapters).map(([name, info]: any) => (
                      <div
                        key={name}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "8px 12px",
                          borderRadius: 8,
                          backgroundColor: "#ffffff",
                          border: "1px solid #e2e8f0",
                          fontSize: 12.5,
                        }}
                      >
                        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{name}</span>
                        <span
                          style={{
                            fontSize: 11,
                            padding: "2px 8px",
                            borderRadius: 4,
                            backgroundColor: info.ui?.selectors_ok ? "var(--accent-success-bg)" : "#fef2f2",
                            color: info.ui?.selectors_ok ? "#065f46" : "#b91c1c",
                            border: `1px solid ${info.ui?.selectors_ok ? "var(--accent-success-border)" : "#fecaca"}`,
                          }}
                        >
                          {info.ui?.selectors_ok ? "Selectors Ready" : "Unverified"}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: "20px 0", textAlign: "center", color: "var(--text-secondary)" }}>
              <p style={{ fontSize: 13.5 }}>Backend API server is not running on port 8000.</p>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                To start the real-time research engine, run <code>.\StartServer.ps1</code> in <code>pc_chatbots</code>.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
