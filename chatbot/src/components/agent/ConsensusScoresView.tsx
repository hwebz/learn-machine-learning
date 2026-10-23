"use client";

import React, { useState } from "react";
import { ConsensusScoreResult } from "../../types/chat";
import { CopyIcon, CheckIcon, ChevronDownIcon, ChevronRightIcon, BrainIcon } from "../icons/Icons";

export interface ConsensusScoresViewProps {
  consensus?: ConsensusScoreResult;
  compact?: boolean;
  defaultExpanded?: boolean;
}

export const ConsensusScoresView: React.FC<ConsensusScoresViewProps> = ({
  consensus,
  compact = false,
  defaultExpanded = true,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [expandedTheses, setExpandedTheses] = useState<Record<string, boolean>>({});

  if (!consensus || !consensus.theses || consensus.theses.length === 0) {
    return null;
  }

  const { theses, rounds = [], converged = false, final_scores = [] } = consensus;

  const toggleThesis = (tid: string) => {
    setExpandedTheses((prev) => ({ ...prev, [tid]: !prev[tid] }));
  };

  const copySummary = () => {
    const lines = [
      `=== BÁO CÁO HỘI TỤ DELPHI CONSENSUS ===`,
      `Trạng thái: ${converged ? "ĐÃ HỘI TỤ (Tỉ lệ đồng thuận cao)" : "CHƯA HỘI TỤ (Quan điểm phân kỳ)"}`,
      `Số vòng đánh giá: ${rounds.length}`,
      `Số luận điểm thẩm định: ${theses.length}`,
      "",
      "--- CÁC LUẬN ĐIỂM & ĐIỂM SỐ ĐỒNG THUẬN ---",
    ];

    for (const t of theses) {
      const sc = final_scores.find((s) => s.id === t.id) || { mean: 0, stdev: 0, n: 0 };
      lines.push(
        `[${t.id}] (${t.category || "General"}) Điểm: ${sc.mean}/5.0 (StdDev: ${sc.stdev}, Đánh giá: ${sc.n})`
      );
      lines.push(`Luận điểm: ${t.thesis}`);
      if (t.supporting_evidence) {
        lines.push(`Cơ sở: ${t.supporting_evidence}`);
      }
      lines.push("");
    }

    navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getScoreColor = (mean: number) => {
    if (mean >= 4.0) return "#10b981"; // Emerald
    if (mean >= 3.0) return "#f59e0b"; // Amber
    return "#f43f5e"; // Rose
  };

  const getCategoryColor = (cat?: string) => {
    const c = (cat || "").toLowerCase();
    if (c.includes("tech")) return { bg: "rgba(59, 130, 246, 0.15)", text: "#60a5fa", border: "rgba(59, 130, 246, 0.3)" };
    if (c.includes("econ")) return { bg: "rgba(16, 185, 129, 0.15)", text: "#34d399", border: "rgba(16, 185, 129, 0.3)" };
    if (c.includes("risk")) return { bg: "rgba(244, 63, 94, 0.15)", text: "#fb7185", border: "rgba(244, 63, 94, 0.3)" };
    return { bg: "rgba(168, 85, 247, 0.15)", text: "#c084fc", border: "rgba(168, 85, 247, 0.3)" };
  };

  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid rgba(255, 255, 255, 0.1)",
        background: compact
          ? "rgba(15, 23, 42, 0.7)"
          : "linear-gradient(180deg, rgba(15, 23, 42, 0.85) 0%, rgba(10, 15, 30, 0.95) 100%)",
        backdropFilter: "blur(12px)",
        padding: compact ? "12px 14px" : "16px 20px",
        boxShadow: "0 8px 24px -4px rgba(0, 0, 0, 0.35)",
        color: "#e2e8f0",
      }}
    >
      {/* Header Row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
          borderBottom: isExpanded ? "1px solid rgba(255, 255, 255, 0.08)" : "none",
          paddingBottom: isExpanded ? 12 : 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(59, 130, 246, 0.2))",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
            }}
          >
            📊
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "#f8fafc" }}>
                Đánh giá Hội tụ Delphi Consensus
              </span>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: 20,
                  background: converged ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)",
                  color: converged ? "#34d399" : "#fbbf24",
                  border: `1px solid ${converged ? "rgba(16, 185, 129, 0.3)" : "rgba(245, 158, 11, 0.3)"}`,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                {converged ? "✓ Đã hội tụ" : "⚠️ Chưa hội tụ hoàn toàn"}
              </span>
            </div>
            <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
              {rounds.length} vòng lặp Delphi • {theses.length} luận điểm thẩm định độc lập
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            onClick={copySummary}
            style={{
              background: "rgba(30, 41, 59, 0.8)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: 6,
              padding: "4px 10px",
              fontSize: 11,
              fontWeight: 500,
              color: "#cbd5e1",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
            }}
            title="Sao chép kết quả đồng thuận Delphi"
          >
            {copied ? <CheckIcon size={13} color="#34d399" /> : <CopyIcon size={13} />}
            <span>{copied ? "Đã sao chép" : "Sao chép"}</span>
          </button>

          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              padding: 4,
              display: "inline-flex",
              alignItems: "center",
            }}
            title={isExpanded ? "Thu gọn" : "Mở rộng"}
          >
            {isExpanded ? <ChevronDownIcon size={16} /> : <ChevronRightIcon size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div style={{ marginTop: 14 }}>
          {/* Theses Cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {theses.map((thesis) => {
              const sc = final_scores.find((s) => s.id === thesis.id) || { mean: 3.0, stdev: 0.0, n: 0 };
              const percent = Math.min(100, Math.max(0, (sc.mean / 5.0) * 100));
              const scoreColor = getScoreColor(sc.mean);
              const catStyle = getCategoryColor(thesis.category);
              const isDetailsOpen = expandedTheses[thesis.id];

              return (
                <div
                  key={thesis.id}
                  style={{
                    borderRadius: 8,
                    background: "rgba(30, 41, 59, 0.5)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                    padding: "10px 14px",
                    transition: "all 0.2s ease",
                  }}
                >
                  {/* Top line: Thesis statement & metadata */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: 12,
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 240 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 4,
                            background: "rgba(255, 255, 255, 0.1)",
                            color: "#f8fafc",
                            fontFamily: "monospace",
                          }}
                        >
                          {thesis.id}
                        </span>
                        {thesis.category && (
                          <span
                            style={{
                              fontSize: 10,
                              fontWeight: 600,
                              padding: "1px 6px",
                              borderRadius: 4,
                              background: catStyle.bg,
                              color: catStyle.text,
                              border: `1px solid ${catStyle.border}`,
                              textTransform: "uppercase",
                            }}
                          >
                            {thesis.category}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 500, color: "#f1f5f9", lineHeight: 1.45 }}>
                        {thesis.thesis}
                      </div>
                    </div>

                    {/* Score summary chips */}
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                          padding: "3px 8px",
                          borderRadius: 6,
                          background: "rgba(0, 0, 0, 0.25)",
                          border: `1px solid ${scoreColor}40`,
                        }}
                      >
                        <span style={{ fontSize: 13, fontWeight: 700, color: scoreColor }}>
                          {sc.mean.toFixed(1)}
                        </span>
                        <span style={{ fontSize: 10, color: "#64748b" }}>/ 5.0</span>
                      </div>

                      <div
                        style={{
                          fontSize: 10,
                          color: sc.stdev <= 0.8 ? "#34d399" : "#fbbf24",
                          background: "rgba(255, 255, 255, 0.04)",
                          padding: "3px 6px",
                          borderRadius: 4,
                          fontFamily: "monospace",
                        }}
                        title={`Độ lệch chuẩn điểm số: ${sc.stdev} (càng thấp càng thống nhất)`}
                      >
                        σ = {sc.stdev.toFixed(2)}
                      </div>
                    </div>
                  </div>

                  {/* Progress Score Bar */}
                  <div
                    style={{
                      height: 5,
                      borderRadius: 3,
                      background: "rgba(255, 255, 255, 0.08)",
                      overflow: "hidden",
                      marginTop: 8,
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${percent}%`,
                        borderRadius: 3,
                        background: `linear-gradient(90deg, ${scoreColor}aa, ${scoreColor})`,
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>

                  {/* Supporting Evidence Toggle */}
                  {thesis.supporting_evidence && (
                    <div style={{ marginTop: 8 }}>
                      <button
                        type="button"
                        onClick={() => toggleThesis(thesis.id)}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#94a3b8",
                          fontSize: 11,
                          cursor: "pointer",
                          padding: 0,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        {isDetailsOpen ? <ChevronDownIcon size={12} /> : <ChevronRightIcon size={12} />}
                        <span>Cơ sở & dẫn chứng</span>
                      </button>

                      {isDetailsOpen && (
                        <div
                          style={{
                            marginTop: 6,
                            padding: "6px 10px",
                            borderRadius: 6,
                            background: "rgba(15, 23, 42, 0.6)",
                            border: "1px solid rgba(255, 255, 255, 0.04)",
                            fontSize: 12,
                            color: "#cbd5e1",
                            lineHeight: 1.4,
                          }}
                        >
                          {thesis.supporting_evidence}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Multi-round Convergence Progression Toggle */}
          {rounds.length > 1 && (
            <div style={{ marginTop: 12, borderTop: "1px solid rgba(255, 255, 255, 0.06)", paddingTop: 8 }}>
              <button
                type="button"
                onClick={() => setShowHistory(!showHistory)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#60a5fa",
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                {showHistory ? <ChevronDownIcon size={12} /> : <ChevronRightIcon size={12} />}
                <span>Xem tiến trình thu hẹp phân kỳ qua các vòng ({rounds.length} vòng)</span>
              </button>

              {showHistory && (
                <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                  {rounds.map((r) => {
                    const avgDev =
                      r.aggregate.length > 0
                        ? r.aggregate.reduce((acc, a) => acc + a.stdev, 0) / r.aggregate.length
                        : 0;
                    return (
                      <div
                        key={r.round}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "6px 10px",
                          borderRadius: 6,
                          background: "rgba(0, 0, 0, 0.2)",
                          fontSize: 11,
                        }}
                      >
                        <span style={{ fontWeight: 600, color: "#e2e8f0" }}>Vòng {r.round}</span>
                        <span style={{ color: "#94a3b8" }}>
                          Độ lệch chuẩn trung bình:{" "}
                          <strong style={{ color: avgDev <= 0.8 ? "#34d399" : "#fbbf24" }}>
                            {avgDev.toFixed(2)}
                          </strong>
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
