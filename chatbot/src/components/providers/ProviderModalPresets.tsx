"use client";

import React from "react";
import { BrainIcon, RefreshIcon } from "../icons/Icons";

interface ProviderModalPresetsProps {
  selectedCount: number;
  totalCount: number;
  onSelectTopThinking: () => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onSyncAll?: () => void;
  isSyncingAll?: boolean;
}

export function ProviderModalPresets({
  selectedCount,
  totalCount,
  onSelectTopThinking,
  onSelectAll,
  onDeselectAll,
  onSyncAll,
  isSyncingAll,
}: ProviderModalPresetsProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "4px 0",
        flexWrap: "wrap",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
          Đã chọn: <strong style={{ color: "var(--brand-blue)" }}>{selectedCount} / {totalCount}</strong> models
        </span>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="button"
          className="btn-composer-pill"
          onClick={onSelectTopThinking}
          style={{ padding: "4px 10px", fontSize: 12 }}
        >
          <BrainIcon size={13} color="var(--brand-blue)" />
          <span>Top Thinking (Copilot, Gemini, Qwen, ChatGPT)</span>
        </button>
        <button
          type="button"
          className="btn-composer-pill"
          onClick={onSelectAll}
          style={{ padding: "4px 10px", fontSize: 12 }}
        >
          <span>Chọn tất cả ({totalCount})</span>
        </button>
        <button
          type="button"
          className="btn-composer-pill"
          onClick={onDeselectAll}
          style={{ padding: "4px 10px", fontSize: 12 }}
        >
          <span>Bỏ chọn tất cả</span>
        </button>
        {onSyncAll && (
          <button
            type="button"
            className="btn-composer-pill"
            onClick={onSyncAll}
            disabled={isSyncingAll}
            style={{
              padding: "4px 10px",
              fontSize: 12,
              borderColor: "#bfdbfe",
              color: "var(--brand-blue)",
              backgroundColor: isSyncingAll ? "#eff6ff" : "transparent",
              cursor: isSyncingAll ? "not-allowed" : "pointer",
            }}
            title="Quét lại DOM của tất cả các chatbot để cập nhật mô hình, suy luận và chế độ"
          >
            <RefreshIcon
              size={12}
              color="var(--brand-blue)"
              style={isSyncingAll ? { animation: "spin 1s linear infinite" } : undefined}
            />
            <span>{isSyncingAll ? "Đang quét tất cả DOM..." : "🔄 Đồng bộ tất cả DOM"}</span>
          </button>
        )}
      </div>
    </div>
  );
}
