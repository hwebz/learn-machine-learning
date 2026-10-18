"use client";

import React from "react";
import { BrainIcon } from "../icons/Icons";

interface WelcomeScreenProps {
  suggestedPrompts: string[];
  selectedCount: number;
  onOpenProvidersModal: () => void;
  onSendMessage: (prompt: string) => void;
}

export function WelcomeScreen({
  suggestedPrompts,
  selectedCount,
  onOpenProvidersModal,
  onSendMessage,
}: WelcomeScreenProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 20px",
        textAlign: "center",
        gap: 20,
        maxWidth: 680,
        margin: "0 auto",
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: "50%",
          background: "linear-gradient(135deg, var(--brand-blue) 0%, #7c3aed 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#ffffff",
          boxShadow: "0 8px 24px rgba(37, 99, 235, 0.25)",
        }}
      >
        <BrainIcon size={32} color="#ffffff" />
      </div>

      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", marginBottom: 6 }}>
          AI Deep Research Hub
        </h2>
        <p style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
          Nghiên cứu bằng việc sử dụng đa mô hình cùng lúc. Nhập câu hỏi bên dưới hoặc chọn gợi ý nghiên cứu:
        </p>
      </div>

      {/* Suggested Prompts Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
          width: "100%",
          marginTop: 10,
        }}
      >
        {suggestedPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => {
              if (selectedCount === 0) {
                onOpenProvidersModal();
              } else {
                onSendMessage(prompt);
              }
            }}
            style={{
              padding: "12px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-default)",
              backgroundColor: "#ffffff",
              textAlign: "left",
              fontSize: 12.5,
              color: "var(--text-primary)",
              lineHeight: 1.4,
              cursor: "pointer",
              boxShadow: "var(--shadow-xs)",
              transition: "all var(--transition-fast)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--brand-blue)";
              e.currentTarget.style.backgroundColor = "var(--brand-blue-light)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border-default)";
              e.currentTarget.style.backgroundColor = "#ffffff";
            }}
          >
            <span style={{ color: "var(--brand-blue)", fontWeight: 700, marginRight: 6 }}>✦</span>
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
