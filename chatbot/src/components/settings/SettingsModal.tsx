"use client";

import React, { useState, useEffect, useCallback } from "react";
import { AppSettings, AvailableBrowser, fetchSettings, updateSettings } from "../../lib/api";
import { PROVIDERS_LIST } from "../../lib/constants";
import { SettingsIcon, ModelBadgeLogo } from "../icons/Icons";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form states
  const [availableBrowsers, setAvailableBrowsers] = useState<AvailableBrowser[]>([]);
  const [selectedBrowser, setSelectedBrowser] = useState<string>("msedge");
  const [workMode, setWorkMode] = useState<"async" | "sync">("async");
  const [maxConcurrent, setMaxConcurrent] = useState<number>(3);
  const [headlessMap, setHeadlessMap] = useState<Record<string, boolean>>({});

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await fetchSettings();
      if (data) {
        setAvailableBrowsers(data.available_browsers || []);
        setSelectedBrowser(data.browser || "msedge");
        setWorkMode(data.work_mode || "async");
        setMaxConcurrent(data.max_concurrent_browsers ?? 3);

        // Build headless map covering all 14 providers
        const currentHeadless: Record<string, boolean> = {};
        for (const prov of PROVIDERS_LIST) {
          const provId = prov.id.toLowerCase();
          if (data.headless_providers && provId in data.headless_providers) {
            currentHeadless[provId] = Boolean(data.headless_providers[provId]);
          } else {
            // Default: false (headed) to ensure browsers like Gemini work safely without anti-bot blocks
            currentHeadless[provId] = false;
          }
        }
        setHeadlessMap(currentHeadless);
      }
    } catch (err: any) {
      setErrorMessage("Không thể tải cài đặt từ máy chủ: " + (err?.message || "Lỗi kết nối"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadData();
      setSaveSuccess(false);
    }
  }, [isOpen, loadData]);

  if (!isOpen) return null;

  const handleToggleHeadless = (providerId: string) => {
    const key = providerId.toLowerCase();
    setHeadlessMap((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleSetAllHeadless = (val: boolean) => {
    const updated: Record<string, boolean> = {};
    for (const prov of PROVIDERS_LIST) {
      updated[prov.id.toLowerCase()] = val;
    }
    setHeadlessMap(updated);
  };

  const handleSetRecommendedHeadless = () => {
    const updated: Record<string, boolean> = {};
    for (const prov of PROVIDERS_LIST) {
      const id = prov.id.toLowerCase();
      // Gemini has strict anti-bot detection in headless mode, so keep it headed (false)
      // Others can safely run headless
      updated[id] = id !== "gemini";
    }
    setHeadlessMap(updated);
  };

  const handleSave = async () => {
    setSaving(true);
    setErrorMessage(null);
    try {
      const result = await updateSettings({
        browser: selectedBrowser,
        work_mode: workMode,
        max_concurrent_browsers: maxConcurrent,
        headless_providers: headlessMap,
      });

      if (result) {
        setSaveSuccess(true);
        setTimeout(() => {
          setSaveSuccess(false);
          onClose();
        }, 800);
      } else {
        setErrorMessage("Lỗi khi lưu cài đặt vào hệ thống.");
      }
    } catch (err: any) {
      setErrorMessage("Lỗi khi lưu cài đặt: " + (err?.message || "Không xác định"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} style={{ zIndex: 9999 }}>
      <div
        className="modal-dialog"
        style={{
          maxWidth: 960,
          width: "95vw",
          maxHeight: "88vh",
          display: "flex",
          flexDirection: "column",
          borderRadius: 16,
          boxShadow: "0 20px 60px -15px rgba(0, 0, 0, 0.45)",
          border: "1px solid var(--border-default)",
          backgroundColor: "#ffffff",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          className="modal-header"
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(180deg, #f8fafc 0%, #ffffff 100%)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
                boxShadow: "0 4px 10px rgba(37, 99, 235, 0.3)",
              }}
            >
              <SettingsIcon size={20} color="#ffffff" />
            </div>
            <div>
              <h2
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  margin: 0,
                  letterSpacing: "-0.01em",
                }}
              >
                Cài đặt hệ thống (Automation Settings)
              </h2>
              <p
                style={{
                  fontSize: 12.5,
                  color: "var(--text-muted)",
                  margin: "3px 0 0 0",
                }}
              >
                Tùy chỉnh trình duyệt Playwright, chế độ xử lý và cấu hình Headless cho từng AI Provider
              </p>
            </div>
          </div>
          <button
            className="icon-btn"
            onClick={onClose}
            aria-label="Close settings modal"
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              border: "1px solid var(--border-default)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              fontSize: 14,
              color: "var(--text-muted)",
            }}
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div
          className="modal-body"
          style={{
            padding: "20px 24px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 22,
          }}
        >
          {loading ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "60px 0",
                gap: 12,
                color: "var(--text-muted)",
              }}
            >
              <div
                style={{
                  width: 30,
                  height: 30,
                  border: "3px solid #e2e8f0",
                  borderTopColor: "var(--brand-blue)",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              <span style={{ fontSize: 13, fontWeight: 500 }}>Đang kiểm tra môi trường và trình duyệt cài đặt...</span>
            </div>
          ) : (
            <>
              {errorMessage && (
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: 8,
                    backgroundColor: "#fef2f2",
                    border: "1px solid #fecaca",
                    color: "#991b1b",
                    fontSize: 13,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span>⚠️</span>
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* ---------------- 1. BROWSER PREFERENCE ---------------- */}
              <section
                style={{
                  padding: 16,
                  borderRadius: 12,
                  backgroundColor: "#f8fafc",
                  border: "1px solid var(--border-default)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                  <div>
                    <h3
                      style={{
                        fontSize: 14.5,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        margin: 0,
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                      }}
                    >
                      <span style={{ fontSize: 16 }}>🌐</span> 1. Trình duyệt tự động hóa (Automation Browser)
                    </h3>
                    <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                      Tất cả trình duyệt khả dụng trên máy tính. Mặc định là Microsoft Edge (nếu có cài đặt) hoặc trình duyệt mặc định của hệ điều hành.
                    </p>
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                    gap: 10,
                  }}
                >
                  {availableBrowsers.map((b) => {
                    const isSelected = selectedBrowser === b.id;
                    return (
                      <div
                        key={b.id}
                        onClick={() => setSelectedBrowser(b.id)}
                        style={{
                          padding: "12px 14px",
                          borderRadius: 10,
                          border: `1.5px solid ${isSelected ? "var(--brand-blue)" : "var(--border-default)"}`,
                          backgroundColor: isSelected ? "#eff6ff" : "#ffffff",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 12,
                          transition: "all 0.15s ease",
                          boxShadow: isSelected ? "0 2px 8px rgba(37, 99, 235, 0.15)" : "none",
                        }}
                      >
                        {/* Radio Ring */}
                        <div
                          style={{
                            width: 18,
                            height: 18,
                            borderRadius: "50%",
                            border: `2px solid ${isSelected ? "var(--brand-blue)" : "#cbd5e1"}`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            marginTop: 2,
                            flexShrink: 0,
                            backgroundColor: "#ffffff",
                          }}
                        >
                          {isSelected && (
                            <div
                              style={{
                                width: 9,
                                height: 9,
                                borderRadius: "50%",
                                backgroundColor: "var(--brand-blue)",
                              }}
                            />
                          )}
                        </div>

                        {/* Browser Details */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                            <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)" }}>
                              {b.name}
                            </span>
                            {b.is_default && (
                              <span
                                style={{
                                  fontSize: 10,
                                  fontWeight: 700,
                                  color: "#1e40af",
                                  backgroundColor: "#dbeafe",
                                  padding: "1px 6px",
                                  borderRadius: 4,
                                }}
                              >
                                Mặc định (Edge)
                              </span>
                            )}
                            {b.is_machine_default && (
                              <span
                                style={{
                                  fontSize: 10,
                                  fontWeight: 600,
                                  color: "#065f46",
                                  backgroundColor: "#d1fae5",
                                  padding: "1px 6px",
                                  borderRadius: 4,
                                }}
                              >
                                Mặc định máy
                              </span>
                            )}
                          </div>
                          <span
                            style={{
                              fontSize: 11,
                              color: "var(--text-muted)",
                              display: "block",
                              marginTop: 3,
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                            title={b.path || b.channel}
                          >
                            {b.path || `Channel: ${b.channel}`}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* ---------------- 2. WORK MODE & CONCURRENCY ---------------- */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                  gap: 16,
                }}
              >
                {/* Work Mode */}
                <section
                  style={{
                    padding: 16,
                    borderRadius: 12,
                    backgroundColor: "#f8fafc",
                    border: "1px solid var(--border-default)",
                  }}
                >
                  <h3
                    style={{
                      fontSize: 14.5,
                      fontWeight: 700,
                      color: "var(--text-primary)",
                      margin: "0 0 4px 0",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <span style={{ fontSize: 16 }}>⚡</span> 3. Chế độ hoạt động (Work Mode)
                  </h3>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 12px 0" }}>
                    Chọn cách thức kích hoạt các trình duyệt tự động
                  </p>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    {/* Async Card */}
                    <div
                      onClick={() => setWorkMode("async")}
                      style={{
                        padding: "12px",
                        borderRadius: 10,
                        border: `1.5px solid ${workMode === "async" ? "var(--brand-blue)" : "var(--border-default)"}`,
                        backgroundColor: workMode === "async" ? "#eff6ff" : "#ffffff",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                          Async (Song song)
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            color: "#1e40af",
                            backgroundColor: "#dbeafe",
                            padding: "1px 5px",
                            borderRadius: 4,
                          }}
                        >
                          Nhanh
                        </span>
                      </div>
                      <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0, lineHeight: 1.35 }}>
                        Chạy đồng thời nhiều chatbot, giảm tối đa thời gian chờ đợi.
                      </p>
                    </div>

                    {/* Sync Card */}
                    <div
                      onClick={() => setWorkMode("sync")}
                      style={{
                        padding: "12px",
                        borderRadius: 10,
                        border: `1.5px solid ${workMode === "sync" ? "var(--brand-blue)" : "var(--border-default)"}`,
                        backgroundColor: workMode === "sync" ? "#eff6ff" : "#ffffff",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                          Sync (Tuần tự)
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            color: "#065f46",
                            backgroundColor: "#d1fae5",
                            padding: "1px 5px",
                            borderRadius: 4,
                          }}
                        >
                          Ít RAM
                        </span>
                      </div>
                      <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: 0, lineHeight: 1.35 }}>
                        Chạy lần lượt từng chatbot một, phù hợp máy tính RAM thấp.
                      </p>
                    </div>
                  </div>
                </section>

                {/* Max Concurrent Browsers */}
                <section
                  style={{
                    padding: 16,
                    borderRadius: 12,
                    backgroundColor: "#f8fafc",
                    border: "1px solid var(--border-default)",
                  }}
                >
                  <h3
                    style={{
                      fontSize: 14.5,
                      fontWeight: 700,
                      color: "var(--text-primary)",
                      margin: "0 0 4px 0",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <span style={{ fontSize: 16 }}>🔢</span> 4. Max concurrent browsers (Tối đa đồng thời)
                  </h3>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 12px 0" }}>
                    Số lượng cửa sổ/tiến trình duyệt mở cùng lúc ở chế độ Async (Mặc định: 3)
                  </p>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 14px",
                      borderRadius: 10,
                      backgroundColor: "#ffffff",
                      border: "1px solid var(--border-default)",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                      Giới hạn luồng song song:
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <button
                        type="button"
                        onClick={() => setMaxConcurrent((prev) => Math.max(1, prev - 1))}
                        disabled={maxConcurrent <= 1}
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: 8,
                          border: "1px solid var(--border-default)",
                          backgroundColor: "#f1f5f9",
                          fontSize: 16,
                          fontWeight: 700,
                          cursor: maxConcurrent <= 1 ? "not-allowed" : "pointer",
                          color: "var(--text-primary)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        -
                      </button>
                      <span
                        style={{
                          fontSize: 16,
                          fontWeight: 800,
                          color: "var(--brand-blue)",
                          minWidth: 24,
                          textAlign: "center",
                        }}
                      >
                        {maxConcurrent}
                      </span>
                      <button
                        type="button"
                        onClick={() => setMaxConcurrent((prev) => Math.min(10, prev + 1))}
                        disabled={maxConcurrent >= 10}
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: 8,
                          border: "1px solid var(--border-default)",
                          backgroundColor: "#f1f5f9",
                          fontSize: 16,
                          fontWeight: 700,
                          cursor: maxConcurrent >= 10 ? "not-allowed" : "pointer",
                          color: "var(--text-primary)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        +
                      </button>
                    </div>
                  </div>
                </section>
              </div>

              {/* ---------------- 3. PER-PROVIDER HEADLESS (3-COLUMNS LAYOUT) ---------------- */}
              <section
                style={{
                  padding: 16,
                  borderRadius: 12,
                  backgroundColor: "#f8fafc",
                  border: "1px solid var(--border-default)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: 10,
                    marginBottom: 14,
                  }}
                >
                  <div>
                    <h3
                      style={{
                        fontSize: 14.5,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                        margin: 0,
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                      }}
                    >
                      <span style={{ fontSize: 16 }}>🖥️</span> 2. Headless Mode theo từng Provider (3 Cột)
                    </h3>
                    <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                      Bật toggle để chạy ngầm (Headless) hoặc tắt toggle để hiện cửa sổ trình duyệt (Headed).
                    </p>
                  </div>

                  {/* Quick Preset Buttons */}
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <button
                      type="button"
                      onClick={() => handleSetAllHeadless(true)}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11,
                        fontWeight: 600,
                        borderRadius: 6,
                        border: "1px solid var(--border-default)",
                        backgroundColor: "#ffffff",
                        color: "var(--text-primary)",
                        cursor: "pointer",
                      }}
                    >
                      Bật hết Headless
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSetAllHeadless(false)}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11,
                        fontWeight: 600,
                        borderRadius: 6,
                        border: "1px solid var(--border-default)",
                        backgroundColor: "#ffffff",
                        color: "var(--text-primary)",
                        cursor: "pointer",
                      }}
                    >
                      Hiện tất cả (Tắt Headless)
                    </button>
                    <button
                      type="button"
                      onClick={handleSetRecommendedHeadless}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11,
                        fontWeight: 700,
                        borderRadius: 6,
                        border: "1px solid #bfdbfe",
                        backgroundColor: "#eff6ff",
                        color: "var(--brand-blue)",
                        cursor: "pointer",
                      }}
                    >
                      Khuyến nghị (Gemini hiện, khác ẩn)
                    </button>
                  </div>
                </div>

                {/* 3-COLUMNS LAYOUT GRID */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                    gap: 10,
                  }}
                >
                  {PROVIDERS_LIST.map((p) => {
                    const key = p.id.toLowerCase();
                    const isHeadless = Boolean(headlessMap[key]);

                    return (
                      <div
                        key={p.id}
                        style={{
                          padding: "10px 12px",
                          borderRadius: 8,
                          border: "1px solid var(--border-default)",
                          backgroundColor: "#ffffff",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 8,
                          transition: "all 0.15s ease",
                        }}
                      >
                        {/* Left: Icon & Provider Name */}
                        <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0, flex: 1 }}>
                          <ModelBadgeLogo type={p.iconType} size={24} />
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <span
                              style={{
                                fontSize: 12.5,
                                fontWeight: 700,
                                color: "var(--text-primary)",
                                display: "block",
                                whiteSpace: "nowrap",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                              }}
                              title={p.name}
                            >
                              {p.name.split(" ")[0]} {p.name.split(" ")[1] || ""}
                            </span>
                            <span
                              style={{
                                fontSize: 10.5,
                                fontWeight: 600,
                                color: isHeadless ? "var(--brand-blue)" : "#e11d48",
                                display: "block",
                              }}
                            >
                              {isHeadless ? "Headless (Ẩn)" : "Headed (Hiện)"}
                            </span>
                          </div>
                        </div>

                        {/* Right: Modern iOS-Style Toggle Switch */}
                        <button
                          type="button"
                          role="switch"
                          aria-checked={isHeadless}
                          onClick={() => handleToggleHeadless(p.id)}
                          style={{
                            width: 38,
                            height: 22,
                            borderRadius: 11,
                            backgroundColor: isHeadless ? "var(--brand-blue)" : "#cbd5e1",
                            position: "relative",
                            border: "none",
                            cursor: "pointer",
                            padding: 2,
                            display: "flex",
                            alignItems: "center",
                            transition: "background-color 0.2s ease",
                            flexShrink: 0,
                          }}
                          title={`Toggle Headless cho ${p.name}`}
                        >
                          <div
                            style={{
                              width: 18,
                              height: 18,
                              borderRadius: "50%",
                              backgroundColor: "#ffffff",
                              transform: isHeadless ? "translateX(16px)" : "translateX(0px)",
                              transition: "transform 0.2s ease",
                              boxShadow: "0 1px 3px rgba(0, 0, 0, 0.25)",
                            }}
                          />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </section>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--border-default)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "#f8fafc",
          }}
        >
          <div>
            {saveSuccess && (
              <span style={{ fontSize: 13, fontWeight: 700, color: "#059669", display: "flex", alignItems: "center", gap: 6 }}>
                ✓ Đã lưu cài đặt thành công!
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button
              type="button"
              className="btn-new-chat-outline"
              onClick={onClose}
              disabled={saving}
              style={{ padding: "8px 18px", borderRadius: 8, fontSize: 13 }}
            >
              Hủy
            </button>
            <button
              type="button"
              className="btn-composer-send"
              onClick={handleSave}
              disabled={saving || loading}
              style={{
                padding: "8px 22px",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              {saving ? (
                <>
                  <span
                    style={{
                      width: 14,
                      height: 14,
                      border: "2px solid #ffffff",
                      borderTopColor: "transparent",
                      borderRadius: "50%",
                      animation: "spin 0.8s linear infinite",
                    }}
                  />
                  <span>Đang lưu...</span>
                </>
              ) : (
                <span>Lưu cài đặt</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
