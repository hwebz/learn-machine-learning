import React from "react";
import { TONE_PRESETS } from "../../lib/constants";

interface AgentToneSectionProps {
  selectedTone: string;
  setSelectedTone: (toneId: string) => void;
  step?: number;
}

export function AgentToneSection({ selectedTone, setSelectedTone, step = 6 }: AgentToneSectionProps) {
  return (
    <div className="agent-section">
      <div className="agent-section-header-row">
        <label className="agent-section-label">
          <span className="agent-section-step">{step}</span>
          <span>Chọn Văn phong Báo cáo (Lead Provider Tone)</span>
        </label>
        <span className="agent-role-pill tone">Định hình văn phong</span>
      </div>
      <p className="agent-section-desc">
        Văn phong sẽ được chuyển thành chỉ thị hệ thống chuyên sâu cho Lead Provider để điều chỉnh cách cấu trúc, lập luận và diễn đạt.
      </p>

      <div className="agent-tones-grid">
        {TONE_PRESETS.map((tone) => {
          const isSelected = selectedTone === tone.id;
          return (
            <div
              key={tone.id}
              className={`agent-tone-card ${isSelected ? "selected" : ""}`}
              onClick={() => setSelectedTone(tone.id)}
            >
              <div className="agent-tone-header">
                <span className="agent-tone-icon">{tone.icon}</span>
                <span className="agent-tone-badge">{tone.badge}</span>
              </div>
              <div className="agent-tone-name">{tone.label}</div>
              <div className="agent-tone-desc">{tone.description}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
