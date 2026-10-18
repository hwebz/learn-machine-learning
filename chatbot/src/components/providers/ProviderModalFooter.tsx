"use client";

import React from "react";

interface ProviderModalFooterProps {
  onClose: () => void;
  onApply: () => void;
  selectedCount: number;
}

export function ProviderModalFooter({
  onClose,
  onApply,
  selectedCount,
}: ProviderModalFooterProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        gap: 12,
        paddingTop: 12,
        borderTop: "1px solid var(--border-default)",
      }}
    >
      <button
        type="button"
        className="btn-new-chat-outline"
        onClick={onClose}
        style={{ padding: "8px 16px" }}
      >
        Hủy
      </button>
      <button
        type="button"
        className="btn-composer-send"
        onClick={onApply}
        disabled={selectedCount === 0}
        style={{
          padding: "8px 20px",
          opacity: selectedCount === 0 ? 0.45 : 1,
          cursor: selectedCount === 0 ? "not-allowed" : "pointer",
        }}
        title={selectedCount === 0 ? "Vui lòng chọn ít nhất 1 nhà cung cấp" : undefined}
      >
        <span>Áp dụng{selectedCount > 0 ? ` (${selectedCount} Models)` : ""}</span>
      </button>
    </div>
  );
}
