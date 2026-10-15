"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";

interface ScrollableTabsRowProps {
  children: React.ReactNode;
  titlePrefix?: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
}

export function ScrollableTabsRow({
  children,
  titlePrefix,
  style,
  className = "",
}: ScrollableTabsRowProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const isDownRef = useRef(false);
  const startXRef = useRef(0);
  const startScrollLeftRef = useRef(0);
  const hasMovedRef = useRef(false);

  const updateScrollButtons = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const { scrollLeft, scrollWidth, clientWidth } = el;
    // Buffer of 4px to account for subpixel rendering
    setCanScrollLeft(scrollLeft > 4);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 4);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    updateScrollButtons();

    const handleScroll = () => {
      updateScrollButtons();
    };

    el.addEventListener("scroll", handleScroll, { passive: true });

    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => {
        updateScrollButtons();
      });
      ro.observe(el);
      Array.from(el.children).forEach((child) => ro?.observe(child));
    }

    // Also update on window resize
    window.addEventListener("resize", updateScrollButtons);

    return () => {
      el.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", updateScrollButtons);
      if (ro) ro.disconnect();
    };
  }, [updateScrollButtons, children]);

  // Convert mouse wheel vertical scroll to horizontal scroll
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const el = containerRef.current;
    if (!el) return;
    if (e.deltaY !== 0) {
      el.scrollLeft += e.deltaY;
      updateScrollButtons();
    }
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only primary mouse button (left-click)
    if (e.button !== 0) return;
    const el = containerRef.current;
    if (!el) return;

    isDownRef.current = true;
    startXRef.current = e.pageX;
    startScrollLeftRef.current = el.scrollLeft;
    hasMovedRef.current = false;

    // Attach global mouseup listener to catch releases outside the container
    const onGlobalMouseUp = () => {
      isDownRef.current = false;
      window.removeEventListener("mouseup", onGlobalMouseUp);
      setTimeout(() => {
        setIsDragging(false);
        hasMovedRef.current = false;
      }, 70);
    };
    window.addEventListener("mouseup", onGlobalMouseUp);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDownRef.current) return;
    const el = containerRef.current;
    if (!el) return;

    const walk = e.pageX - startXRef.current;
    if (Math.abs(walk) > 4) {
      if (!hasMovedRef.current) {
        hasMovedRef.current = true;
        setIsDragging(true);
      }
      el.scrollLeft = startScrollLeftRef.current - walk;
      updateScrollButtons();
    }
  };

  const handleMouseUpOrLeave = () => {
    if (isDownRef.current) {
      isDownRef.current = false;
      setTimeout(() => {
        setIsDragging(false);
        hasMovedRef.current = false;
      }, 70);
    }
  };

  // Prevent click on child tabs if user was dragging/panning
  const handleClickCapture = (e: React.MouseEvent) => {
    if (hasMovedRef.current) {
      e.stopPropagation();
      e.preventDefault();
    }
  };

  const scrollByAmount = (amount: number) => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollBy({ left: amount, behavior: "smooth" });
    setTimeout(updateScrollButtons, 320);
  };

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        display: "flex",
        alignItems: "center",
        ...style,
      }}
      className={`scrollable-tabs-wrapper ${className}`}
    >
      {canScrollLeft && (
        <button
          type="button"
          onClick={() => scrollByAmount(-220)}
          aria-label="Cuộn sang trái"
          title="Cuộn sang trái"
          className="live-tabs-nav-btn left"
        >
          ‹
        </button>
      )}

      <div
        ref={containerRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUpOrLeave}
        onMouseLeave={handleMouseUpOrLeave}
        onClickCapture={handleClickCapture}
        className="live-streaming-tabs-scroll"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          borderBottom: "1.5px solid #e2e8f0",
          paddingBottom: 8,
          overflowX: "auto",
          width: "100%",
          cursor: isDragging ? "grabbing" : "grab",
          userSelect: isDragging ? "none" : "auto",
        }}
      >
        {titlePrefix && <div style={{ flexShrink: 0 }}>{titlePrefix}</div>}
        {children}
      </div>

      {canScrollRight && (
        <button
          type="button"
          onClick={() => scrollByAmount(220)}
          aria-label="Cuộn sang phải"
          title="Cuộn sang phải"
          className="live-tabs-nav-btn right"
        >
          ›
        </button>
      )}
    </div>
  );
}
