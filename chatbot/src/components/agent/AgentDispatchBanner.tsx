"use client";

import React, { useState, useEffect, useMemo } from "react";
import { AgentDispatchPlanItem, Message, StepLog } from "../../types/chat";
import { ModelBadgeLogo, BrainIcon, ChevronRightIcon, ExternalLinkIcon } from "../icons/Icons";
import { DurationBadge } from "../common/DurationBadge";
import { formatDuration, getStepElapsedDuration } from "../../lib/timeUtils";

export interface AgentDispatchBannerProps {
  orchestratorProvider?: string;
  leadProvider?: string;
  tone?: string;
  dispatchPlan?: AgentDispatchPlanItem[];
  status?: string;
  providerRuns?: Record<string, any> | any[];
  steps?: StepLog[];
  topic?: string;
  message?: Message;
  onSelectThinking?: (provider: string, message?: Message) => void;
}

function normalize(p?: string): string {
  if (!p) return "";
  const s = p.trim().toLowerCase();
  if (s.includes("qwen")) return "qwen";
  if (s.includes("copilot")) return "copilot";
  if (s.includes("gemini")) return "gemini";
  if (s.includes("deepseek")) return "deepseek";
  if (s.includes("chatgpt") || s.includes("openai")) return "chatgpt";
  if (s.includes("grok")) return "grok";
  if (s.includes("claude")) return "claude";
  if (s.includes("perplexity")) return "perplexity";
  if (s.includes("kimi")) return "kimi";
  if (s.includes("zhipu") || s.includes("glm")) return "zhipu";
  return s;
}

export const ROLE_GROUP_CONFIG: Record<string, { label: string; className: string }> = {
  researcher: { label: "Researcher", className: "researcher" },
  infra: { label: "Infra/Data", className: "infra" },
  fact_checker: { label: "Fact-Check", className: "fact_checker" },
  red_team: { label: "Red Team", className: "red_team" },
};

export function AgentDispatchBanner({
  orchestratorProvider = "gemini",
  leadProvider = "chatgpt",
  tone = "professional",
  dispatchPlan,
  status = "queued",
  providerRuns,
  steps = [],
  topic,
  message,
  onSelectThinking,
}: AgentDispatchBannerProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [liveSeconds, setLiveSeconds] = useState<number>(0);

  // Live timer tick for active stages
  useEffect(() => {
    const isJobActive =
      status === "queued" ||
      status === "orchestrating" ||
      status === "researching" ||
      status === "leading" ||
      status === "running";

    if (!isJobActive) return;

    const interval = setInterval(() => {
      setLiveSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [status]);

  const runsArray: any[] = useMemo(() => {
    if (Array.isArray(providerRuns)) return providerRuns;
    if (providerRuns && typeof providerRuns === "object") return Object.values(providerRuns);
    return [];
  }, [providerRuns]);

  // Extract steps per provider / role
  const orchNorm = normalize(orchestratorProvider);
  const leadNorm = normalize(leadProvider);

  // --- 1. ORCHESTRATOR STATUS & THINKING ---
  const orchSteps = useMemo(() => {
    return steps.filter((st) => {
      const p = normalize(st.provider || st.data?.provider);
      const isRole = st.data?.role === "orchestrator";
      const isStatus = (st.status as string) === "orchestrating";
      return isRole || (p === orchNorm && (isStatus || st.step === "orchestrator_result"));
    });
  }, [steps, orchNorm]);

  const orchState = useMemo<"live" | "completed" | "waiting" | "error">(() => {
    if (status === "completed" || status === "researching" || status === "leading") return "completed";
    if (orchSteps.some((s) => s.step === "orchestrator_result" || s.data?.dispatch)) return "completed";
    if (dispatchPlan && dispatchPlan.length > 0) return "completed";
    if (status === "failed") return "error";
    if (status === "orchestrating") return "live";
    return "waiting";
  }, [status, dispatchPlan, orchSteps]);

  const orchThinkingText = useMemo(() => {
    if (orchSteps.length > 0) {
      const last = orchSteps[orchSteps.length - 1];
      if (last.thinkingSteps && last.thinkingSteps.length > 0) {
        return last.thinkingSteps[last.thinkingSteps.length - 1].title;
      }
      if (last.data?.thinking_steps && last.data.thinking_steps.length > 0) {
        const rawSteps = last.data.thinking_steps;
        return rawSteps[rawSteps.length - 1].title || rawSteps[rawSteps.length - 1];
      }
      if (last.message) return last.message;
    }
    if (orchState === "live") {
      return "Đang phân tích chủ đề và lập kế hoạch điều phối các tác nhân AI...";
    }
    if (orchState === "completed") {
      return `Đã hoàn thành phân rã chủ đề thành ${dispatchPlan?.length || 2} nhiệm vụ chuyên sâu độc lập.`;
    }
    if (orchState === "error") {
      return "Quá trình phân rã tác vụ gặp sự cố.";
    }
    return "Đang trong hàng đợi chuẩn bị kích hoạt Orchestrator...";
  }, [orchSteps, orchState, dispatchPlan]);

  const orchTimeTaken = useMemo(() => {
    const recordedElapsed = getStepElapsedDuration(orchSteps);
    if (recordedElapsed !== null) {
      return formatDuration(recordedElapsed);
    }
    if (orchState === "live") {
      return formatDuration(liveSeconds);
    }
    return "--";
  }, [orchSteps, orchState, liveSeconds]);

  // --- 2. LEAD PROVIDER STATUS & THINKING ---
  const leadSteps = useMemo(() => {
    return steps.filter((st) => {
      const p = normalize(st.provider || st.data?.provider);
      const isRole = st.data?.role === "lead";
      const isStatus = (st.status as string) === "leading";
      return isRole || (p === leadNorm && isStatus);
    });
  }, [steps, leadNorm]);

  const leadState = useMemo<"live" | "completed" | "waiting" | "error">(() => {
    if (status === "completed") return "completed";
    if (leadSteps.some((s) => s.step === "completed" || s.data?.report_markdown)) return "completed";
    if (status === "leading") return "live";
    if (status === "failed") return "error";
    return "waiting";
  }, [status, leadSteps]);

  const leadThinkingText = useMemo(() => {
    if (leadSteps.length > 0) {
      const last = leadSteps[leadSteps.length - 1];
      if (last.thinkingSteps && last.thinkingSteps.length > 0) {
        return last.thinkingSteps[last.thinkingSteps.length - 1].title;
      }
      if (last.data?.thinking_steps && last.data.thinking_steps.length > 0) {
        const rawSteps = last.data.thinking_steps;
        return rawSteps[rawSteps.length - 1].title || rawSteps[rawSteps.length - 1];
      }
      if (last.message) return last.message;
    }
    if (leadState === "live") {
      return `Đang tổng hợp các phát hiện, đối soát luận điểm và viết báo cáo theo văn phong ${tone}...`;
    }
    if (leadState === "completed") {
      return `Báo cáo nghiên cứu chuyên sâu đã hoàn tất thành công theo văn phong ${tone}.`;
    }
    if (leadState === "error") {
      return "Quá trình tổng hợp báo cáo thất bại.";
    }
    const remainingCount = dispatchPlan ? Math.max(0, dispatchPlan.length - runsArray.length) : 0;
    return `Đang chờ ${remainingCount > 0 ? `${remainingCount} tác nhân` : "các tác nhân"} hoàn thành nghiên cứu nhánh để bắt đầu tổng hợp.`;
  }, [leadSteps, leadState, tone, dispatchPlan, runsArray.length]);

  const leadTimeTaken = useMemo(() => {
    const recordedElapsed = getStepElapsedDuration(leadSteps);
    if (recordedElapsed !== null) {
      return formatDuration(recordedElapsed);
    }
    if (leadState === "live") {
      return formatDuration(liveSeconds);
    }
    return "--";
  }, [leadSteps, leadState, liveSeconds]);

  // Subtask helper
  const getSubtaskDetails = (item: AgentDispatchPlanItem, idx: number) => {
    const itemNorm = normalize(item.id);
    const branchIdx = item.branch_index || (idx + 1);
    const branchKey = item.provider_role_key || `subtask:${itemNorm}_${branchIdx}`;

    const run = runsArray.find(
      (r) =>
        r.provider_role_key === branchKey ||
        r.subtask_id === `${message?.id || ""}:${item.id}_${branchIdx}` ||
        (r.branch && r.branch.toLowerCase().includes(item.sub_topic.toLowerCase())) ||
        (r.branch_index === branchIdx) ||
        (runsArray.length === 1 && normalize(r.provider) === itemNorm)
    );

    // Thinking text for this branch (isolate from orchestrator and lead)
    const pSteps = steps.filter((st) => {
      const stKey = st.data?.provider_role_key;
      if (stKey) return stKey === branchKey;
      const isSubtaskRole = st.data?.role === "subtask" || (st.status as string) === "researching";
      if (!isSubtaskRole) return false;
      const stBranch = st.data?.branch;
      if (stBranch && (stBranch.includes(item.sub_topic) || item.sub_topic.includes(stBranch))) return true;
      if (st.data?.branch_index && st.data.branch_index === branchIdx) return true;
      if (st.data?.subtask_id && st.data.subtask_id.endsWith(`_${branchIdx}`)) return true;
      return normalize(st.provider || st.data?.provider) === itemNorm;
    });

    let subState: "live" | "completed" | "waiting" | "error" = "waiting";
    if (run) {
      if (run.status === "ok" || run.status === "completed") subState = "completed";
      else if (run.status === "error" || run.status === "failed") subState = "error";
      else subState = "live";
    } else {
      const hasCompleted = pSteps.some((s) => s.step === "completed" || s.data?.status === "ok" || s.data?.answer_md);
      const hasError = pSteps.some((s) => s.step === "error" || s.data?.status === "error" || s.data?.status === "failed");
      if (hasCompleted) subState = "completed";
      else if (hasError) subState = "error";
      else if (pSteps.length > 0) subState = "live";
      else if (status === "researching") subState = "live";
      else if (status === "leading" || status === "completed") subState = "completed";
      else subState = "waiting";
    }

    let thinkingMsg = "";
    if (pSteps.length > 0) {
      const lastPStep = pSteps[pSteps.length - 1];
      if (lastPStep.thinkingSteps && lastPStep.thinkingSteps.length > 0) {
        thinkingMsg = lastPStep.thinkingSteps[lastPStep.thinkingSteps.length - 1].title;
      } else if (lastPStep.data?.thinking_steps && lastPStep.data.thinking_steps.length > 0) {
        const raw = lastPStep.data.thinking_steps;
        thinkingMsg = raw[raw.length - 1].title || raw[raw.length - 1];
      } else if (lastPStep.message) {
        thinkingMsg = lastPStep.message;
      }
    }

    if (!thinkingMsg) {
      if (subState === "live") {
        thinkingMsg = `Đang phân tích sâu và tra cứu dữ liệu cho chuyên đề: "${item.sub_topic}"...`;
      } else if (subState === "completed") {
        thinkingMsg = `Đã hoàn thành nghiên cứu nhánh "${item.sub_topic}" và đính kèm dẫn chứng.`;
      } else if (subState === "error") {
        thinkingMsg = `Nghiên cứu nhánh "${item.sub_topic}" gặp lỗi kết nối.`;
      } else {
        thinkingMsg = "Đang chờ điều phối lượt nghiên cứu...";
      }
    }

    // Time taken
    let timeStr = "--";
    if (run?.elapsed_s !== undefined && Number(run.elapsed_s) > 0) {
      timeStr = formatDuration(Number(run.elapsed_s));
    } else if (run?.elapsed_ms !== undefined && Number(run.elapsed_ms) > 0) {
      timeStr = formatDuration(Number(run.elapsed_ms) / 1000);
    } else {
      const recordedElapsed = getStepElapsedDuration(pSteps);
      if (recordedElapsed !== null) {
        timeStr = formatDuration(recordedElapsed);
      } else if (subState === "live") {
        timeStr = formatDuration(liveSeconds);
      }
    }

    return {
      state: subState,
      thinkingText: thinkingMsg,
      timeTaken: timeStr,
      branchIdx,
      branchKey,
    };
  };

  const completedSubtasksCount = useMemo(() => {
    if (!dispatchPlan) return 0;
    return dispatchPlan.filter((item, idx) => {
      const info = getSubtaskDetails(item, idx);
      return info.state === "completed";
    }).length;
  }, [dispatchPlan, runsArray, status]);

  return (
    <div className="agent-dispatch-container">
      {/* 1. TOP HEADER SUMMARY BAR */}
      <div className="agent-dispatch-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="agent-dispatch-header-left">
          <div className="agent-dispatch-pill">
            <span style={{ fontSize: 13 }}>🤖</span>
            <span>Deep Research Orchestrator</span>
          </div>

          <div
            className="agent-meta-badge clickable"
            title="Nhấn để xem chi tiết suy luận của Orchestrator ở thanh bên phải"
            onClick={(e) => {
              e.stopPropagation();
              onSelectThinking?.(orchestratorProvider, message);
            }}
          >
            <span className="agent-meta-label">Orchestrator:</span>
            <ModelBadgeLogo providerId={orchestratorProvider} size={14} />
            <span className="agent-meta-val">{orchestratorProvider.toUpperCase()}</span>
          </div>

          <div
            className="agent-meta-badge lead clickable"
            title="Nhấn để xem chi tiết tổng hợp của Lead Provider ở thanh bên phải"
            onClick={(e) => {
              e.stopPropagation();
              onSelectThinking?.(leadProvider, message);
            }}
          >
            <span className="agent-meta-label">Lead Synthesizer:</span>
            <ModelBadgeLogo providerId={leadProvider} size={14} />
            <span className="agent-meta-val">{leadProvider.toUpperCase()}</span>
          </div>

          {tone && (
            <div className="agent-meta-badge tone">
              <span className="agent-meta-label">Tone:</span>
              <span className="agent-meta-val">{tone}</span>
            </div>
          )}
        </div>

        <div className="agent-dispatch-header-right">
          <div className="agent-stage-stepper">
            <span className={`stage-step-dot ${orchState === "live" ? "active" : orchState === "completed" ? "done" : ""}`}>
              1. Phân rã
            </span>
            <span className="stage-sep">➔</span>
            <span className={`stage-step-dot ${status === "researching" ? "active" : (status === "leading" || status === "completed") ? "done" : ""}`}>
              2. Nghiên cứu ({completedSubtasksCount}/{dispatchPlan?.length || 0})
            </span>
            <span className="stage-sep">➔</span>
            <span className={`stage-step-dot ${leadState === "live" ? "active" : leadState === "completed" ? "done" : ""}`}>
              3. Tổng hợp
            </span>
          </div>

          <span
            style={{
              transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            <ChevronRightIcon size={16} color="var(--text-muted)" />
          </span>
        </div>
      </div>

      {/* EXPANDED CONTENT: ALL 3 PROVIDER TIERS */}
      {isExpanded && (
        <div className="agent-tiers-container">
          {/* ======================================================== */}
          {/* TIER 1: ORCHESTRATOR PROVIDER SUMMARY CARD */}
          {/* ======================================================== */}
          <div className="agent-tier-section">
            <div className="agent-tier-title-row">
              <div className="agent-tier-heading">
                <span className="agent-tier-num">1</span>
                <span>Tác nhân Điều phối (Orchestrator)</span>
              </div>
              <span className="agent-tier-hint">Phân rã bài toán và lập kế hoạch dispatch</span>
            </div>

            <div
              className={`agent-provider-summary-card ${orchState}`}
              onClick={() => onSelectThinking?.("orchestrator", message)}
              title="Nhấn để xem chi tiết tiến trình suy luận của Orchestrator"
            >
              <div className="agent-card-top-row">
                <div className="agent-card-provider-info">
                  <ModelBadgeLogo providerId={orchestratorProvider} size={18} />
                  <div>
                    <span className="agent-card-provider-name">{orchestratorProvider.toUpperCase()}</span>
                    <span className="agent-card-role-tag orchestrator">Master Orchestrator</span>
                  </div>
                </div>

                <div className="agent-card-meta-right">
                  {/* Status Indicator: LIVE vs Completed */}
                  <div className={`agent-live-badge ${orchState}`}>
                    {orchState === "live" && (
                      <>
                        <span className="pulse-dot live" />
                        <span className="badge-text">LIVE</span>
                      </>
                    )}
                    {orchState === "completed" && (
                      <>
                        <span className="badge-icon">✓</span>
                        <span className="badge-text">Completed</span>
                      </>
                    )}
                    {orchState === "waiting" && (
                      <>
                        <span className="badge-icon">⏳</span>
                        <span className="badge-text">Chờ xử lý</span>
                      </>
                    )}
                    {orchState === "error" && (
                      <>
                        <span className="badge-icon">⚠️</span>
                        <span className="badge-text">Lỗi</span>
                      </>
                    )}
                  </div>

                  {/* Time Taken */}
                  <DurationBadge
                    duration={orchTimeTaken}
                    title="Thời gian thực thi của Orchestrator"
                  />
                </div>
              </div>

              {/* Active Thinking Step */}
              <div className="agent-card-thinking-box">
                <div className="agent-card-thinking-header">
                  <BrainIcon size={13} color="#7c3aed" />
                  <span className="thinking-title-label">
                    {orchState === "live" ? "Tiến trình suy luận (Active Step):" : "Tóm tắt bước suy luận hoàn thành:"}
                  </span>
                </div>
                <div className="agent-card-thinking-content">{orchThinkingText}</div>
              </div>

              {/* Card Footer with Click Prompt */}
              <div className="agent-card-footer">
                <span className="agent-click-prompt">
                  Xem chi tiết từng bước suy luận & phân tách ở Sidebar phải <ExternalLinkIcon size={12} />
                </span>
              </div>
            </div>
          </div>

          {/* ======================================================== */}
          {/* TIER 2: SUB-PROVIDERS AUTONOMOUS BRANCHES */}
          {/* ======================================================== */}
          <div className="agent-tier-section">
            <div className="agent-tier-title-row">
              <div className="agent-tier-heading">
                <span className="agent-tier-num">2</span>
                <span>Các Tác nhân Nghiên cứu Độc lập (Sub-providers)</span>
                <span className="agent-branch-count-pill">
                  {completedSubtasksCount}/{dispatchPlan?.length || 0} hoàn thành
                </span>
              </div>
              <span className="agent-tier-hint">Mỗi tác nhân tự vận hành và nghiên cứu một nhánh tri thức chuyên sâu</span>
            </div>

            {dispatchPlan && dispatchPlan.length > 0 ? (
              <div className="agent-dispatch-grid">
                {dispatchPlan.map((item, idx) => {
                  const subInfo = getSubtaskDetails(item, idx);

                  return (
                    <div
                      key={subInfo.branchKey}
                      className={`agent-subtask-card ${subInfo.state}`}
                      onClick={() => onSelectThinking?.(subInfo.branchKey, message)}
                      title={`Nhấn để mở chi tiết suy luận của ${item.name || item.id} (Nhánh #${subInfo.branchIdx})`}
                    >
                      <div className="agent-subtask-card-header">
                        <div className="agent-subtask-provider">
                          <ModelBadgeLogo providerId={item.id} size={16} />
                          <div>
                            <span className="agent-subtask-name">{item.name || item.id}</span>
                            <span className="agent-branch-idx">Nhánh #{subInfo.branchIdx}</span>
                            {item.role_group && ROLE_GROUP_CONFIG[item.role_group] && (
                              <span className={`agent-role-badge ${ROLE_GROUP_CONFIG[item.role_group].className}`}>
                                {ROLE_GROUP_CONFIG[item.role_group].label}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="agent-subtask-header-right">
                          {item.config?.thinking && (
                            <div className="agent-live-badge normal compact">
                              <BrainIcon size={11} color="rgb(124, 58, 237)" />
                            </div>
                          )}
                          {/* Live vs Completed Indicator */}
                          <div className={`agent-live-badge ${subInfo.state} compact`}>
                            {subInfo.state === "live" && (
                              <>
                                <span className="pulse-dot live" />
                                <span className="badge-text">LIVE</span>
                              </>
                            )}
                            {subInfo.state === "completed" && (
                              <>
                                <span className="badge-icon">✓</span>
                                <span className="badge-text">Done</span>
                              </>
                            )}
                            {subInfo.state === "waiting" && (
                              <>
                                <span className="badge-icon">⏳</span>
                                <span className="badge-text">Chờ</span>
                              </>
                            )}
                            {subInfo.state === "error" && (
                              <>
                                <span className="badge-icon">⚠️</span>
                                <span className="badge-text">Lỗi</span>
                              </>
                            )}
                          </div>

                          {/* Time Taken */}
                          <DurationBadge
                            duration={subInfo.timeTaken}
                            variant="compact"
                            title="Thời gian thực thi nhánh này"
                          />
                        </div>
                      </div>

                      {/* Sub-topic Title */}
                      <div className="agent-subtask-topic">{item.sub_topic}</div>

                      {/* Question / Prompt preview */}
                      <div className="agent-subtask-question">{item.question}</div>

                      {/* Active Thinking Step */}
                      <div className="agent-subtask-thinking-box">
                        <div className="subtask-thinking-icon">
                          <BrainIcon size={11} color="var(--brand-blue)" />
                        </div>
                        <span className="subtask-thinking-text">{subInfo.thinkingText}</span>
                      </div>

                      {/* Config Tags */}
                      {item.config && Object.keys(item.config).length > 0 && (
                        <div className="agent-subtask-config">
                          {item.config.thinking && false ? <span className="config-tag"><BrainIcon size={11} color="rgb(124, 58, 237)" /></span> : null}
                          {item.config.model ? <span className="config-tag">Model: {item.config.model}</span> : null}
                          {item.config.mode ? <span className="config-tag">Mode: {item.config.mode}</span> : null}
                        </div>
                      )}

                      {/* Click Affordance */}
                      <div className="agent-subtask-footer-action">
                        <span>Chi tiết tiến trình suy luận ➔</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="agent-subtasks-empty-state">
                <div className="spinner-dots" />
                <span>Orchestrator đang phân tích để kiến tạo danh sách tác nhân chuyên trách...</span>
              </div>
            )}
          </div>

          {/* ======================================================== */}
          {/* TIER 3: LEAD PROVIDER SYNTHESIZER SUMMARY CARD */}
          {/* ======================================================== */}
          <div className="agent-tier-section">
            <div className="agent-tier-title-row">
              <div className="agent-tier-heading">
                <span className="agent-tier-num">3</span>
                <span>Tác nhân Tổng hợp Trưởng (Lead Provider)</span>
              </div>
              <span className="agent-tier-hint">Hợp nhất luận cứ, đối soát sự thật và định hình báo cáo hoàn chỉnh</span>
            </div>

            <div
              className={`agent-provider-summary-card lead ${leadState}`}
              onClick={() => onSelectThinking?.("lead", message)}
              title="Nhấn để xem chi tiết tiến trình tổng hợp của Lead Provider"
            >
              <div className="agent-card-top-row">
                <div className="agent-card-provider-info">
                  <ModelBadgeLogo providerId={leadProvider} size={18} />
                  <div>
                    <span className="agent-card-provider-name">{leadProvider.toUpperCase()}</span>
                    <span className="agent-card-role-tag lead">Lead Synthesizer</span>
                    <span className="agent-card-tone-pill">Tone: {tone}</span>
                  </div>
                </div>

                <div className="agent-card-meta-right">
                  {/* Status Indicator: LIVE vs Completed */}
                  <div className={`agent-live-badge ${leadState}`}>
                    {leadState === "live" && (
                      <>
                        <span className="pulse-dot live" />
                        <span className="badge-text">LIVE</span>
                      </>
                    )}
                    {leadState === "completed" && (
                      <>
                        <span className="badge-icon">✓</span>
                        <span className="badge-text">Completed</span>
                      </>
                    )}
                    {leadState === "waiting" && (
                      <>
                        <span className="badge-icon">⏳</span>
                        <span className="badge-text">Chờ nhánh</span>
                      </>
                    )}
                    {leadState === "error" && (
                      <>
                        <span className="badge-icon">⚠️</span>
                        <span className="badge-text">Lỗi</span>
                      </>
                    )}
                  </div>

                  {/* Time Taken */}
                  <DurationBadge
                    duration={leadTimeTaken}
                    title="Thời gian tổng hợp của Lead Provider"
                  />
                </div>
              </div>

              {/* Active Thinking Step */}
              <div className="agent-card-thinking-box lead">
                <div className="agent-card-thinking-header">
                  <BrainIcon size={13} color="#059669" />
                  <span className="thinking-title-label">
                    {leadState === "live" ? "Tiến trình tổng hợp & suy luận (Active Step):" : "Trạng thái tổng hợp báo cáo:"}
                  </span>
                </div>
                <div className="agent-card-thinking-content">{leadThinkingText}</div>
              </div>

              {/* Card Footer with Click Prompt */}
              <div className="agent-card-footer">
                <span className="agent-click-prompt">
                  Xem chi tiết báo cáo tổng hợp & các bước suy luận ở Sidebar phải <ExternalLinkIcon size={12} />
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
