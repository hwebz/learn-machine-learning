import React from "react";
import { ProviderInfo } from "../../types/chat";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";
import { ModelBadgeLogo, RefreshIcon } from "../icons/Icons";
import { resolveSubProviderLiveConfig } from "../../lib/agentPromptBuilder";

interface SubProvidersDelegationSectionProps {
  availableProviders: ProviderInfo[];
  selectedDelegatedProviders: string[];
  toggleDelegatedProvider: (providerId: string) => void;
  onSelectTopThinking: () => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  capabilitiesMap: Record<string, ProviderLiveCapabilities>;
  selectionsMap: Record<string, ProviderSelectionConfig>;
  onSyncProvider?: (providerId: string) => Promise<any>;
  isSyncingAllSub?: boolean;
  onSyncAllSub?: () => Promise<void>;
  subSyncMessage?: string | null;
}

export function SubProvidersDelegationSection({
  availableProviders,
  selectedDelegatedProviders,
  toggleDelegatedProvider,
  onSelectTopThinking,
  onSelectAll,
  onDeselectAll,
  capabilitiesMap,
  selectionsMap,
  onSyncProvider,
  isSyncingAllSub = false,
  onSyncAllSub,
  subSyncMessage,
}: SubProvidersDelegationSectionProps) {
  return (
    <div className="agent-section">
      <div className="agent-section-header-row">
        <label className="agent-section-label">
          <span className="agent-section-step">3</span>
          <span>Chọn Sub-Providers được phép giao việc (Delegated Sub-Providers)</span>
        </label>
        <span className="agent-role-pill sub">Ủy quyền & Phân bổ nhánh</span>
      </div>
      <p className="agent-section-desc">
        Chỉ các AI provider được tích chọn dưới đây mới được phép điều phối thực thi các nhánh nghiên cứu con. Orchestrator sẽ lập kế hoạch và phân rã bài toán dựa trên danh sách này.
      </p>

      {/* Quick Actions Toolbar */}
      <div className="agent-subproviders-toolbar">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>
            Trạng thái chọn:
          </span>
          <span
            className={`agent-counter-badge ${selectedDelegatedProviders.length === 0 ? "empty" : ""}`}
          >
            {selectedDelegatedProviders.length} / {availableProviders.length} providers
          </span>
        </div>
        <div className="agent-subproviders-actions">
          <button
            type="button"
            className="agent-mini-action-btn primary"
            onClick={onSelectTopThinking}
            title="Chọn các mô hình suy luận chuyên sâu hàng đầu"
          >
            ⚡ Top Reasoning
          </button>
          <button
            type="button"
            className="agent-mini-action-btn"
            onClick={onSelectAll}
            title="Chọn tất cả 14 providers"
          >
            Chọn tất cả
          </button>
          <button
            type="button"
            className="agent-mini-action-btn"
            onClick={onDeselectAll}
            title="Bỏ chọn tất cả"
          >
            Bỏ chọn tất cả
          </button>
          {onSyncProvider && onSyncAllSub && (
            <button
              type="button"
              className="agent-mini-action-btn"
              onClick={onSyncAllSub}
              disabled={isSyncingAllSub || selectedDelegatedProviders.length === 0}
              title="Đồng bộ trực tiếp DOM cho toàn bộ sub-providers được chọn"
            >
              <RefreshIcon size={12} className={isSyncingAllSub ? "spin" : ""} />
              <span>{isSyncingAllSub ? "Đang quét DOM..." : "Đồng bộ DOM Sub"}</span>
            </button>
          )}
        </div>
      </div>

      {subSyncMessage && (
        <div
          className={`agent-sync-feedback ${subSyncMessage.startsWith("Lỗi") ? "error" : "success"}`}
          style={{ margin: "8px 0" }}
        >
          {subSyncMessage}
        </div>
      )}

      {selectedDelegatedProviders.length === 0 && (
        <div className="agent-delegated-warning">
          ⚠️ Vui lòng chọn ít nhất 1 sub-provider để Orchestrator có thể giao việc.
        </div>
      )}

      <div className="agent-providers-grid">
        {availableProviders.map((prov) => {
          const isSelected = selectedDelegatedProviders.includes(prov.id);
          const isLive = Boolean(capabilitiesMap[prov.id]?.is_live_dom);
          const liveInfo = resolveSubProviderLiveConfig(prov.id, selectionsMap, capabilitiesMap);
          return (
            <div
              key={`delegated-${prov.id}`}
              className={`agent-provider-card ${isSelected ? "selected delegated-selected" : ""}`}
              onClick={() => toggleDelegatedProvider(prov.id)}
            >
              <div className="agent-provider-card-header">
                {/* Checkbox indicator */}
                <div className={`agent-checkbox-card-indicator ${isSelected ? "checked" : ""}`}>
                  {isSelected ? "✓" : ""}
                </div>

                <div
                  className="agent-provider-avatar"
                  style={{ background: prov.avatarBg }}
                >
                  <ModelBadgeLogo providerId={prov.id} size={15} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <span className="agent-provider-name" title={prov.name}>{prov.name}</span>
                    {isLive ? (
                      <span className="agent-card-mini-badge live" title="Đã đồng bộ trực tiếp từ DOM">LIVE</span>
                    ) : (
                      <span className="agent-card-mini-badge cached" title="Cấu hình bộ đệm">CACHED</span>
                    )}
                  </div>
                  <div className="agent-provider-model" title={liveInfo.activeModel || prov.modelName}>
                    {liveInfo.activeModel || prov.modelName}
                  </div>
                </div>
              </div>

              {/* Sub-Provider Active Live DOM Feature Chips */}
              <div className="agent-sub-chips-row">
                {liveInfo.isDeepResearch && (
                  <span className="agent-sub-chip dr" title="Deep Research đang bật">Deep Research</span>
                )}
                {liveInfo.activeThinking && (
                  <span className="agent-sub-chip think" title={`Reasoning: ${liveInfo.activeThinking}`}>
                    🧠 {liveInfo.activeThinking}
                  </span>
                )}
                {liveInfo.isDeepThinking && !liveInfo.activeThinking && (
                  <span className="agent-sub-chip think" title="Deep Thinking R1">🧠 Think</span>
                )}
                {liveInfo.isWebSearch && (
                  <span className="agent-sub-chip web" title="Tìm kiếm Web">🌐 Web</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
