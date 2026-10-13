"use client";

import React, { useState } from "react";
import { openProviderBrowser, closeProviderBrowser } from "../../lib/api";
import { ModelBadgeLogo } from "../icons/Icons";

interface ProviderActionBannerProps {
  provider: string;
  reason?: string;
  kind?: string;
  jobId?: string;
  onContinue?: (provider: string) => void;
  compact?: boolean;
}

export function ProviderActionBanner({
  provider,
  reason,
  kind = "login",
  jobId,
  onContinue,
  compact = false,
}: ProviderActionBannerProps) {
  const [isOpening, setIsOpening] = useState(false);
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const displayProvider = provider ? provider.toUpperCase() : "CHATBOT";

  const handleOpenBrowser = async () => {
    setIsOpening(true);
    setErrorMsg(null);
    setStatusMsg(`Đang khởi chạy trình duyệt với hồ sơ của ${displayProvider}...`);
    try {
      const res = await openProviderBrowser(provider);
      setIsBrowserOpen(true);
      setStatusMsg(
        res.message ||
          `Cửa sổ trình duyệt cho ${displayProvider} đã mở. Hãy đăng nhập tài khoản / vượt qua CAPTCHA, sau đó nhấn "Tiếp tục" bên dưới.`
      );
    } catch (err: any) {
      console.error("Failed to open browser:", err);
      setErrorMsg(
        err.message ||
          `Không thể mở trình duyệt cho ${displayProvider}. Vui lòng kiểm tra backend server.`
      );
    } finally {
      setIsOpening(false);
    }
  };

  const handleCloseBrowser = async () => {
    try {
      await closeProviderBrowser(provider);
      setIsBrowserOpen(false);
      setStatusMsg("Đã đóng cửa sổ trình duyệt.");
    } catch (err) {
      console.warn("Error closing browser:", err);
    }
  };

  const handleContinue = async () => {
    setIsContinuing(true);
    setErrorMsg(null);
    try {
      // First ensure manual browser session is cleanly closed to release profile lock
      await closeProviderBrowser(provider);
      setIsBrowserOpen(false);

      if (onContinue) {
        onContinue(provider);
      }
    } catch (err: any) {
      console.error("Error continuing:", err);
      setErrorMsg(err.message || "Lỗi khi tiếp tục nghiên cứu.");
      setIsContinuing(false);
    }
  };

  if (compact) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          padding: "8px 10px",
          backgroundColor: "#fffbeb",
          border: "1px solid #fde68a",
          borderRadius: 6,
          fontSize: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#b45309", fontWeight: 600 }}>
          <ModelBadgeLogo type={provider} size={15} />
          <span>{displayProvider} yêu cầu đăng nhập / xác thực</span>
        </div>
        {reason && (
          <div style={{ color: "#92400e", fontSize: 11, lineHeight: 1.4, wordBreak: "break-word" }}>
            {reason}
          </div>
        )}
        <div style={{ display: "flex", gap: 6, marginTop: 2, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={handleOpenBrowser}
            disabled={isOpening}
            style={{
              padding: "4px 8px",
              fontSize: 11,
              fontWeight: 600,
              borderRadius: 4,
              border: "1px solid #d97706",
              backgroundColor: "#d97706",
              color: "#ffffff",
              cursor: isOpening ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            {isOpening ? "Đang mở..." : `🌐 Mở trình duyệt ${displayProvider}`}
          </button>
          <button
            type="button"
            onClick={handleContinue}
            disabled={isContinuing}
            style={{
              padding: "4px 8px",
              fontSize: 11,
              fontWeight: 600,
              borderRadius: 4,
              border: "1px solid #059669",
              backgroundColor: "#059669",
              color: "#ffffff",
              cursor: isContinuing ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            {isContinuing ? "Đang xử lý..." : "▶ Tiếp tục"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="provider-action-banner animate-fade-in"
      style={{
        margin: "10px 0",
        padding: "14px 16px",
        borderRadius: "var(--radius-md, 8px)",
        backgroundColor: "#fffdf5",
        border: "1.5px solid #f59e0b",
        boxShadow: "0 4px 14px rgba(245, 158, 11, 0.12)",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              backgroundColor: "#fef3c7",
              border: "1.5px solid #fcd34d",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <ModelBadgeLogo type={provider} size={18} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 13.5, fontWeight: 700, color: "#92400e" }}>
                Yêu cầu can thiệp người dùng: {displayProvider}
              </span>
              <span
                style={{
                  fontSize: 10.5,
                  fontWeight: 600,
                  padding: "1px 6px",
                  borderRadius: 4,
                  backgroundColor: "#fef3c7",
                  color: "#b45309",
                  border: "1px solid #fde68a",
                }}
              >
                {kind === "captcha" ? "CAPTCHA / Verification" : "Cần đăng nhập"}
              </span>
            </div>
            <p
              style={{
                fontSize: 12.5,
                color: "#78350f",
                margin: "4px 0 0 0",
                lineHeight: 1.45,
                wordBreak: "break-word",
              }}
            >
              {reason ||
                `Hồ sơ tự động của ${displayProvider} chưa đăng nhập hoặc gặp bức tường xác thực. Hãy nhấn nút bên dưới để mở trình duyệt thực tế, đăng nhập thủ công, sau đó bấm tiếp tục.`}
            </p>
          </div>
        </div>
      </div>

      {statusMsg && (
        <div
          style={{
            padding: "8px 12px",
            borderRadius: 6,
            backgroundColor: isBrowserOpen ? "#eff6ff" : "#fef3c7",
            border: `1px solid ${isBrowserOpen ? "#bfdbfe" : "#fde68a"}`,
            fontSize: 12,
            color: isBrowserOpen ? "#1e40af" : "#92400e",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          {isBrowserOpen && (
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: "#3b82f6",
                animation: "pulse 1.5s infinite",
                flexShrink: 0,
              }}
            />
          )}
          <span>{statusMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div
          style={{
            padding: "8px 12px",
            borderRadius: 6,
            backgroundColor: "#fef2f2",
            border: "1px solid #fecaca",
            fontSize: 12,
            color: "#991b1b",
          }}
        >
          ✕ {errorMsg}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", paddingTop: 2 }}>
        <button
          type="button"
          onClick={handleOpenBrowser}
          disabled={isOpening}
          style={{
            padding: "8px 16px",
            borderRadius: 6,
            border: "none",
            background: "linear-gradient(135deg, #d97706 0%, #b45309 100%)",
            color: "#ffffff",
            fontSize: 12.5,
            fontWeight: 600,
            cursor: isOpening ? "not-allowed" : "pointer",
            boxShadow: "0 2px 6px rgba(217, 119, 6, 0.25)",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.15s ease",
          }}
        >
          {isOpening ? (
            <>
              <span
                style={{
                  width: 12,
                  height: 12,
                  border: "2px solid #ffffff",
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              <span>Đang mở trình duyệt...</span>
            </>
          ) : (
            <>
              <span>🌐</span>
              <span>{isBrowserOpen ? `Đưa trình duyệt ${displayProvider} lên trước` : `Mở trình duyệt ${displayProvider} để đăng nhập`}</span>
            </>
          )}
        </button>

        <button
          type="button"
          onClick={handleContinue}
          disabled={isContinuing}
          style={{
            padding: "8px 18px",
            borderRadius: 6,
            border: "none",
            background: "linear-gradient(135deg, #059669 0%, #047857 100%)",
            color: "#ffffff",
            fontSize: 12.5,
            fontWeight: 600,
            cursor: isContinuing ? "not-allowed" : "pointer",
            boxShadow: "0 2px 6px rgba(5, 150, 105, 0.25)",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.15s ease",
          }}
        >
          {isContinuing ? (
            <>
              <span
                style={{
                  width: 12,
                  height: 12,
                  border: "2px solid #ffffff",
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              <span>Đang tiếp tục nghiên cứu...</span>
            </>
          ) : (
            <>
              <span>▶</span>
              <span>Đã đăng nhập - Tiếp tục</span>
            </>
          )}
        </button>

        {isBrowserOpen && (
          <button
            type="button"
            onClick={handleCloseBrowser}
            style={{
              padding: "6px 12px",
              borderRadius: 6,
              border: "1px solid #d1d5db",
              backgroundColor: "#ffffff",
              color: "#4b5563",
              fontSize: 11.5,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Đóng trình duyệt
          </button>
        )}
      </div>
    </div>
  );
}
