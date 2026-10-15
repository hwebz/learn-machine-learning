"use client";

import React from "react";
import { formatDuration } from "../../lib/timeUtils";

export interface DurationBadgeProps {
  /** Duration in seconds (number), milliseconds, or string (e.g., "75s", "1m 15s") */
  duration?: number | string | null;
  /** Whether to show the stopwatch icon ⏱ (default: true) */
  showIcon?: boolean;
  /** Optional custom icon */
  icon?: React.ReactNode;
  /** Optional visual variant: 'default' | 'compact' | 'subtle' | 'pill' */
  variant?: "default" | "compact" | "subtle" | "pill";
  /** Tooltip / title text */
  title?: string;
  /** Optional custom class name */
  className?: string;
  /** Inline style overrides */
  style?: React.CSSProperties;
}

export function DurationBadge({
  duration,
  showIcon = true,
  icon,
  variant = "default",
  title = "Thời gian thực thi",
  className = "",
  style,
}: DurationBadgeProps) {
  if (duration === undefined || duration === null || duration === "") {
    return null;
  }

  const isPlaceholder = duration === "--";
  const formatted = isPlaceholder ? "--" : formatDuration(duration);

  const isCompact = variant === "compact";
  const isPill = variant === "pill";
  const isSubtle = variant === "subtle";

  // Base styling for each visual variant
  const baseStyle: React.CSSProperties = isPill
    ? {
        color: "#2563eb",
        fontWeight: 600,
        fontSize: 10.5,
        backgroundColor: "#eff6ff",
        padding: "1px 7px",
        borderRadius: 4,
        border: "1px solid #bfdbfe",
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        whiteSpace: "nowrap",
        lineHeight: 1.4,
      }
    : isSubtle
    ? {
        color: "var(--text-secondary, #475569)",
        fontWeight: 500,
        fontSize: 11,
        display: "inline-flex",
        alignItems: "center",
        gap: 3,
        whiteSpace: "nowrap",
      }
    : {
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: isCompact ? 10 : 11,
        fontWeight: 600,
        color: "#475569",
        backgroundColor: "#f1f5f9",
        padding: isCompact ? "1px 6px" : "2px 8px",
        borderRadius: 6,
        border: "1px solid #e2e8f0",
        whiteSpace: "nowrap",
      };

  return (
    <span
      className={`duration-badge ${variant ? `duration-badge-${variant}` : ""} ${className}`.trim()}
      style={{ ...baseStyle, ...style }}
      title={title}
    >
      {showIcon && (
        icon || (
          <span
            className="duration-badge-icon"
            style={{ fontSize: isCompact ? 10 : 11, lineHeight: 1 }}
          >
            ⏱
          </span>
        )
      )}
      <span className="duration-badge-value">{formatted}</span>
    </span>
  );
}

export const TimeTakenBadge = DurationBadge;
