"use client";

import React, { useState } from "react";
import { Message, ProviderInfo, StepLog } from "../../types/chat";
import {
  ModelBadgeLogo,
  CheckCircleIcon,
  ExternalLinkIcon,
  ChevronRightIcon,
  BrainIcon,
} from "../icons/Icons";

interface RightSidebarProps {
  selectedProvider: ProviderInfo;
  selectedProviders?: ProviderInfo[];
  currentMessage?: Message;
  currentQuery?: string;
  isGenerating?: boolean;
  activeSteps?: StepLog[];
}

export function RightSidebar({
  selectedProvider,
  selectedProviders = [],
  currentMessage,
  currentQuery = "",
  isGenerating = false,
  activeSteps = [],
}: RightSidebarProps) {
  const [showFactCheckModal, setShowFactCheckModal] = useState(false);

  const sources = currentMessage?.sources || [];
  const claims = currentMessage?.claims || [];

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

  return (
    <aside className="right-sidebar">
      {/* Model Showcase Header */}
      <div className="model-header-showcase">
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
        )}

        <h2 className="model-title-text">
          {displayProviders.length > 1
            ? `${displayProviders.length} Models Selected`
            : selectedProvider.modelName}
        </h2>
        <p className="model-desc-text">
          {displayProviders.length > 1
            ? displayProviders.map((p) => p.name).join(" • ")
            : selectedProvider.shortDesc}
        </p>

        {/* Model Specs Grid */}
        <div className="model-specs-grid">
          <div className="spec-item">
            <span className="spec-label">Reasoning Mode</span>
            <span className="spec-value" style={{ color: "var(--brand-blue)", fontWeight: 700 }}>
              {displayProviders.some((p) => p.supportsDeepMode) ? "Deep Thinking" : "Standard"}
            </span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Active Models</span>
            <span className="spec-value">{displayProviders.length} Engines</span>
          </div>
        </div>
      </div>

      {/* Real-time Status / Execution Steps Pills */}
      <div className="status-pills-list">
        {currentQuery && (
          <div className="status-pill-green">
            <CheckCircleIcon size={16} color="#059669" />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              Query: <strong>{currentQuery.slice(0, 32)}</strong>
            </span>
          </div>
        )}

        {isGenerating ? (
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
              {activeSteps[activeSteps.length - 1]?.message || "Đang tổng hợp câu trả lời từ các model..."}
            </span>
          </div>
        ) : (
          <div className="status-pill-green">
            <CheckCircleIcon size={16} color="#059669" />
            <span>Sẵn sàng nghiên cứu đa mô hình</span>
          </div>
        )}

        {/* Dynamic Step Logs if available */}
        {activeSteps.length > 0 && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
              padding: "8px 10px",
              backgroundColor: "var(--bg-app)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
              maxHeight: 140,
              overflowY: "auto",
            }}
          >
            <span style={{ fontSize: 10.5, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
              Live Trace Logs ({activeSteps.length})
            </span>
            {activeSteps.map((s, idx) => (
              <div key={idx} style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 6, alignItems: "flex-start" }}>
                <span style={{ color: "var(--brand-blue)", fontWeight: 700 }}>•</span>
                <span style={{ flex: 1 }}>{s.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Citations & Sources Card */}
      <div className="sources-card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
            Nguồn trích dẫn ({sources.length})
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

      {/* Fact Check History Footer Link */}
      <button
        className="fact-check-footer-link"
        onClick={() => setShowFactCheckModal(true)}
      >
        <span>Chi tiết đối chiếu Fact Check</span>
        <ChevronRightIcon size={16} />
      </button>

      {/* Fact Check Details Modal */}
      {showFactCheckModal && (
        <div className="modal-backdrop" onClick={() => setShowFactCheckModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Fact Check & Claims Verification</h3>
              <button className="icon-btn" onClick={() => setShowFactCheckModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                Các khẳng định dưới đây được trích xuất từ dữ liệu đa mô hình và xác minh chéo qua công cụ đồng thuận:
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {claims.length > 0 ? (
                  claims.map((c: any, idx: number) => (
                    <div
                      key={idx}
                      style={{
                        padding: 12,
                        borderRadius: 8,
                        backgroundColor: c.verdict === "disputed" ? "#fef2f2" : "var(--accent-success-bg)",
                        border: `1px solid ${c.verdict === "disputed" ? "#fecaca" : "var(--accent-success-border)"}`,
                        fontSize: 13,
                      }}
                    >
                      <strong style={{ color: c.verdict === "disputed" ? "#991b1b" : "#065f46" }}>
                        {c.verdict === "disputed" ? "⚠ Disputed: " : "✓ Verified: "}
                      </strong>
                      <span>{c.claim || JSON.stringify(c)}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: 16, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
                    Chưa có khẳng định nào cần kiểm chứng cho câu hỏi này.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
