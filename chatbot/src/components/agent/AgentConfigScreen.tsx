"use client";

import React, { useState } from "react";
import { PROVIDERS_LIST, TONE_PRESETS, TonePresetItem } from "../../lib/constants";
import { ProviderInfo } from "../../types/chat";
import { BrainIcon, CloseIcon, ModelBadgeLogo, SendIcon } from "../icons/Icons";

interface AgentConfigScreenProps {
  onStartAgentResearch: (config: {
    query: string;
    orchestrator_provider: string;
    orchestrator_config: Record<string, any>;
    lead_provider: string;
    lead_config: Record<string, any>;
    tone: string;
  }) => void;
  onCancel: () => void;
}

const SUPPORTED_AGENT_PROVIDERS = [
  "gemini",
  "chatgpt",
  "perplexity",
  "copilot",
  "deepseek",
  "qwen",
  "kimi",
  "zhipu",
];

const SUGGESTED_AGENT_TOPICS = [
  "Ứng dụng của Deep Learning trong đời sống và y học hiện đại",
  "So sánh cơ chế Thinking & Reasoning giữa Gemini 3.1 Pro, ChatGPT o3 và DeepSeek R1",
  "Khảo sát kiến trúc Agentic AI và khả năng tự động phân rã nhiệm vụ (Task Decomposition)",
  "Xu hướng bán dẫn và chip tăng tốc AI (GPU vs NPU vs TPU) giai đoạn 2026-2030",
];

export function AgentConfigScreen({ onStartAgentResearch, onCancel }: AgentConfigScreenProps) {
  const [query, setQuery] = useState("");
  const [selectedOrchestrator, setSelectedOrchestrator] = useState<string>("gemini");
  const [orchThinking, setOrchThinking] = useState<boolean>(true);
  const [orchModel, setOrchModel] = useState<string>("pro");
  const [orchMode, setOrchMode] = useState<string>("high");

  const [selectedLead, setSelectedLead] = useState<string>("chatgpt");
  const [leadThinking, setLeadThinking] = useState<boolean>(true);
  const [leadModel, setLeadModel] = useState<string>("default");

  const [selectedTone, setSelectedTone] = useState<string>("professional");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const availableProviders = PROVIDERS_LIST.filter((p) =>
    SUPPORTED_AGENT_PROVIDERS.includes(p.id)
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isSubmitting) return;

    setIsSubmitting(true);

    // Build orchestrator config
    const orchConfig: Record<string, any> = {};
    if (selectedOrchestrator === "gemini") {
      orchConfig.model = orchModel;
      orchConfig.mode = orchMode;
    } else if (selectedOrchestrator === "qwen") {
      orchConfig.mode = "qwen-3.8-max";
      orchConfig.thinking = orchThinking;
    } else if (selectedOrchestrator === "zhipu") {
      orchConfig.model = "glm-5.3";
      orchConfig.mode = "high";
    } else {
      orchConfig.thinking = orchThinking;
    }

    // Build lead config
    const leadConfig: Record<string, any> = {};
    if (selectedLead === "gemini") {
      leadConfig.model = "pro";
      leadConfig.mode = "high";
    } else {
      leadConfig.thinking = leadThinking;
    }

    onStartAgentResearch({
      query: query.trim(),
      orchestrator_provider: selectedOrchestrator,
      orchestrator_config: orchConfig,
      lead_provider: selectedLead,
      lead_config: leadConfig,
      tone: selectedTone,
    });
  };

  return (
    <div className="agent-config-overlay">
      <div className="agent-config-container">
        {/* Header */}
        <div className="agent-config-header">
          <div className="agent-config-title-group">
            <div className="agent-badge-icon">
              <span style={{ fontSize: 22 }}>🤖</span>
            </div>
            <div>
              <h2 className="agent-config-title">Deep Research Orchestrator</h2>
              <p className="agent-config-subtitle">
                Hệ thống điều phối đa tác nhân AI tự động: phân tách bài toán, kích hoạt đa mô hình chuyên biệt và tổng hợp báo cáo độc lập.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="agent-close-btn"
            onClick={onCancel}
            title="Đóng cấu hình"
          >
            <CloseIcon size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="agent-config-form">
          {/* Section 1: Research Topic Input */}
          <div className="agent-section">
            <label className="agent-section-label">
              <span className="agent-section-step">1</span>
              <span>Chủ đề / Đề tài Nghiên cứu (Research Topic)</span>
            </label>
            <textarea
              className="agent-topic-input"
              rows={3}
              placeholder="Nhập câu hỏi hoặc chủ đề phức tạp cần điều phối đa tác nhân... (VD: Ứng dụng của Deep Learning trong đời sống và y học)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
            />
            <div className="agent-suggestions-row">
              <span style={{ fontSize: 11.5, color: "var(--text-muted)", alignSelf: "center", marginRight: 4 }}>
                Gợi ý:
              </span>
              {SUGGESTED_AGENT_TOPICS.map((topic, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="agent-suggestion-pill"
                  onClick={() => setQuery(topic)}
                >
                  {topic.length > 45 ? topic.slice(0, 45) + "..." : topic}
                </button>
              ))}
            </div>
          </div>

          {/* Section 2: Orchestrator Provider */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">2</span>
                <span>Chọn Orchestrator Provider (Phân rã nhiệm vụ & Lập kế hoạch)</span>
              </label>
              <span className="agent-role-pill">Phân tích & Tách nhánh</span>
            </div>
            <p className="agent-section-desc">
              Tác nhân này chịu trách nhiệm phân tích chủ đề, bóc tách thành các nhiệm vụ con và gán cho các chatbot phù hợp nhất kèm cấu hình Thinking.
            </p>

            <div className="agent-providers-grid">
              {availableProviders.map((prov) => {
                const isSelected = selectedOrchestrator === prov.id;
                return (
                  <div
                    key={`orch-${prov.id}`}
                    className={`agent-provider-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedOrchestrator(prov.id)}
                  >
                    <div className="agent-provider-card-header">
                      <div
                        className="agent-provider-avatar"
                        style={{ background: prov.avatarBg }}
                      >
                        <ModelBadgeLogo providerId={prov.id} size={15} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="agent-provider-name">{prov.name}</div>
                        <div className="agent-provider-model">{prov.modelName}</div>
                      </div>
                      <input
                        type="radio"
                        name="orchestrator"
                        checked={isSelected}
                        onChange={() => setSelectedOrchestrator(prov.id)}
                        className="agent-radio"
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Fine-tune config for selected orchestrator */}
            <div className="agent-provider-finetune">
              <div className="agent-finetune-title">
                <BrainIcon size={14} color="var(--brand-blue)" />
                <span>Cấu hình mô hình Orchestrator ({selectedOrchestrator.toUpperCase()}):</span>
              </div>
              <div className="agent-finetune-options">
                {selectedOrchestrator === "gemini" && (
                  <>
                    <label className="agent-option-inline">
                      <span>Mô hình:</span>
                      <select
                        value={orchModel}
                        onChange={(e) => setOrchModel(e.target.value)}
                        className="agent-select"
                      >
                        <option value="pro">Gemini 3.1 Pro (Deep)</option>
                        <option value="flash">Gemini Flash (Nhanh)</option>
                        <option value="argon">Gemini Argon</option>
                      </select>
                    </label>
                    <label className="agent-option-inline">
                      <span>Reasoning Effort:</span>
                      <select
                        value={orchMode}
                        onChange={(e) => setOrchMode(e.target.value)}
                        className="agent-select"
                      >
                        <option value="high">Cao (High Thinking)</option>
                        <option value="medium">Vừa (Medium)</option>
                        <option value="low">Thấp (Low)</option>
                      </select>
                    </label>
                  </>
                )}
                {selectedOrchestrator !== "gemini" && (
                  <label className="agent-checkbox-inline">
                    <input
                      type="checkbox"
                      checked={orchThinking}
                      onChange={(e) => setOrchThinking(e.target.checked)}
                    />
                    <span>Kích hoạt Thinking / Deep Reasoning Mode</span>
                  </label>
                )}
              </div>
            </div>
          </div>

          {/* Section 3: Lead Provider */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">3</span>
                <span>Chọn Lead Provider (Tổng hợp & Viết báo cáo cuối)</span>
              </label>
              <span className="agent-role-pill lead">Tổng hợp & Đúc kết</span>
            </div>
            <p className="agent-section-desc">
              Tác nhân chủ trì tiếp nhận toàn bộ kết quả từ các chatbot vệ tinh, kiểm chứng chéo và đúc kết thành báo cáo chuyên sâu hoàn chỉnh.
            </p>

            <div className="agent-providers-grid">
              {availableProviders.map((prov) => {
                const isSelected = selectedLead === prov.id;
                return (
                  <div
                    key={`lead-${prov.id}`}
                    className={`agent-provider-card ${isSelected ? "selected lead-selected" : ""}`}
                    onClick={() => setSelectedLead(prov.id)}
                  >
                    <div className="agent-provider-card-header">
                      <div
                        className="agent-provider-avatar"
                        style={{ background: prov.avatarBg }}
                      >
                        <ModelBadgeLogo providerId={prov.id} size={15} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="agent-provider-name">{prov.name}</div>
                        <div className="agent-provider-model">{prov.modelName}</div>
                      </div>
                      <input
                        type="radio"
                        name="lead_provider"
                        checked={isSelected}
                        onChange={() => setSelectedLead(prov.id)}
                        className="agent-radio"
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="agent-provider-finetune">
              <div className="agent-finetune-title">
                <BrainIcon size={14} color="#10a37f" />
                <span>Cấu hình Lead Provider ({selectedLead.toUpperCase()}):</span>
              </div>
              <div className="agent-finetune-options">
                <label className="agent-checkbox-inline">
                  <input
                    type="checkbox"
                    checked={leadThinking}
                    onChange={(e) => setLeadThinking(e.target.checked)}
                  />
                  <span>Kích hoạt Suy luận sâu (Thinking / Deep Research) cho Lead Provider</span>
                </label>
              </div>
            </div>
          </div>

          {/* Section 4: Report Tone Selection */}
          <div className="agent-section">
            <div className="agent-section-header-row">
              <label className="agent-section-label">
                <span className="agent-section-step">4</span>
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

          {/* Footer Submit */}
          <div className="agent-config-footer">
            <button
              type="button"
              className="agent-btn-secondary"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Hủy
            </button>
            <button
              type="submit"
              className="agent-btn-primary"
              disabled={!query.trim() || isSubmitting}
            >
              <span style={{ fontSize: 16 }}>🚀</span>
              <span>
                {isSubmitting ? "Đang khởi tạo Agent..." : "Khởi chạy Deep Research Orchestrator"}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
