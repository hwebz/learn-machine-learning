"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { ProviderInfo } from "../../types/chat";
import { checkBackendHealth } from "../../lib/api";
import { ProviderLiveCapabilities, ProviderSelectionConfig } from "../../types/capabilities";
import { ProviderModalHeader } from "./ProviderModalHeader";
import { ProviderModalPresets } from "./ProviderModalPresets";
import { ProviderCard } from "./ProviderCard";
import { ProviderModalFooter } from "./ProviderModalFooter";

interface ProviderModalProps {
  isOpen: boolean;
  onClose: () => void;
  providers: ProviderInfo[];
  selectedProviderIds: string[];
  onToggleProvider: (id: string) => void;
  onSelectMultipleProviders: (ids: string[]) => void;
  capabilitiesMap?: Record<string, ProviderLiveCapabilities>;
  selectionsMap?: Record<string, ProviderSelectionConfig>;
  onUpdateSelection?: (providerId: string, updates: Partial<ProviderSelectionConfig>) => void;
  onSyncProvider?: (providerId: string) => Promise<any>;
  loadingProvider?: string | null;
  onSyncAll?: () => void;
  isSyncingAll?: boolean;
  onLoadCapabilities?: (providerId: string) => void;
}

export function ProviderModal({
  isOpen,
  onClose,
  providers,
  selectedProviderIds,
  onToggleProvider,
  onSelectMultipleProviders,
  capabilitiesMap = {},
  selectionsMap = {},
  onUpdateSelection,
  onSyncProvider,
  loadingProvider,
  onSyncAll,
  isSyncingAll,
  onLoadCapabilities,
}: ProviderModalProps) {
  const [backendStatus, setBackendStatus] = useState<{ online: boolean; data?: any }>({
    online: false,
  });
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [tempSelected, setTempSelected] = useState<string[]>(selectedProviderIds);

  const prevIsOpenRef = useRef(false);

  useEffect(() => {
    // Only synchronize tempSelected and check health when modal transitions from closed to open
    if (isOpen && !prevIsOpenRef.current) {
      setTempSelected(selectedProviderIds);
      setLoadingHealth(true);
      checkBackendHealth().then((res) => {
        setBackendStatus(res);
        setLoadingHealth(false);
      });
    }
    prevIsOpenRef.current = isOpen;
  }, [isOpen, selectedProviderIds]);

  // Load capabilities for all providers if not yet cached
  useEffect(() => {
    if (isOpen && onLoadCapabilities) {
      providers.forEach((p) => {
        if (!capabilitiesMap[p.id]) {
          onLoadCapabilities(p.id);
        }
      });
    }
  }, [isOpen, onLoadCapabilities, providers, capabilitiesMap]);

  const handleToggle = useCallback((id: string) => {
    setTempSelected((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  }, []);

  const handleSelectAll = useCallback(() => {
    setTempSelected(providers.map((p) => p.id));
  }, [providers]);

  const handleSelectTopThinking = useCallback(() => {
    const thinkingIds = providers
      .filter((p) => p.supportsDeepMode)
      .slice(0, 4)
      .map((p) => p.id);
    setTempSelected(thinkingIds);
  }, [providers]);

  const handleDeselectAll = useCallback(() => {
    setTempSelected([]);
  }, []);

  const handleApply = useCallback(() => {
    if (tempSelected.length === 0) return;
    onSelectMultipleProviders(tempSelected);
    onClose();
  }, [tempSelected, onSelectMultipleProviders, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-dialog"
        style={{ maxWidth: 960, maxHeight: "90vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        <ProviderModalHeader
          onClose={onClose}
          backendStatus={backendStatus}
          loadingHealth={loadingHealth}
        />

        <div className="modal-body">
          <ProviderModalPresets
            selectedCount={tempSelected.length}
            totalCount={providers.length}
            onSelectTopThinking={handleSelectTopThinking}
            onSelectAll={handleSelectAll}
            onDeselectAll={handleDeselectAll}
            onSyncAll={onSyncAll}
            isSyncingAll={isSyncingAll}
          />

          {/* Providers Grid with Combined Options */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
              gap: 14,
              maxHeight: "calc(88vh - 200px)",
              minHeight: 380,
              overflowY: "auto",
              paddingRight: 6,
            }}
          >
            {providers.map((p) => (
              <ProviderCard
                key={p.id}
                provider={p}
                isSelected={tempSelected.includes(p.id)}
                onToggle={() => handleToggle(p.id)}
                capabilities={capabilitiesMap[p.id]}
                selection={selectionsMap[p.id]}
                onUpdateSelection={onUpdateSelection}
                onSyncProvider={onSyncProvider}
                isSyncing={loadingProvider === p.id}
                isSyncingAll={isSyncingAll}
              />
            ))}
          </div>

          <ProviderModalFooter
            onClose={onClose}
            onApply={handleApply}
            selectedCount={tempSelected.length}
          />
        </div>
      </div>
    </div>
  );
}
