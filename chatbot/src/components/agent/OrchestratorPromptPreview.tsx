import React, { useState } from "react";
import { ProviderInfo } from "../../types/chat";
import { ProviderLiveCapabilities } from "../../types/capabilities";

interface OrchestratorPromptPreviewProps {
  promptText: string;
  orchestratorProvider?: ProviderInfo;
  orchestratorModel?: string;
  selectedDelegatedCount: number;
  selectedDelegatedProviders: string[];
  capabilitiesMap: Record<string, ProviderLiveCapabilities>;
}

export function OrchestratorPromptPreview({
  promptText,
  orchestratorProvider,
  orchestratorModel,
  selectedDelegatedCount,
  selectedDelegatedProviders,
  capabilitiesMap,
}: OrchestratorPromptPreviewProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [isCopied, setIsCopied] = useState(false);

  const liveDomCount = selectedDelegatedProviders.filter(
    (p) => capabilitiesMap[p]?.is_live_dom
  ).length;

  const handleCopy = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(promptText);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div className="agent-prompt-preview-section">
      <div className="agent-prompt-preview-header">
        <div className="agent-prompt-preview-title">
          <span style={{ fontSize: 16 }}>📋</span>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <strong>Prompt Phân Rã Sub-Tasks (Live DOM Synced)</strong>
              <span className="agent-prompt-badge">DOM Tự Động Đồng Bộ</span>
            </div>
            <span className="agent-prompt-preview-sub">
              Prompt điều phối được xây dựng tự động từ cấu hình DOM thực tế của {selectedDelegatedCount} Sub-Providers được chọn.
            </span>
          </div>
        </div>

        <div className="agent-prompt-preview-actions">
          <button
            type="button"
            className="agent-prompt-copy-btn"
            onClick={handleCopy}
            title="Sao chép toàn bộ Prompt điều phối đã tạo"
          >
            {isCopied ? "✓ Đã sao chép!" : "📋 Sao chép Prompt"}
          </button>

          <button
            type="button"
            className="agent-prompt-toggle-btn"
            onClick={() => setIsOpen(!isOpen)}
            title={isOpen ? "Thu gọn bản xem trước" : "Mở rộng xem trước"}
          >
            {isOpen ? "▲ Thu gọn" : "▼ Xem Prompt"}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="agent-prompt-preview-body">
          <div className="agent-prompt-preview-stats">
            <span className="agent-stat-tag">
              🎯 Orchestrator: <strong>{orchestratorProvider?.name || "Mặc định"} ({orchestratorModel || "Mặc định"})</strong>
            </span>
            <span className="agent-stat-tag">
              👥 Sub-Providers: <strong>{selectedDelegatedCount} providers</strong>
            </span>
            <span className="agent-stat-tag">
              🌐 Cấu hình DOM: <strong>{liveDomCount} / {selectedDelegatedCount} Live DOM</strong>
            </span>
          </div>
          <pre className="agent-prompt-preview-code">
            {promptText}
          </pre>
        </div>
      )}
    </div>
  );
}
