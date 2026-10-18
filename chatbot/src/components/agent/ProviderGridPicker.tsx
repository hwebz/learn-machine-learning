import React from "react";
import { ProviderInfo } from "../../types/chat";
import { ProviderLiveCapabilities } from "../../types/capabilities";
import { ModelBadgeLogo } from "../icons/Icons";

interface ProviderGridPickerProps {
  providers: ProviderInfo[];
  selectedProviderId: string;
  onSelectProvider: (providerId: string) => void;
  capabilitiesMap: Record<string, ProviderLiveCapabilities>;
  nameRadioGroup: string;
  selectedCardClass?: string;
}

export function ProviderGridPicker({
  providers,
  selectedProviderId,
  onSelectProvider,
  capabilitiesMap,
  nameRadioGroup,
  selectedCardClass = "selected",
}: ProviderGridPickerProps) {
  return (
    <div className="agent-providers-grid">
      {providers.map((prov) => {
        const isSelected = selectedProviderId === prov.id;
        const isLive = Boolean(capabilitiesMap[prov.id]?.is_live_dom);
        return (
          <div
            key={`${nameRadioGroup}-${prov.id}`}
            className={`agent-provider-card ${isSelected ? selectedCardClass : ""}`}
            onClick={() => onSelectProvider(prov.id)}
          >
            <div className="agent-provider-card-header">
              <div
                className="agent-provider-avatar"
                style={{ background: prov.avatarBg }}
              >
                <ModelBadgeLogo providerId={prov.id} size={15} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span className="agent-provider-name" title={prov.name}>{prov.name}</span>
                  {isLive && (
                    <span className="agent-card-mini-badge live" title="Đã đồng bộ trực tiếp từ DOM">LIVE</span>
                  )}
                </div>
                <div className="agent-provider-model" title={prov.modelName}>{prov.modelName}</div>
              </div>
              <input
                type="radio"
                name={nameRadioGroup}
                checked={isSelected}
                onChange={() => onSelectProvider(prov.id)}
                className="agent-radio"
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
