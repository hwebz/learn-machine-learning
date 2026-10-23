"use client";

import React, { useState } from "react";
import { MatrixReport, MatrixAlternative } from "../../types/chat";

interface MatrixReportViewProps {
  matrix?: MatrixReport;
  report?: MatrixReport;
}

const DIMENSION_CONFIG: Record<
  string,
  { icon: string; label: string; desc: string }
> = {
  cost: { icon: "💰", label: "Chi phí (Cost)", desc: "1 = Rất đắt, 5 = Tiết kiệm / Miễn phí" },
  performance: { icon: "⚡", label: "Hiệu năng (Performance)", desc: "1 = Chậm, 5 = Cực nhanh / Tối ưu" },
  complexity: { icon: "🔧", label: "Độ phức tạp (Complexity)", desc: "1 = Khó triển khai, 5 = Rất đơn giản" },
  maturity: { icon: "📊", label: "Độ hoàn thiện (Maturity)", desc: "1 = Mới nổi / Thử nghiệm, 5 = Chuẩn ngành" },
  scalability: { icon: "📈", label: "Khả năng mở rộng (Scalability)", desc: "1 = Giới hạn, 5 = Quy mô lớn toàn cầu" },
};

function ScoreBar({ score, max = 5 }: { score: number; max?: number }) {
  const safeScore = Math.max(0, Math.min(max, Number(score) || 0));
  const pct = (safeScore / max) * 100;
  const color = safeScore >= 4 ? "#10b981" : safeScore >= 3 ? "#f59e0b" : "#ef4444";
  const bg = safeScore >= 4 ? "rgba(16, 185, 129, 0.15)" : safeScore >= 3 ? "rgba(245, 158, 11, 0.15)" : "rgba(239, 68, 68, 0.15)";

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
      <div
        style={{
          width: 64,
          height: 6,
          borderRadius: 3,
          background: "var(--border-color, rgba(226, 232, 240, 0.6))",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            borderRadius: 3,
            background: color,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize: 11.5,
          fontWeight: 700,
          color,
          backgroundColor: bg,
          padding: "1px 6px",
          borderRadius: 4,
          minWidth: 32,
          textAlign: "center",
        }}
      >
        {safeScore}/{max}
      </span>
    </div>
  );
}

export function MatrixReportView({ matrix, report }: MatrixReportViewProps) {
  const activeMatrix = matrix || report;
  const [sortDim, setSortDim] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const handleHeaderSort = (dimKey: string) => {
    if (sortDim === dimKey) {
      if (!sortAsc) {
        setSortAsc(true);
      } else {
        setSortDim(null);
        setSortAsc(false);
      }
    } else {
      setSortDim(dimKey);
      setSortAsc(false);
    }
  };

  const alternatives: MatrixAlternative[] = React.useMemo(() => {
    if (!activeMatrix || !activeMatrix.alternatives || !Array.isArray(activeMatrix.alternatives)) return [];
    if (!sortDim) return activeMatrix.alternatives;

    return [...activeMatrix.alternatives].sort((a, b) => {
      const scoreA = Number(a.scores?.[sortDim as keyof typeof a.scores]) || 0;
      const scoreB = Number(b.scores?.[sortDim as keyof typeof b.scores]) || 0;
      return sortAsc ? scoreA - scoreB : scoreB - scoreA;
    });
  }, [activeMatrix?.alternatives, sortDim, sortAsc]);

  if (!activeMatrix) return null;

  return (
    <div className="matrix-report-container" style={{ margin: "8px 0 16px 0" }}>
      {/* Title & Executive Summary Card */}
      <div
        style={{
          padding: "18px 20px",
          borderRadius: 12,
          background: "var(--card-bg, #ffffff)",
          border: "1px solid var(--border-color, #e2e8f0)",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 20 }}>📊</span>
          <h2
            style={{
              margin: 0,
              fontSize: 18,
              fontWeight: 700,
              color: "var(--text-primary, #0f172a)",
              letterSpacing: "-0.01em",
            }}
          >
            {activeMatrix.title || "Báo cáo Ma trận So sánh Tổng hợp"}
          </h2>
          <span
            style={{
              marginLeft: "auto",
              fontSize: 11,
              fontWeight: 600,
              padding: "3px 8px",
              borderRadius: 6,
              background: "rgba(59, 130, 246, 0.1)",
              color: "#3b82f6",
              border: "1px solid rgba(59, 130, 246, 0.2)",
            }}
          >
            {alternatives.length} Phương án so sánh
          </span>
        </div>
        {activeMatrix.executive_summary && (
          <p
            style={{
              margin: 0,
              fontSize: 13.5,
              lineHeight: 1.6,
              color: "var(--text-secondary, #475569)",
            }}
          >
            {activeMatrix.executive_summary}
          </p>
        )}
      </div>

      {/* Comparative Matrix Table */}
      {alternatives.length > 0 && (
        <div
          style={{
            borderRadius: 12,
            border: "1px solid var(--border-color, #e2e8f0)",
            background: "var(--card-bg, #ffffff)",
            overflow: "hidden",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              padding: "12px 18px",
              borderBottom: "1px solid var(--border-color, #e2e8f0)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "var(--table-header-bg, #f8fafc)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontWeight: 700, fontSize: 13, color: "var(--text-primary, #0f172a)" }}>
                📈 Bảng So Sánh Các Chiều Đánh Giá
              </span>
              <span style={{ fontSize: 11, color: "var(--text-muted, #94a3b8)" }}>
                (Nhấn vào tên tiêu chí để sắp xếp thứ hạng)
              </span>
            </div>
            {sortDim && (
              <button
                type="button"
                onClick={() => {
                  setSortDim(null);
                  setSortAsc(false);
                }}
                style={{
                  fontSize: 11,
                  color: "#3b82f6",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                ✕ Đặt lại sắp xếp
              </button>
            )}
          </div>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 13,
                textAlign: "left",
              }}
            >
              <thead>
                <tr style={{ background: "var(--table-header-bg, #f8fafc)", borderBottom: "1px solid var(--border-color, #e2e8f0)" }}>
                  <th
                    style={{
                      padding: "10px 16px",
                      fontWeight: 600,
                      color: "var(--text-secondary, #64748b)",
                      width: "220px",
                    }}
                  >
                    Tiêu chí đánh giá
                  </th>
                  {alternatives.map((alt) => (
                    <th
                      key={alt.name}
                      style={{
                        padding: "10px 16px",
                        fontWeight: 700,
                        color: "var(--text-primary, #0f172a)",
                        textAlign: "center",
                        minWidth: 150,
                      }}
                    >
                      {alt.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(DIMENSION_CONFIG).map(([dimKey, info], rIdx) => {
                  const isSorted = sortDim === dimKey;
                  return (
                    <tr
                      key={dimKey}
                      onClick={() => handleHeaderSort(dimKey)}
                      style={{
                        borderBottom: rIdx < Object.keys(DIMENSION_CONFIG).length - 1 ? "1px solid var(--border-color, #f1f5f9)" : "none",
                        backgroundColor: isSorted ? "rgba(59, 130, 246, 0.04)" : "transparent",
                        cursor: "pointer",
                        transition: "background-color 0.15s ease",
                      }}
                      title={`${info.desc} — Nhấn để sắp xếp`}
                    >
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span>{info.icon}</span>
                          <span style={{ fontWeight: 600, color: "var(--text-primary, #0f172a)" }}>
                            {info.label}
                          </span>
                          {isSorted && (
                            <span style={{ fontSize: 10, color: "#3b82f6", fontWeight: 700 }}>
                              {sortAsc ? "▲" : "▼"}
                            </span>
                          )}
                        </div>
                      </td>
                      {alternatives.map((alt) => {
                        const score = alt.scores?.[dimKey as keyof typeof alt.scores] ?? 0;
                        return (
                          <td key={alt.name} style={{ padding: "12px 16px", textAlign: "center" }}>
                            <ScoreBar score={score} />
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pros & Cons Cards Grid */}
      {alternatives.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3
            style={{
              fontSize: 14,
              fontWeight: 700,
              color: "var(--text-primary, #0f172a)",
              marginBottom: 12,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span>⚖️</span>
            <span>Chi tiết Ưu điểm & Hạn chế từng Phương án</span>
          </h3>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(auto-fit, minmax(280px, 1fr))`,
              gap: 14,
            }}
          >
            {alternatives.map((alt, i) => (
              <div
                key={alt.name || i}
                style={{
                  padding: 16,
                  borderRadius: 12,
                  background: "var(--card-bg, #ffffff)",
                  border: "1px solid var(--border-color, #e2e8f0)",
                  boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <h4 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary, #0f172a)" }}>
                    {alt.name}
                  </h4>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: "var(--text-muted, #94a3b8)",
                      background: "rgba(0, 0, 0, 0.04)",
                      padding: "2px 6px",
                      borderRadius: 4,
                    }}
                  >
                    Lựa chọn #{i + 1}
                  </span>
                </div>

                {alt.description && (
                  <p
                    style={{
                      margin: "0 0 12px 0",
                      fontSize: 12.5,
                      color: "var(--text-secondary, #64748b)",
                      lineHeight: 1.5,
                    }}
                  >
                    {alt.description}
                  </p>
                )}

                {/* Pros */}
                <div style={{ marginBottom: 12 }}>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: "#059669",
                      marginBottom: 6,
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <span>✅</span>
                    <span>Ưu điểm (Pros)</span>
                  </div>
                  {alt.pros && alt.pros.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, lineHeight: 1.55, color: "var(--text-primary, #1e293b)" }}>
                      {alt.pros.map((p, pIdx) => (
                        <li key={pIdx} style={{ marginBottom: 3 }}>{p}</li>
                      ))}
                    </ul>
                  ) : (
                    <span style={{ fontSize: 12, color: "var(--text-muted, #94a3b8)" }}>Không ghi nhận ưu điểm nổi bật.</span>
                  )}
                </div>

                {/* Cons */}
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: "#dc2626",
                      marginBottom: 6,
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <span>❌</span>
                    <span>Hạn chế (Cons)</span>
                  </div>
                  {alt.cons && alt.cons.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, lineHeight: 1.55, color: "var(--text-primary, #1e293b)" }}>
                      {alt.cons.map((c, cIdx) => (
                        <li key={cIdx} style={{ marginBottom: 3 }}>{c}</li>
                      ))}
                    </ul>
                  ) : (
                    <span style={{ fontSize: 12, color: "var(--text-muted, #94a3b8)" }}>Không ghi nhận hạn chế lớn.</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendation Card */}
      {activeMatrix.recommendation && (
        <div
          style={{
            padding: "16px 20px",
            borderRadius: 12,
            background: "rgba(16, 185, 129, 0.08)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            marginBottom: 14,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: 18 }}>🎯</span>
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "#065f46" }}>
              Khuyến Nghị Chiến Lược (Recommendation)
            </h3>
          </div>
          <p
            style={{
              margin: 0,
              fontSize: 13.5,
              lineHeight: 1.6,
              color: "#047857",
            }}
          >
            {activeMatrix.recommendation}
          </p>
        </div>
      )}

      {/* Caveats & Disagreements */}
      {((activeMatrix.caveats && activeMatrix.caveats.length > 0) || (activeMatrix.disagreements && activeMatrix.disagreements.length > 0)) && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: activeMatrix.caveats?.length && activeMatrix.disagreements?.length ? "1fr 1fr" : "1fr",
            gap: 12,
          }}
        >
          {activeMatrix.caveats && activeMatrix.caveats.length > 0 && (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: 10,
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span>⚠️</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#92400e" }}>
                  Lưu ý & Giới hạn (Caveats)
                </span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, lineHeight: 1.5, color: "#78350f" }}>
                {activeMatrix.caveats.map((cav, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>{cav}</li>
                ))}
              </ul>
            </div>
          )}

          {activeMatrix.disagreements && activeMatrix.disagreements.length > 0 && (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: 10,
                background: "rgba(99, 102, 241, 0.08)",
                border: "1px solid rgba(99, 102, 241, 0.3)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span>🔀</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#3730a3" }}>
                  Bất đồng & Câu hỏi mở (Disagreements)
                </span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, lineHeight: 1.5, color: "#312e81" }}>
                {activeMatrix.disagreements.map((dis, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>{dis}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
