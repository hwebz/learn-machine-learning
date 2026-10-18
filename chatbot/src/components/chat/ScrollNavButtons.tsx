"use client";

import React from "react";
import { ArrowUpCircleIcon, ArrowDownCircleIcon } from "../icons/Icons";

interface ScrollNavButtonsProps {
  show: boolean;
  canScrollTop: boolean;
  canScrollBottom: boolean;
  onScrollToTop: () => void;
  onScrollToBottom: () => void;
}

export function ScrollNavButtons({
  show,
  canScrollTop,
  canScrollBottom,
  onScrollToTop,
  onScrollToBottom,
}: ScrollNavButtonsProps) {
  if (!show) return null;

  return (
    <div className="chat-scroll-nav">
      <button
        type="button"
        className={`scroll-nav-btn ${!canScrollTop ? "disabled" : ""}`}
        onClick={onScrollToTop}
        disabled={!canScrollTop}
        title="Cuộn lên đầu trang (Scroll to top)"
        aria-label="Scroll to top"
      >
        <ArrowUpCircleIcon size={20} />
      </button>
      <button
        type="button"
        className={`scroll-nav-btn ${!canScrollBottom ? "disabled" : ""}`}
        onClick={onScrollToBottom}
        disabled={!canScrollBottom}
        title="Cuộn xuống cuối trang (Scroll to bottom)"
        aria-label="Scroll to bottom"
      >
        <ArrowDownCircleIcon size={20} />
      </button>
    </div>
  );
}
