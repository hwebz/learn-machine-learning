import React from "react";

export const SUGGESTED_AGENT_TOPICS = [
  "Ứng dụng của Deep Learning trong đời sống và y học hiện đại",
  "So sánh cơ chế Thinking & Reasoning giữa Gemini 3.1 Pro, ChatGPT o3 và DeepSeek R1",
  "Khảo sát kiến trúc Agentic AI và khả năng tự động phân rã nhiệm vụ (Task Decomposition)",
  "Xu hướng bán dẫn và chip tăng tốc AI (GPU vs NPU vs TPU) giai đoạn 2026-2030",
];

interface AgentTopicSectionProps {
  query: string;
  setQuery: (val: string) => void;
}

export function AgentTopicSection({ query, setQuery }: AgentTopicSectionProps) {
  return (
    <div className="agent-section">
      <div className="agent-section-header-row">
        <label className="agent-section-label" htmlFor="agent-topic-input">
          <span className="agent-section-step">1</span>
          <span>Chủ đề / Đề tài Nghiên cứu Chuyên sâu</span>
        </label>
        <span className="agent-char-count">{query.length} ký tự</span>
      </div>
      <p className="agent-section-desc">
        Nhập câu hỏi hoặc bài toán phức tạp. Hệ thống sẽ tự động phân tách đề tài thành các nhánh chuyên biệt cho từng mô hình AI phù hợp.
      </p>

      <textarea
        id="agent-topic-input"
        className="agent-topic-input"
        placeholder="Ví dụ: Phân tích toàn diện kiến trúc Transformer, các cải tiến Attention mới nhất và dự đoán xu hướng AI 2026..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        rows={3}
      />

      <div className="agent-suggestions-row">
        {SUGGESTED_AGENT_TOPICS.map((topic, idx) => (
          <button
            key={idx}
            type="button"
            className="agent-suggestion-pill"
            onClick={() => setQuery(topic)}
          >
            💡 {topic}
          </button>
        ))}
      </div>
    </div>
  );
}
