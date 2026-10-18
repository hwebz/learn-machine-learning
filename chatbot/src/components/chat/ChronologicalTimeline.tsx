"use client";

import React from "react";
import { StepLog, Message } from "../../types/chat";
import { BrainIcon, ChevronRightIcon } from "../icons/Icons";
import {
  buildChronologicalTimeline,
  TimelineThinkingItem,
} from "../../lib/chronologicalTimeline";

export function ProviderThinkingHeader({
  item,
  isLive,
  onClick,
}: {
  item: TimelineThinkingItem;
  isLive: boolean;
  onClick?: () => void;
}) {
  const stepCount = item.steps.length || (item.text ? 1 : 0);
  const providerLabel = item.provider ? item.provider.toUpperCase() : "";

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      className="provider-thinking-header-btn"
      style={{
        backgroundColor: item.isRunning ? "#f0f7ff" : "#ffffff",
        borderRadius: 8,
        border: item.isRunning ? "1.5px solid #93c5fd" : "1px solid #cbd5e1",
        margin: "3px 0",
        padding: "8px 12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        cursor: "pointer",
        userSelect: "none",
        outline: "none",
        boxShadow: item.isRunning
          ? "0 2px 6px rgba(59, 130, 246, 0.08)"
          : "0 1px 2px rgba(0, 0, 0, 0.03)",
        transition: "all 0.15s ease",
      }}
      title="Nhấn để xem chi tiết các bước suy luận trên thanh bên phải"
    >
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <BrainIcon size={14} color="var(--brand-blue)" />
        <span style={{ color: "var(--brand-blue)", fontWeight: 700, fontSize: 12 }}>
          ✦ Các bước suy luận & tìm kiếm ({stepCount}){providerLabel ? ` — ${providerLabel}` : ""}:
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {isLive && item.isRunning ? (
          <span
            style={{
              fontSize: 10.5,
              color: "#059669",
              backgroundColor: "#ecfdf5",
              padding: "2px 8px",
              borderRadius: 12,
              border: "1px solid #a7f3d0",
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              fontWeight: 600,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "#059669",
              }}
            />
            Live DOM
          </span>
        ) : null}
        <span
          style={{
            fontSize: 11,
            color: "var(--brand-blue)",
            fontWeight: 600,
            display: "inline-flex",
            alignItems: "center",
            gap: 3,
            backgroundColor: "#eff6ff",
            padding: "3px 8px",
            borderRadius: 6,
            border: "1px solid #bfdbfe",
          }}
        >
          <span>Xem chi tiết</span>
          <ChevronRightIcon size={12} color="var(--brand-blue)" />
        </span>
      </div>
    </div>
  );
}

export function ChronologicalTimeline({
  steps,
  isLive = false,
  message,
  onSelectThinking,
}: {
  steps: StepLog[];
  isLive?: boolean;
  message?: Message;
  onSelectThinking?: (provider?: string, message?: Message) => void;
}) {
  const items = buildChronologicalTimeline(steps, isLive, message);

  if (items.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {items.map((item) => {
        if (item.kind === "thinking") {
          return (
            <ProviderThinkingHeader
              key={item.key}
              item={item}
              isLive={isLive}
              onClick={() => onSelectThinking?.(item.provider, message)}
            />
          );
        }

        return (
          <div
            key={item.key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color: item.isLatest ? "var(--text-primary)" : "var(--text-secondary)",
              fontWeight: item.isLatest ? 600 : 400,
              padding: "2px 4px",
              borderRadius: 4,
              backgroundColor: item.isLatest ? "var(--brand-blue-light)" : "transparent",
            }}
          >
            {item.isLatest ? (
              <div
                style={{
                  width: 11,
                  height: 11,
                  border: "2px solid #3b82f6",
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                  flexShrink: 0,
                }}
              />
            ) : (
              <span style={{ color: "#059669", fontWeight: 700, flexShrink: 0 }}>✓</span>
            )}
            <span style={{ flex: 1 }}>{item.message}</span>
            {item.timestamp && (
              <span style={{ fontSize: 10.5, color: "var(--text-muted)" }}>
                {item.timestamp}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
