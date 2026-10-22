"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { ChatSession, ProviderInfo, StepLog, ThinkingStep, SourceLink, Message } from "../../types/chat";
import { SUGGESTED_PROMPTS } from "../../lib/constants";
import { extractProviderResponse } from "../../lib/providerResponse";
import { MarkdownContent } from "./MarkdownContent";
import { MatrixReportView } from "./MatrixReportView";
import { WelcomeScreen } from "./WelcomeScreen";
import { ScrollNavButtons } from "./ScrollNavButtons";
import { ProviderActionBanner } from "./ProviderActionBanner";
import { ScrollableTabsRow } from "./ScrollableTabsRow";
import { AgentDispatchBanner } from "../agent/AgentDispatchBanner";
import { DebateTranscript } from "../agent/DebateTranscript";
import { detectAllProvidersNeedingAction } from "../../lib/providerAction";
import { useVoiceRecording } from "../../lib/useVoiceRecording";
import {
  SupportedDataTypes,
  VoiceChatSupport,
  ProviderLiveCapabilities,
  ProviderSelectionConfig,
} from "../../types/capabilities";
import { ProviderOptionsBar } from "./ProviderOptionsBar";
import {
  PlusIcon,
  SettingsIcon,
  SidebarCollapseIcon,
  ShareIcon,
  RefreshIcon,
  CopyIcon,
  BookmarkIcon,
  MoreHorizontalIcon,
  LibraryIcon,
  PaperclipIcon,
  ImageIcon,
  MicIcon,
  GridIcon,
  SendIcon,
  StopIcon,
  BrainIcon,
  ChevronRightIcon,
  ModelBadgeLogo,
  ExternalLinkIcon,
} from "../icons/Icons";

import { ChronologicalTimeline } from "./ChronologicalTimeline";
import { normalizeProvider, extractProvider } from "../../lib/chronologicalTimeline";

interface ChatAreaProps {
  session: ChatSession;
  providers: ProviderInfo[];
  selectedProvider: ProviderInfo;
  selectedProviders: ProviderInfo[];
  onToggleProvider: (providerId: string) => void;
  onSendMessage: (content: string) => void;
  onToggleRightSidebar: () => void;
  isGenerating: boolean;
  onOpenProvidersModal: () => void;
  onOpenAgentConfig?: () => void;
  activeSteps?: StepLog[];
  onSelectThinking?: (provider?: string, message?: Message) => void;
  onStopResearch?: () => void;
  onRetryProvider?: (provider: string, jobId?: string) => void;
  supportedDataTypes?: SupportedDataTypes;
  voiceChatSupport?: VoiceChatSupport;
  capabilitiesMap?: Record<string, ProviderLiveCapabilities>;
  selectionsMap?: Record<string, ProviderSelectionConfig>;
  onUpdateSelection?: (providerId: string, updates: Partial<ProviderSelectionConfig>) => void;
  onSyncProvider?: (providerId: string) => void;
  loadingProvider?: string | null;
}

export function ChatArea({
  session,
  providers,
  selectedProvider,
  selectedProviders,
  onToggleProvider,
  onSendMessage,
  onToggleRightSidebar,
  isGenerating,
  onOpenProvidersModal,
  onOpenAgentConfig,
  activeSteps = [],
  onSelectThinking,
  onStopResearch,
  onRetryProvider,
  supportedDataTypes,
  voiceChatSupport,
  capabilitiesMap,
  selectionsMap,
  onUpdateSelection,
  onSyncProvider,
  loadingProvider,
}: ChatAreaProps) {
  const [inputText, setInputText] = useState("");
  const [isCopied, setIsCopied] = useState<string | null>(null);
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<{ id: string; name: string; size: string; type: string }[]>([]);
  const [activeOptionsProviderId, setActiveOptionsProviderId] = useState<string>("");
  const [messageMatrixTabs, setMessageMatrixTabs] = useState<Record<string, "matrix" | "narrative">>({});
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // Voice recording integration
  const {
    isRecording,
    isTranscribing,
    error: voiceError,
    toggleRecording,
  } = useVoiceRecording({
    onTranscribed: (text) => {
      setInputText((prev) => (prev ? `${prev} ${text}` : text));
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, isImage: boolean = false) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const newItems = Array.from(files).map((f) => ({
      id: `${Date.now()}-${f.name}`,
      name: f.name,
      size: `${(f.size / 1024).toFixed(1)} KB`,
      type: isImage ? "image" : "file",
    }));
    setAttachedFiles((prev) => [...prev, ...newItems]);
    e.target.value = "";
  };

  const handleRemoveFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // Close model dropdown when clicking outside or pressing Escape
  useEffect(() => {
    if (!isModelDropdownOpen) return;

    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (
        modelDropdownRef.current &&
        !modelDropdownRef.current.contains(event.target as Node)
      ) {
        setIsModelDropdownOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsModelDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isModelDropdownOpen]);

  const [canScrollTop, setCanScrollTop] = useState(false);
  const [canScrollBottom, setCanScrollBottom] = useState(false);
  const [showScrollNav, setShowScrollNav] = useState(false);
  const [activeStreamingTab, setActiveStreamingTab] = useState<string>("");
  const wasGeneratingRef = useRef<boolean>(false);
  const userSelectedStreamingTabRef = useRef<string | null>(null);

  // When a brand-new generation starts, clear manual tab selection so default staging can begin
  useEffect(() => {
    if (!wasGeneratingRef.current && isGenerating) {
      userSelectedStreamingTabRef.current = null;
      setActiveStreamingTab("");
    }
    wasGeneratingRef.current = isGenerating;
  }, [isGenerating]);

  // Reset tab selection when session changes
  useEffect(() => {
    userSelectedStreamingTabRef.current = null;
    setActiveStreamingTab("");
  }, [session.id]);

  const checkScrollState = useCallback(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const isScrollable = scrollHeight > clientHeight + 30;
    setShowScrollNav(isScrollable);
    setCanScrollTop(scrollTop > 40);

    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setCanScrollBottom(distanceFromBottom > 40);
  }, []);

  useEffect(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    checkScrollState();

    el.addEventListener("scroll", checkScrollState, { passive: true });
    window.addEventListener("resize", checkScrollState);
    return () => {
      el.removeEventListener("scroll", checkScrollState);
      window.removeEventListener("resize", checkScrollState);
    };
  }, [checkScrollState]);

  // Keep scroll navigation buttons state in sync when messages or active steps change (without auto-scrolling)
  useEffect(() => {
    checkScrollState();
  }, [session.messages, activeSteps, checkScrollState]);

  // Derive live Agent Dispatch Plan from activeSteps if not yet stored on session
  const liveDispatchPlan = useMemo(() => {
    if (session.orchestrator_dispatch && session.orchestrator_dispatch.length > 0) {
      return session.orchestrator_dispatch;
    }
    for (let i = activeSteps.length - 1; i >= 0; i--) {
      const d = activeSteps[i].data?.dispatch;
      if (Array.isArray(d) && d.length > 0) return d;
    }
    return undefined;
  }, [session.orchestrator_dispatch, activeSteps]);

  // Derive live Completed Subtask Runs from activeSteps during generation
  const liveProviderRuns = useMemo(() => {
    const runsMap = new Map<string, any>();
    for (const st of activeSteps) {
      if (st.data?.role === "subtask") {
        const branchIdx = st.data.branch_index || 1;
        const k = st.data.provider_role_key || st.data.subtask_id || `${st.provider}_${branchIdx}`;
        if (
          st.step === "completed" ||
          st.data.status === "ok" ||
          st.data.status === "completed" ||
          st.data.status === "error" ||
          st.data.status === "failed" ||
          st.data.answer_md ||
          st.data.answer_markdown
        ) {
          runsMap.set(k, {
            provider: st.provider || st.data.provider,
            branch: st.data.branch,
            branch_index: branchIdx,
            provider_role_key: st.data.provider_role_key || k,
            subtask_id: st.data.subtask_id,
            status: st.data.status || (st.step === "completed" ? "ok" : "completed"),
            elapsed_s: st.data.elapsed_s,
            elapsed_ms: st.data.elapsed_ms,
            answer_md: st.data.answer_md || st.data.answer_markdown,
          });
        }
      }
    }
    return Array.from(runsMap.values());
  }, [activeSteps]);

  // Derive live Agent Overall Status from activeSteps & session
  const liveAgentStatus = useMemo(() => {
    if (session.status === "completed" || session.status === "failed" || session.status === "cancelled") {
      return session.status;
    }
    for (let i = activeSteps.length - 1; i >= 0; i--) {
      const st = activeSteps[i];
      const jobStatus = (st.data as any)?.job_status;
      if (jobStatus && jobStatus !== "running") return jobStatus;
      if (st.data?.role === "lead" || st.message?.includes("Lead Provider")) return "leading";
      if (st.status === "debating" || st.step === "debating" || st.step === "debate_round" || st.data?.stage === "debate") return "debating";
      if (st.step === "fact_checking" || st.data?.role === "fact_checker" || (st.status as string) === "fact_checking") return "fact_checking";
      if (st.data?.role === "subtask" || st.step === "orchestrator_result" || st.data?.dispatch) return "researching";
      if (st.data?.role === "orchestrator") return "orchestrating";
    }
    return session.status || "orchestrating";
  }, [session.status, activeSteps]);

  const scrollToTop = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    }
  };

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    } else {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  // Adjust textarea height automatically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [inputText]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isAgentSession = Boolean(
    session?.job_type === "agent" ||
    Boolean(session?.orchestrator_provider) ||
    session?.messages?.some((m) => m.job_type === "agent" || Boolean(m.orchestrator_provider)) ||
    activeSteps.some((st) => st.data?.role || st.data?.dispatch)
  );

  const selectedCount = selectedProviders.length;

  const handleSend = () => {
    if (!isAgentSession && selectedCount === 0) {
      onOpenProvidersModal();
      return;
    }
    if ((!inputText.trim() && attachedFiles.length === 0) || isGenerating) return;
    let finalPrompt = inputText.trim();
    if (attachedFiles.length > 0) {
      const attachmentsList = attachedFiles.map((f) => `[Tệp đính kèm: ${f.name} (${f.size})]`).join(" ");
      finalPrompt = finalPrompt ? `${finalPrompt}\n\n${attachmentsList}` : attachmentsList;
    }
    onSendMessage(finalPrompt);
    setInputText("");
    setAttachedFiles([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setIsCopied(id);
    setTimeout(() => setIsCopied(null), 2000);
  };

  const currentActiveOptionsId = useMemo(() => {
    if (selectedProviders.some((p) => p.id === activeOptionsProviderId)) {
      return activeOptionsProviderId;
    }
    return selectedProviders[0]?.id || selectedProvider.id;
  }, [selectedProviders, activeOptionsProviderId, selectedProvider.id]);

  const currentActiveProvider = useMemo(() => {
    return selectedProviders.find((p) => p.id === currentActiveOptionsId) || selectedProviders[0] || selectedProvider;
  }, [selectedProviders, currentActiveOptionsId, selectedProvider]);

  return (
    <main className="main-chat-area">
      {/* Top Header Bar */}
      <header className="chat-header">
        <div className="chat-title-group">
          {/* <h1 className="chat-title">{session.title}</h1> */}

          {/* Model Selector Pill / Agent Orchestrator Trigger */}
          <div style={{ position: "relative" }} ref={modelDropdownRef}>
            <button
              className="model-badge-trigger"
              onClick={() => {
                if (isAgentSession && onOpenAgentConfig) {
                  onOpenAgentConfig();
                } else {
                  onOpenProvidersModal();
                }
              }}
              title={isAgentSession ? "Mở cấu hình Deep Research Orchestrator" : "Chọn mô hình / Thêm nhiều nhà cung cấp"}
            >
              {isAgentSession ? (
                <>
                  <span style={{ display: "inline-flex", gap: 5, alignItems: "center" }}>
                    <span style={{ fontSize: 13.5 }}>🤖</span>
                    {session.orchestrator_provider && (
                      <ModelBadgeLogo type={session.orchestrator_provider} size={15} />
                    )}
                    {session.lead_provider && session.lead_provider !== session.orchestrator_provider && (
                      <ModelBadgeLogo type={session.lead_provider} size={15} />
                    )}
                  </span>
                  <span style={{ fontWeight: 600 }}>Deep Research Orchestrator</span>
                  <span
                    style={{
                      fontSize: 9.5,
                      padding: "1px 5px",
                      borderRadius: 4,
                      backgroundColor: "var(--brand-blue-light, #eff6ff)",
                      color: "var(--brand-blue, #2563eb)",
                      fontWeight: 700,
                    }}
                  >
                    Agent
                  </span>
                </>
              ) : selectedCount > 1 ? (
                <>
                  <span style={{ display: "inline-flex", gap: 3, alignItems: "center" }}>
                    {selectedProviders.slice(0, 3).map((p) => (
                      <ModelBadgeLogo key={p.id} type={p.iconType} size={15} />
                    ))}
                  </span>
                  <span>{selectedCount} Models Selected</span>
                </>
              ) : selectedCount === 1 ? (
                <>
                  <ModelBadgeLogo type={(selectedProviders[0] || selectedProvider).iconType} size={16} />
                  <span>{(selectedProviders[0] || selectedProvider).name.split(" ")[0]}</span>
                </>
              ) : (
                <>
                  <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 500 }}>
                    Chưa chọn nhà cung cấp
                  </span>
                </>
              )}
            </button>

            {isModelDropdownOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "115%",
                  left: 0,
                  width: 310,
                  backgroundColor: "#ffffff",
                  borderRadius: "var(--radius-lg)",
                  boxShadow: "var(--shadow-lg)",
                  border: "1px solid var(--border-default)",
                  zIndex: 50,
                  padding: "8px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "4px 8px",
                    borderBottom: "1px solid var(--border-subtle)",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)" }}>
                    ACTIVE MODELS ({selectedCount}/{providers.length})
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setIsModelDropdownOpen(false);
                      onOpenProvidersModal();
                    }}
                    style={{
                      border: "none",
                      background: "none",
                      fontSize: 11,
                      color: "var(--brand-blue)",
                      fontWeight: 600,
                      cursor: "pointer",
                      padding: 0,
                    }}
                  >
                    Mở thư viện ↗
                  </button>
                </div>

                <div style={{ maxHeight: 280, overflowY: "auto", display: "flex", flexDirection: "column", gap: "2px" }}>
                  {providers.map((p) => {
                    const isChecked = selectedProviders.some((sp) => sp.id === p.id);
                    return (
                      <div
                        key={p.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: "6px 8px",
                          borderRadius: "var(--radius-sm)",
                          fontSize: 12.5,
                          backgroundColor: isChecked ? "var(--brand-blue-light)" : "transparent",
                          cursor: "pointer",
                        }}
                        onClick={() => onToggleProvider(p.id)}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => onToggleProvider(p.id)}
                          style={{ cursor: "pointer", accentColor: "var(--brand-blue)" }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <ModelBadgeLogo type={p.iconType} size={18} />
                        <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
                          <span style={{ fontWeight: isChecked ? 600 : 400, color: "var(--text-primary)" }}>
                            {p.name}
                          </span>
                          <span style={{ fontSize: 10.5, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {p.modelName}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Header Actions */}
        <div className="chat-header-actions">
          <button
            className="icon-btn"
            title="Inspect Details / Citations"
            onClick={onToggleRightSidebar}
            aria-label="Toggle Details Panel"
          >
            <SidebarCollapseIcon size={16} />
          </button>
        </div>
      </header>

      {/* Message Stream */}
      <div
        ref={messagesContainerRef}
        className={`messages-scroll-container ${isAgentSession ? "agent-session" : ""}`}
        style={{ paddingBottom: isAgentSession ? "160px" : "250px" }}
      >
        {/* Empty State / Welcome Screen when session has no messages */}
        {session.messages.length === 0 && (
          <WelcomeScreen
            suggestedPrompts={SUGGESTED_PROMPTS}
            selectedCount={selectedCount}
            onOpenProvidersModal={onOpenProvidersModal}
            onSendMessage={onSendMessage}
          />
        )}

        {session.messages.map((msg) => (
          <div key={msg.id} className="message-item animate-fade-in">
            {/* Message Author Header */}
            <div className="message-header">
              {msg.role === "user" ? (
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
                    color: "#ffffff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    fontSize: 12,
                    boxShadow: "var(--shadow-xs)",
                  }}
                >
                  U
                </div>
              ) : (
                <div
                  className="author-avatar-badge"
                  style={{
                    background:
                      selectedProvider.avatarBg ||
                      "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <ModelBadgeLogo type={selectedProvider.iconType} size={18} />
                </div>
              )}
              <span className="author-name">{msg.authorName}</span>
              <span className="message-timestamp">{msg.timestamp}</span>

            </div>

            {/* Multi-provider badges if this message combined multiple models */}
            {msg.providers && msg.providers.length > 0 && (
              <div style={{ display: "flex", gap: 4, marginLeft: 35, flexWrap: 'wrap' }}>
                {msg.providers.map((pId) => {
                  const pInfo = providers.find((p) => p.id === pId);
                  return (
                    <span
                      key={pId}
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        padding: "2px 7px",
                        borderRadius: 4,
                        backgroundColor: "#f1f5f9",
                        color: pInfo?.color || "var(--text-secondary)",
                        border: "1px solid #e2e8f0",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <ModelBadgeLogo type={pInfo?.iconType || pId} size={12} />
                      {pInfo?.name || pId}
                    </span>
                  );
                })}
              </div>
            )}

            {/* Message Body */}
            {msg.role === "user" ? (
              <div className="message-bubble-user">{msg.content}</div>
            ) : (
              <div className="message-card-assistant">
                {/* Assistant Top Tool Badges */}

                {/* Action Required Banner for providers needing login/manual action */}
                {(() => {
                  const neededActions = detectAllProvidersNeedingAction(msg);
                  if (neededActions.length === 0) return null;
                  return (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "6px 0 10px 0" }}>
                      {neededActions.map((act) => (
                        <ProviderActionBanner
                          key={act.provider}
                          provider={act.provider}
                          reason={act.reason}
                          kind={act.kind}
                          jobId={msg.jobId || session.jobId || session.id}
                          onContinue={(prov) => onRetryProvider?.(prov, msg.jobId || session.jobId || session.id)}
                        />
                      ))}
                    </div>
                  );
                })()}

                {/* Agent Orchestrator Multi-Provider Plan & Synthesis Banner */}
                {(msg.job_type === "agent" || session.job_type === "agent") && (
                  <AgentDispatchBanner
                    orchestratorProvider={msg.orchestrator_provider || session.orchestrator_provider}
                    leadProvider={msg.lead_provider || session.lead_provider}
                    tone={msg.tone || session.tone}
                    dispatchPlan={msg.orchestrator_dispatch || session.orchestrator_dispatch}
                    status={
                      msg.content === "you stopped the research, please try again."
                        ? "cancelled"
                        : (msg.factCheckStatus === "unverified" && session.status === "cancelled")
                          ? "cancelled"
                          : "completed"
                    }
                    providerRuns={msg.provider_runs}
                    steps={msg.steps || []}
                    topic={
                      session.messages
                        .slice(0, session.messages.indexOf(msg))
                        .reverse()
                        .find((m) => m.role === "user")?.content ||
                      session.title ||
                      msg.content
                    }
                    message={msg}
                    onSelectThinking={onSelectThinking}
                    enableFactCheck={msg.enable_fact_check ?? session.enable_fact_check}
                    factCheckProvider={msg.fact_check_provider || session.fact_check_provider}
                    factCheckResults={msg.fact_check_results || session.fact_check_results}
                    enableDebate={msg.enable_debate ?? session.enable_debate}
                    debateProvider={msg.debate_provider || session.debate_provider}
                    debateDefenderProvider={msg.debate_defender_provider || session.debate_defender_provider}
                    maxDebateRounds={msg.max_debate_rounds ?? session.max_debate_rounds}
                    debateTranscript={msg.debate_transcript || session.debate_transcript}
                  />
                )}

                {/* Thinking Steps Inspector Button for standard research messages */}
                {msg.steps && msg.steps.length > 0 && !(msg.job_type === "agent" || session.job_type === "agent") && (
                  <div style={{ margin: "4px 0 10px 0" }}>
                    <button
                      type="button"
                      onClick={() => onSelectThinking?.(msg.providers?.[0] || selectedProvider.id, msg)}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "5px 12px",
                        borderRadius: 6,
                        backgroundColor: "#f8fafc",
                        border: "1px solid #e2e8f0",
                        color: "var(--brand-blue, #2563eb)",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      title="Xem các bước suy luận và nhật ký nghiên cứu trong thanh bên phải"
                    >
                      <BrainIcon size={14} color="var(--brand-blue, #2563eb)" />
                      <span>Xem tiến trình suy luận ({msg.steps.length} bước)</span>
                      <ChevronRightIcon size={12} color="var(--brand-blue, #2563eb)" />
                    </button>
                  </div>
                )}

                {/* Matrix / Hybrid Report Section */}
                {msg.report_matrix ? (
                  <div className="message-report-container" style={{ margin: "12px 0" }}>
                    {msg.report_format === "hybrid" ? (
                      <div>
                        <div
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            background: "rgba(255, 255, 255, 0.04)",
                            border: "1px solid rgba(255, 255, 255, 0.08)",
                            borderRadius: 8,
                            padding: 3,
                            marginBottom: 16,
                            gap: 4,
                          }}
                        >
                          <button
                            type="button"
                            onClick={() =>
                              setMessageMatrixTabs((prev) => ({ ...prev, [msg.id]: "matrix" }))
                            }
                            style={{
                              padding: "6px 14px",
                              borderRadius: 6,
                              fontSize: 13,
                              fontWeight: 600,
                              cursor: "pointer",
                              border: "none",
                              transition: "all 0.15s ease",
                              background:
                                (messageMatrixTabs[msg.id] ?? "matrix") === "matrix"
                                  ? "#6366f1"
                                  : "transparent",
                              color:
                                (messageMatrixTabs[msg.id] ?? "matrix") === "matrix"
                                  ? "#fff"
                                  : "var(--text-secondary, #94a3b8)",
                            }}
                          >
                            📊 Ma trận so sánh (Matrix)
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setMessageMatrixTabs((prev) => ({ ...prev, [msg.id]: "narrative" }))
                            }
                            style={{
                              padding: "6px 14px",
                              borderRadius: 6,
                              fontSize: 13,
                              fontWeight: 600,
                              cursor: "pointer",
                              border: "none",
                              transition: "all 0.15s ease",
                              background:
                                (messageMatrixTabs[msg.id] ?? "matrix") === "narrative"
                                  ? "#6366f1"
                                  : "transparent",
                              color:
                                (messageMatrixTabs[msg.id] ?? "matrix") === "narrative"
                                  ? "#fff"
                                  : "var(--text-secondary, #94a3b8)",
                            }}
                          >
                            📝 Báo cáo tự sự (Narrative)
                          </button>
                        </div>

                        {(messageMatrixTabs[msg.id] ?? "matrix") === "matrix" ? (
                          <MatrixReportView report={msg.report_matrix} />
                        ) : (
                          <div className="message-content-body">
                            <MarkdownContent content={msg.content} />
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>
                        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
                          <button
                            type="button"
                            onClick={() =>
                              setMessageMatrixTabs((prev) => ({
                                ...prev,
                                [msg.id]: prev[msg.id] === "narrative" ? "matrix" : "narrative",
                              }))
                            }
                            style={{
                              background: "transparent",
                              border: "1px solid rgba(255, 255, 255, 0.1)",
                              color: "var(--text-secondary, #94a3b8)",
                              borderRadius: 6,
                              padding: "4px 10px",
                              fontSize: 12,
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 5,
                            }}
                          >
                            {messageMatrixTabs[msg.id] === "narrative" ? "📊 Xem dạng Ma trận" : "📄 Xem dạng Markdown"}
                          </button>
                        </div>

                        {messageMatrixTabs[msg.id] === "narrative" ? (
                          <div className="message-content-body">
                            <MarkdownContent content={msg.content} />
                          </div>
                        ) : (
                          <MatrixReportView report={msg.report_matrix} />
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  /* Main Content Body with Full Markdown & Syntax Highlighter */
                  <div className="message-content-body">
                    <MarkdownContent content={msg.content} />
                  </div>
                )}

                {/* Adversarial Debate Transcript (Red Team vs Defender) */}
                {((msg.debate_transcript && msg.debate_transcript.length > 0) ||
                  (msg.id === session.messages[session.messages.length - 1]?.id && session.debate_transcript && session.debate_transcript.length > 0)) && (
                  <div style={{ margin: "14px 0" }}>
                    <DebateTranscript transcript={msg.debate_transcript || session.debate_transcript} defaultExpanded={false} />
                  </div>
                )}

                {/* Citations & Source Links Section */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="message-sources-section">
                    <div className="message-sources-header">
                      <div className="message-sources-title">
                        <span style={{ fontSize: 13, marginRight: 5 }}>📚</span>
                        <span>Nguồn trích dẫn & Tham khảo ({msg.sources.length})</span>
                      </div>
                    </div>
                    <div className="message-sources-grid">
                      {msg.sources.map((src, sIdx) => {
                        let domain = "";
                        try {
                          domain = src.domain || (src.url ? new URL(src.url).hostname.replace(/^www\./, "") : "");
                        } catch {
                          domain = src.url || "source";
                        }
                        const rawTitle = src.title && src.title !== src.url ? src.title : domain;
                        const displayTitle = rawTitle.replace(/^\[[a-zA-Z0-9_\-:]+\]\s*/, "");
                        const loopKey = (src as any).id || src.url || `source-${sIdx}`;
                        return (
                          <a
                            key={loopKey}
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="message-source-chip"
                            title={`${displayTitle}\n${src.url}`}
                          >
                            <span className="message-source-index">{sIdx + 1}</span>
                            <span className="message-source-domain">{domain}</span>
                            <span className="message-source-title">{displayTitle}</span>
                            <ExternalLinkIcon size={12} color="var(--text-muted)" />
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Assistant Footer Row */}
                <div className="assistant-card-footer">
                  <div className="card-footer-icons">
                    <button
                      className="icon-btn"
                      title="Chạy lại nghiên cứu"
                      onClick={() => {
                        const correspondingUserQuery =
                          session.messages
                            .slice(0, session.messages.indexOf(msg))
                            .reverse()
                            .find((m) => m.role === "user")?.content ||
                          session.messages[0]?.content ||
                          "Research more";
                        onSendMessage(correspondingUserQuery);
                      }}
                    >
                      <RefreshIcon size={15} />
                    </button>
                    <button
                      className="icon-btn"
                      title={isCopied === msg.id ? "Đã sao chép!" : "Sao chép câu trả lời"}
                      onClick={() => copyToClipboard(msg.content, msg.id)}
                    >
                      <CopyIcon size={15} />
                    </button>
                    <button
                      className="icon-btn"
                      title={isCopied === `share-${msg.id}` ? "Đã sao chép liên kết hội thoại!" : "Chia sẻ liên kết hội thoại (/chat/...)"}
                      onClick={() => {
                        const targetId = session.jobId || session.id;
                        const shareUrl = typeof window !== "undefined"
                          ? `${window.location.origin}/chat/${targetId}`
                          : `/chat/${targetId}`;
                        navigator.clipboard.writeText(shareUrl);
                        setIsCopied(`share-${msg.id}`);
                        setTimeout(() => setIsCopied(null), 2500);
                      }}
                    >
                      <ShareIcon size={15} color={isCopied === `share-${msg.id}` ? "var(--brand-blue)" : "currentColor"} />
                    </button>
                    <button className="icon-btn" title="Đánh dấu">
                      <BookmarkIcon size={15} />
                    </button>
                    <button className="icon-btn" title="Tùy chọn khác">
                      <MoreHorizontalIcon size={15} />
                    </button>
                  </div>

                  {(!!msg.tokens || !!msg.latencySeconds) && (
                    <span className="card-footer-token">
                      {msg.tokens ? `${msg.tokens} tokens` : ""}
                      {msg.latencySeconds ? ` · ${msg.latencySeconds}s` : ""}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Loading Indicator when bot is generating/thinking */}
        {isGenerating && (
          <div className="message-item animate-fade-in">
            <div className="message-header">
              <div
                className="author-avatar-badge"
                style={{
                  background: selectedProvider.avatarBg,
                  animation: "pulseGlow 1.5s infinite",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <ModelBadgeLogo type={selectedProvider.iconType} size={18} />
              </div>
              <span className="author-name">
                Multi-Model Engine ({selectedProviders.map((p) => p.name).join(", ")})
              </span>
            </div>
            <div
              className="message-card-assistant"
              style={{
                backgroundColor: "#ffffff",
                border: "1.5px solid #bfdbfe",
                boxShadow: "0 4px 12px rgba(37, 99, 235, 0.08)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid #f1f5f9",
                  paddingBottom: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <BrainIcon size={16} color="var(--brand-blue)" />
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--brand-blue)" }}>
                    Đang xử lý {selectedProviders.length > 1 ? 'đa mô hình song song' : ''}...
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      border: "2px solid #bfdbfe",
                      borderTopColor: "var(--brand-blue)",
                      borderRadius: "50%",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                  <span style={{ fontSize: 11, fontWeight: 600, color: "var(--brand-blue)" }}>
                    SSE Live Stream
                  </span>
                </div>
              </div>

              {/* Live Action Required Banner if any provider is blocked during generation */}
              {(() => {
                const liveNeededActions = detectAllProvidersNeedingAction(undefined, activeSteps);
                if (liveNeededActions.length === 0) return null;
                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, margin: "6px 0 8px 0" }}>
                    {liveNeededActions.map((act) => (
                      <ProviderActionBanner
                        key={act.provider}
                        provider={act.provider}
                        reason={act.reason}
                        kind={act.kind}
                        jobId={session.jobId || session.id}
                        onContinue={(prov) => onRetryProvider?.(prov, session.jobId || session.id)}
                      />
                    ))}
                  </div>
                );
              })()}

              {session.job_type === "agent" && (
                <AgentDispatchBanner
                  orchestratorProvider={session.orchestrator_provider}
                  leadProvider={session.lead_provider}
                  tone={session.tone}
                  dispatchPlan={liveDispatchPlan}
                  status={liveAgentStatus}
                  providerRuns={liveProviderRuns}
                  steps={activeSteps}
                  topic={session.title || session.messages[0]?.content}
                  onSelectThinking={onSelectThinking}
                  enableFactCheck={session.enable_fact_check}
                  factCheckProvider={session.fact_check_provider}
                  factCheckResults={session.fact_check_results}
                  enableDebate={session.enable_debate}
                  debateProvider={session.debate_provider}
                  debateDefenderProvider={session.debate_defender_provider}
                  maxDebateRounds={session.max_debate_rounds}
                  debateTranscript={session.debate_transcript}
                />
              )}

              {/* Active Step in message-steps-accordion (Only 1 active step shown) */}
              {(() => {
                const activeStep = activeSteps.length > 0 ? activeSteps[activeSteps.length - 1] : null;
                const activeProvider = activeStep ? extractProvider(activeStep) : "";
                const activePInfo = providers.find((p) => p.id === activeProvider);

                let activeTitle = activeStep?.message || `Khởi tạo phiên nghiên cứu và kết nối tới ${selectedCount} trình duyệt...`;
                let activeDesc = "";

                if (activeStep?.thinkingSteps && activeStep.thinkingSteps.length > 0) {
                  const latestThinking = activeStep.thinkingSteps[activeStep.thinkingSteps.length - 1];
                  if (latestThinking?.title) {
                    const provPrefix = activePInfo?.name ? `${activePInfo.name}: ` : activeProvider ? `${activeProvider.toUpperCase()}: ` : "";
                    activeTitle = `${provPrefix}${latestThinking.title}`;
                    activeDesc = latestThinking.description || "";
                  }
                } else if (activeStep?.data?.thinking_steps && activeStep.data.thinking_steps.length > 0) {
                  const latestThinking = activeStep.data.thinking_steps[activeStep.data.thinking_steps.length - 1];
                  if (latestThinking?.title) {
                    const provPrefix = activePInfo?.name ? `${activePInfo.name}: ` : activeProvider ? `${activeProvider.toUpperCase()}: ` : "";
                    activeTitle = `${provPrefix}${latestThinking.title}`;
                    activeDesc = latestThinking.description || "";
                  }
                }

                return (
                  <div
                    className="message-steps-accordion"
                    style={{
                      backgroundColor: "#f8fafc",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid #e2e8f0",
                      padding: "8px 12px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 12,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          width: 14,
                          height: 14,
                          border: "2px solid #3b82f6",
                          borderTopColor: "transparent",
                          borderRadius: "50%",
                          animation: "spin 0.8s linear infinite",
                          flexShrink: 0,
                        }}
                      />
                      <div style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <BrainIcon size={14} color="var(--brand-blue)" />
                          <span
                            style={{
                              fontSize: 12.5,
                              fontWeight: 600,
                              color: "var(--text-primary)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                            title={activeTitle}
                          >
                            {activeTitle}
                          </span>
                        </div>
                        {activeDesc && (
                          <span
                            style={{
                              fontSize: 11,
                              color: "var(--text-secondary)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              marginTop: 2,
                            }}
                            title={activeDesc}
                          >
                            {activeDesc}
                          </span>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        if (onSelectThinking) {
                          onSelectThinking(activeProvider);
                        } else {
                          onToggleRightSidebar();
                        }
                      }}
                      style={{
                        border: "1px solid #bfdbfe",
                        backgroundColor: "#ffffff",
                        color: "var(--brand-blue)",
                        fontSize: 11.5,
                        fontWeight: 600,
                        padding: "3px 9px",
                        borderRadius: 4,
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        flexShrink: 0,
                        boxShadow: "0 1px 2px rgba(37, 99, 235, 0.05)",
                        transition: "all 0.15s ease",
                      }}
                      title="Xem toàn bộ tiến trình và các bước suy luận chi tiết trong thanh bên phải"
                    >
                      <span>Chi tiết ({activeSteps.length || 1})</span>
                      <ChevronRightIcon size={12} color="var(--brand-blue)" />
                    </button>
                  </div>
                );
              })()}

              {/* Real-time Streaming Response - Reusing real response preview with markdown-rendered-content */}
              {(() => {
                // Check if this active run is an Agent job
                const isAgentRun =
                  session?.job_type === "agent" ||
                  Boolean(session?.orchestrator_provider) ||
                  activeSteps.some((st) => st.data?.role || st.data?.dispatch);

                if (isAgentRun) {
                  const orchProv = normalizeProvider(session?.orchestrator_provider || "gemini");
                  const leadProv = normalizeProvider(session?.lead_provider || "chatgpt");
                  const dispatchPlan = liveDispatchPlan || [];

                  interface AgentStreamCandidate {
                    key: string;
                    label: string;
                    providerId: string;
                    role: "orchestrator" | "subtask" | "lead";
                    roleTag: string;
                  }

                  const candidates: AgentStreamCandidate[] = [];

                  // 1. Orchestrator
                  candidates.push({
                    key: "orchestrator",
                    label: orchProv.toUpperCase(),
                    providerId: orchProv,
                    role: "orchestrator",
                    roleTag: "Orchestrator",
                  });

                  // 2. Subtasks
                  dispatchPlan.forEach((item: any, idx: number) => {
                    const branchIdx = item.branch_index || (idx + 1);
                    const sp = normalizeProvider(item.id);
                    const k = item.provider_role_key || `subtask:${sp}_${branchIdx}`;
                    candidates.push({
                      key: k,
                      label: item.name || sp.toUpperCase(),
                      providerId: sp,
                      role: "subtask",
                      roleTag: `Nhánh #${branchIdx}`,
                    });
                  });

                  // 3. Lead Synthesizer
                  candidates.push({
                    key: "lead",
                    label: leadProv.toUpperCase(),
                    providerId: leadProv,
                    role: "lead",
                    roleTag: "Lead Synthesizer",
                  });

                  // Collect streaming text for each candidate
                  const streamingTextByKey: Record<string, string> = {};
                  for (let i = activeSteps.length - 1; i >= 0; i--) {
                    const st = activeSteps[i];
                    const text = (st.streamingText || (st.data as any)?.streaming_text || "").trim();
                    if (!text) continue;

                    const stKey = st.data?.provider_role_key;
                    const stRole = st.data?.role || ((st.status as string) === "orchestrating" ? "orchestrator" : (st.status as string) === "leading" ? "lead" : undefined);

                    if (stKey && !streamingTextByKey[stKey]) {
                      streamingTextByKey[stKey] = text;
                    }
                    if (stRole === "orchestrator" && !streamingTextByKey["orchestrator"]) {
                      streamingTextByKey["orchestrator"] = text;
                    }
                    if (stRole === "lead" && !streamingTextByKey["lead"]) {
                      streamingTextByKey["lead"] = text;
                    }
                    if (stRole === "subtask") {
                      for (const c of candidates) {
                        if (c.role === "subtask" && !streamingTextByKey[c.key]) {
                          if (st.data?.provider_role_key === c.key ||
                            (st.data?.subtask_id && st.data.subtask_id.includes(c.key)) ||
                            (st.data?.branch && c.label.includes(st.data.branch))) {
                            streamingTextByKey[c.key] = text;
                          }
                        }
                      }
                    }
                  }

                  const hasAnyText = Object.values(streamingTextByKey).some((t) => t.length > 0);
                  if (!hasAnyText && candidates.length === 0) return null;

                  // Pick active tab: priority to user explicit choice, then active stage
                  let defaultKey = "orchestrator";
                  if (liveAgentStatus === "leading") defaultKey = "lead";
                  else if (liveAgentStatus === "researching") {
                    const firstSub = candidates.find((c) => c.role === "subtask" && streamingTextByKey[c.key]);
                    defaultKey = firstSub?.key || candidates.find((c) => c.role === "subtask")?.key || "orchestrator";
                  }

                  const userChoice = userSelectedStreamingTabRef.current;
                  const currentTabKey =
                    userChoice && candidates.some((c) => c.key === userChoice)
                      ? userChoice
                      : activeStreamingTab && candidates.some((c) => c.key === activeStreamingTab)
                        ? activeStreamingTab
                        : defaultKey;

                  const currentCandidate = candidates.find((c) => c.key === currentTabKey) || candidates[0];
                  const currentText = streamingTextByKey[currentCandidate?.key || ""] || "";

                  return (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      <ScrollableTabsRow
                        titlePrefix={
                          <span
                            style={{
                              fontSize: 11.5,
                              fontWeight: 700,
                              color: "var(--text-secondary)",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 5,
                              marginRight: 4,
                              whiteSpace: "nowrap",
                              userSelect: "none",
                            }}
                          >
                            <span>✦</span> Xem trực tiếp:
                          </span>
                        }
                      >
                        {candidates.map((c) => {
                          const isSelected = c.key === currentTabKey;
                          const streamText = streamingTextByKey[c.key] || "";
                          const hasText = streamText.length > 0;

                          return (
                            <button
                              key={c.key}
                              type="button"
                              onClick={() => {
                                userSelectedStreamingTabRef.current = c.key;
                                setActiveStreamingTab(c.key);
                                if (onSelectThinking) {
                                  onSelectThinking(c.key);
                                }
                              }}
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6,
                                padding: "5px 12px",
                                borderRadius: "var(--radius-full)",
                                fontSize: 12,
                                fontWeight: isSelected ? 700 : 500,
                                cursor: "pointer",
                                flexShrink: 0,
                                border: isSelected ? "1.5px solid var(--brand-blue)" : "1px solid #e2e8f0",
                                backgroundColor: isSelected ? "var(--brand-blue-light)" : "#ffffff",
                                color: isSelected ? "var(--brand-blue)" : "var(--text-secondary)",
                                boxShadow: isSelected ? "0 1px 3px rgba(37, 99, 235, 0.12)" : "0 1px 2px rgba(0,0,0,0.03)",
                                transition: "all 0.15s ease",
                                whiteSpace: "nowrap",
                              }}
                              title={`Xem phản hồi thời gian thực của ${c.label} (${c.roleTag})`}
                            >
                              <ModelBadgeLogo providerId={c.providerId} size={15} />
                              <span>{c.label}</span>
                              <span
                                style={{
                                  fontSize: 9.5,
                                  fontWeight: 700,
                                  padding: "1px 5px",
                                  borderRadius: 4,
                                  backgroundColor: c.role === "orchestrator" ? "rgba(124, 58, 237, 0.15)" : c.role === "lead" ? "rgba(16, 163, 127, 0.15)" : "rgba(59, 130, 246, 0.15)",
                                  color: c.role === "orchestrator" ? "#7c3aed" : c.role === "lead" ? "#10a37f" : "#2563eb",
                                }}
                              >
                                {c.roleTag}
                              </span>
                              {hasText ? (
                                <span
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: 4,
                                    fontSize: 10.5,
                                    fontWeight: 600,
                                    padding: "1px 6px",
                                    borderRadius: 10,
                                    backgroundColor: isSelected ? "rgba(37, 99, 235, 0.15)" : "#f1f5f9",
                                    color: isSelected ? "var(--brand-blue)" : "#64748b",
                                  }}
                                >
                                  <span
                                    style={{
                                      width: 5,
                                      height: 5,
                                      borderRadius: "50%",
                                      backgroundColor: "#22c55e",
                                      animation: "pulseGlow 1s infinite",
                                    }}
                                  />
                                  {streamText.length} ký tự
                                </span>
                              ) : (
                                <span
                                  style={{
                                    fontSize: 10,
                                    color: "#94a3b8",
                                    fontStyle: "italic",
                                  }}
                                >
                                  (đang suy nghĩ)
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </ScrollableTabsRow>

                      {/* Selected Provider Streaming Response Body */}
                      {currentText ? (
                        <div className="message-content-body">
                          <MarkdownContent content={currentText} />
                        </div>
                      ) : (
                        <div
                          style={{
                            padding: "20px 16px",
                            display: "flex",
                            alignItems: "center",
                            gap: 12,
                            backgroundColor: "#f8fafc",
                            borderRadius: "var(--radius-md)",
                            border: "1px dashed #cbd5e1",
                            color: "var(--text-secondary)",
                            fontSize: 13,
                          }}
                        >
                          <div
                            style={{
                              width: 16,
                              height: 16,
                              border: "2px solid #3b82f6",
                              borderTopColor: "transparent",
                              borderRadius: "50%",
                              animation: "spin 0.8s linear infinite",
                              flexShrink: 0,
                            }}
                          />
                          <div>
                            <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                              {currentCandidate.label} ({currentCandidate.roleTag})
                            </span>{" "}
                            đang suy nghĩ và thu thập dữ liệu... Câu trả lời sẽ hiển thị tại đây khi bắt đầu sinh phản hồi.
                          </div>
                        </div>
                      )}
                    </div>
                  );
                }

                // Normal / standard chat mode fallback
                const candidateProviders: ProviderInfo[] =
                  selectedProviders.length > 0
                    ? selectedProviders
                    : providers.filter((p) =>
                      activeSteps.some((st) => extractProvider(st) === p.id)
                    );

                // Collect latest streaming text for each provider
                const streamingTextByProvider: Record<string, string> = {};
                for (let i = activeSteps.length - 1; i >= 0; i--) {
                  const st = activeSteps[i];
                  const p = extractProvider(st) || (candidateProviders.length === 1 ? candidateProviders[0].id : "");
                  const text = (st.streamingText || (st.data as any)?.streaming_text || "").trim();
                  if (p && text && !streamingTextByProvider[p]) {
                    streamingTextByProvider[p] = text;
                  }
                }

                const hasAnyStreamingText = Object.values(streamingTextByProvider).some((t) => t.length > 0);
                if (!hasAnyStreamingText) return null;

                // Single provider mode: render directly without tabs
                if (candidateProviders.length <= 1) {
                  const singleProv = candidateProviders[0] || providers[0];
                  const singleText =
                    streamingTextByProvider[singleProv?.id || ""] ||
                    Object.values(streamingTextByProvider)[0] ||
                    "";
                  if (!singleText) return null;

                  return (
                    <div className="message-content-body">
                      <MarkdownContent content={singleText} />
                    </div>
                  );
                }

                // Multiple providers mode: render tab selection on top
                const userChoice = userSelectedStreamingTabRef.current;
                const currentTabProviderId =
                  userChoice && candidateProviders.some((p) => p.id === userChoice)
                    ? userChoice
                    : activeStreamingTab && candidateProviders.some((p) => p.id === activeStreamingTab)
                      ? activeStreamingTab
                      : (candidateProviders.find((p) => streamingTextByProvider[p.id])?.id || candidateProviders[0].id);

                const currentText = streamingTextByProvider[currentTabProviderId] || "";
                const currentProviderInfo =
                  candidateProviders.find((p) => p.id === currentTabProviderId) ||
                  providers.find((p) => p.id === currentTabProviderId);

                return (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {/* Provider Selection Tabs for Real-time Streaming */}
                    <ScrollableTabsRow
                      titlePrefix={
                        <span
                          style={{
                            fontSize: 11.5,
                            fontWeight: 700,
                            color: "var(--text-secondary)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 5,
                            marginRight: 4,
                            whiteSpace: "nowrap",
                            userSelect: "none",
                          }}
                        >
                          <span>✦</span> Xem trực tiếp:
                        </span>
                      }
                    >
                      {candidateProviders.map((p) => {
                        const isSelected = p.id === currentTabProviderId;
                        const streamText = streamingTextByProvider[p.id] || "";
                        const hasText = streamText.length > 0;

                        return (
                          <button
                            key={p.id}
                            type="button"
                            onClick={() => {
                              userSelectedStreamingTabRef.current = p.id;
                              setActiveStreamingTab(p.id);
                              if (onSelectThinking) {
                                onSelectThinking(p.id);
                              }
                            }}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 6,
                              padding: "5px 12px",
                              borderRadius: "var(--radius-full)",
                              fontSize: 12,
                              fontWeight: isSelected ? 700 : 500,
                              cursor: "pointer",
                              flexShrink: 0,
                              border: isSelected ? "1.5px solid var(--brand-blue)" : "1px solid #e2e8f0",
                              backgroundColor: isSelected ? "var(--brand-blue-light)" : "#ffffff",
                              color: isSelected ? "var(--brand-blue)" : "var(--text-secondary)",
                              boxShadow: isSelected ? "0 1px 3px rgba(37, 99, 235, 0.12)" : "0 1px 2px rgba(0,0,0,0.03)",
                              transition: "all 0.15s ease",
                              whiteSpace: "nowrap",
                            }}
                            title={`Xem phản hồi thời gian thực của ${p.name}`}
                          >
                            <ModelBadgeLogo type={p.iconType || p.id} size={15} />
                            <span>{p.name}</span>
                            {hasText ? (
                              <span
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 4,
                                  fontSize: 10.5,
                                  fontWeight: 600,
                                  padding: "1px 6px",
                                  borderRadius: 10,
                                  backgroundColor: isSelected ? "rgba(37, 99, 235, 0.15)" : "#f1f5f9",
                                  color: isSelected ? "var(--brand-blue)" : "#64748b",
                                }}
                              >
                                <span
                                  style={{
                                    width: 5,
                                    height: 5,
                                    borderRadius: "50%",
                                    backgroundColor: "#22c55e",
                                    animation: "pulseGlow 1s infinite",
                                  }}
                                />
                                {streamText.length} ký tự
                              </span>
                            ) : (
                              <span
                                style={{
                                  fontSize: 10,
                                  color: "#94a3b8",
                                  fontStyle: "italic",
                                }}
                              >
                                (đang suy nghĩ)
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </ScrollableTabsRow>

                    {/* Selected Provider Streaming Response Body */}
                    {currentText ? (
                      <div className="message-content-body">
                        <MarkdownContent content={currentText} />
                      </div>
                    ) : (
                      <div
                        style={{
                          padding: "20px 16px",
                          display: "flex",
                          alignItems: "center",
                          gap: 12,
                          backgroundColor: "#f8fafc",
                          borderRadius: "var(--radius-md)",
                          border: "1px dashed #cbd5e1",
                          color: "var(--text-secondary)",
                          fontSize: 13,
                        }}
                      >
                        <div
                          style={{
                            width: 16,
                            height: 16,
                            border: "2px solid #3b82f6",
                            borderTopColor: "transparent",
                            borderRadius: "50%",
                            animation: "spin 0.8s linear infinite",
                            flexShrink: 0,
                          }}
                        />
                        <div>
                          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                            {currentProviderInfo?.name || currentTabProviderId}
                          </span>{" "}
                          đang suy nghĩ và thu thập dữ liệu... Câu trả lời sẽ hiển thị tại đây khi bắt đầu sinh phản hồi.
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Scroll Navigation: Scroll to Top / Bottom */}
      <ScrollNavButtons
        show={showScrollNav}
        canScrollTop={canScrollTop}
        canScrollBottom={canScrollBottom}
        onScrollToTop={scrollToTop}
        onScrollToBottom={scrollToBottom}
      />

      {/* Floating Composer Card */}
      <div className="composer-floating-container">

        <div className="composer-card">
          {/* Attached Files Pill Row */}
          {attachedFiles.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "8px 12px 2px 12px" }}>
              {attachedFiles.map((f) => (
                <div
                  key={f.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "3px 8px",
                    borderRadius: 6,
                    backgroundColor: "#f1f5f9",
                    border: "1px solid #cbd5e1",
                    fontSize: 11.5,
                    color: "var(--text-primary)",
                  }}
                >
                  <span>{f.type === "image" ? "📷" : "📄"}</span>
                  <span style={{ fontWeight: 600 }}>{f.name}</span>
                  <span style={{ color: "var(--text-muted)", fontSize: 10 }}>({f.size})</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(f.id)}
                    style={{
                      border: "none",
                      background: "none",
                      color: "#94a3b8",
                      cursor: "pointer",
                      padding: "0 2px",
                      fontSize: 12,
                      fontWeight: 700,
                    }}
                    title="Xóa tệp đính kèm"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Provider Options Bar for selected provider(s) (Models, Deep Research toggle, Reasoning, DOM Sync) */}
          {/* In an Agent conversation, no model selection is shown at the textbox area */}
          {!isAgentSession && selectedCount === 1 && (
            <div style={{ padding: "0 0 4px 0", borderBottom: "1px solid var(--border-subtle, #f1f5f9)" }}>
              <ProviderOptionsBar
                providerName={(selectedProviders[0] || selectedProvider).name}
                providerId={(selectedProviders[0] || selectedProvider).id}
                capabilities={capabilitiesMap?.[(selectedProviders[0] || selectedProvider).id] || null}
                selection={selectionsMap?.[(selectedProviders[0] || selectedProvider).id] || {}}
                isLoading={loadingProvider === (selectedProviders[0] || selectedProvider).id}
                onUpdateSelection={(updates) => onUpdateSelection?.((selectedProviders[0] || selectedProvider).id, updates)}
                onSyncProvider={() => onSyncProvider?.((selectedProviders[0] || selectedProvider).id)}
              />
            </div>
          )}

          {!isAgentSession && selectedCount > 1 && (
            <div style={{ padding: "6px 12px 4px 12px", borderBottom: "1px solid var(--border-subtle, #f1f5f9)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6, overflowX: "auto" }}>
                <span style={{ fontSize: 10.5, fontWeight: 700, color: "var(--text-muted, #64748b)", whiteSpace: "nowrap" }}>
                  TÙY CHỌN ({selectedCount}):
                </span>
                {selectedProviders.map((sp) => {
                  const isActive = sp.id === currentActiveOptionsId;
                  return (
                    <button
                      key={sp.id}
                      type="button"
                      onClick={() => setActiveOptionsProviderId(sp.id)}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                        padding: "2px 8px",
                        borderRadius: 12,
                        border: `1px solid ${isActive ? "var(--brand-blue, #2563eb)" : "var(--border-subtle, #cbd5e1)"}`,
                        backgroundColor: isActive ? "var(--brand-blue-light, #eff6ff)" : "#ffffff",
                        color: isActive ? "var(--brand-blue, #2563eb)" : "var(--text-secondary, #475569)",
                        fontSize: 11,
                        fontWeight: isActive ? 700 : 500,
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                        transition: "all 0.15s ease",
                      }}
                    >
                      <ModelBadgeLogo type={sp.iconType} size={12} />
                      <span>{sp.name.split(" ")[0]}</span>
                    </button>
                  );
                })}
              </div>
              <ProviderOptionsBar
                providerName={currentActiveProvider.name}
                providerId={currentActiveProvider.id}
                capabilities={capabilitiesMap?.[currentActiveProvider.id] || null}
                selection={selectionsMap?.[currentActiveProvider.id] || {}}
                isLoading={loadingProvider === currentActiveProvider.id}
                onUpdateSelection={(updates) => onUpdateSelection?.(currentActiveProvider.id, updates)}
                onSyncProvider={() => onSyncProvider?.(currentActiveProvider.id)}
              />
            </div>
          )}

          {!isAgentSession && selectedCount === 0 && (
            <div
              style={{
                padding: "6px 12px",
                borderBottom: "1px solid var(--border-subtle, #f1f5f9)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: 11.5,
                color: "var(--text-muted, #64748b)",
                backgroundColor: "#f8fafc",
              }}
            >
              <span>Chưa chọn mô hình AI. Vui lòng chọn mô hình (MiniMax, Gemini, ChatGPT...) để kích hoạt Deep Research và tùy chọn.</span>
              <button
                type="button"
                onClick={onOpenProvidersModal}
                style={{
                  border: "none",
                  backgroundColor: "var(--brand-blue, #2563eb)",
                  color: "#ffffff",
                  borderRadius: 4,
                  padding: "3px 8px",
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                + Chọn mô hình
              </button>
            </div>
          )}

          {/* Voice status banner if recording or transcribing */}
          {(isRecording || isTranscribing || voiceError) && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 12px",
                backgroundColor: isRecording ? "#fef2f2" : isTranscribing ? "#eff6ff" : "#fffbeb",
                borderBottom: "1px solid #f1f5f9",
                fontSize: 12,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {isRecording ? (
                  <>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        backgroundColor: "#ef4444",
                        animation: "micPulse 1.2s infinite",
                      }}
                    />
                    <span style={{ fontWeight: 600, color: "#b91c1c" }}>
                      Đang lắng nghe giọng nói... Bấm biểu tượng micro để dừng và chuyển văn bản.
                    </span>
                  </>
                ) : isTranscribing ? (
                  <>
                    <div
                      style={{
                        width: 10,
                        height: 10,
                        border: "2px solid #93c5fd",
                        borderTopColor: "#2563eb",
                        borderRadius: "50%",
                        animation: "spin 1s linear infinite",
                      }}
                    />
                    <span style={{ fontWeight: 600, color: "#1d4ed8" }}>
                      Đang gửi âm thanh tới backend STT để nhận diện văn bản...
                    </span>
                  </>
                ) : (
                  <span style={{ color: "#b45309" }}>{voiceError}</span>
                )}
              </div>
              {isRecording && (
                <button
                  type="button"
                  onClick={toggleRecording}
                  style={{
                    border: "none",
                    backgroundColor: "#ef4444",
                    color: "#ffffff",
                    borderRadius: 4,
                    padding: "2px 8px",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Dừng thu âm
                </button>
              )}
            </div>
          )}

          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder={
              isRecording
                ? "Đang lắng nghe giọng nói từ micro của bạn..."
                : isAgentSession
                  ? "Đặt câu hỏi nghiên cứu tiếp theo tới hệ thống Deep Research Orchestrator..."
                  : selectedCount === 0
                    ? "Vui lòng chọn nhà cung cấp AI để bắt đầu..."
                    : `Đặt câu hỏi nghiên cứu tới ${selectedCount} mô hình AI (${selectedProviders.map((p) => p.name.split(" ")[0]).join(", ")})...`
            }
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
          />

          {/* Hidden File and Image Inputs */}
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            accept={supportedDataTypes?.supported_mime_types?.join(",") || "*"}
            onChange={(e) => handleFileChange(e, false)}
          />
          <input
            type="file"
            ref={imageInputRef}
            style={{ display: "none" }}
            accept="image/*"
            onChange={(e) => handleFileChange(e, true)}
          />

          <div className="composer-bottom-row">
            <div className="composer-left-actions">
              <button
                className="btn-composer-pill hidden"
                onClick={onOpenProvidersModal}
                title="Mở Thư viện AI Models"
              >
                <LibraryIcon size={15} />
                <span>{selectedCount} Models</span>
              </button>

              {/* Attach File Button - dynamically enabled/disabled */}
              <button
                className="icon-btn"
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={!supportedDataTypes?.file}
                style={{
                  opacity: supportedDataTypes?.file ? 1 : 0.38,
                  cursor: supportedDataTypes?.file ? "pointer" : "not-allowed",
                }}
                title={
                  supportedDataTypes?.file
                    ? `Đính kèm tệp (${supportedDataTypes.supported_mime_types?.slice(0, 4).join(", ") || "PDF, TXT, Code"})`
                    : "Mô hình hiện tại không hỗ trợ đính kèm tệp tin"
                }
                aria-label="Đính kèm tệp"
              >
                <PaperclipIcon size={17} />
              </button>

              {/* Upload Image Button - dynamically enabled/disabled */}
              <button
                className="icon-btn"
                type="button"
                onClick={() => imageInputRef.current?.click()}
                disabled={!supportedDataTypes?.image}
                style={{
                  opacity: supportedDataTypes?.image ? 1 : 0.38,
                  cursor: supportedDataTypes?.image ? "pointer" : "not-allowed",
                }}
                title={
                  supportedDataTypes?.image
                    ? "Tải ảnh lên (Hỗ trợ PNG, JPG, WebP)"
                    : "Mô hình hiện tại không hỗ trợ tải ảnh"
                }
                aria-label="Tải ảnh lên"
              >
                <ImageIcon size={17} />
              </button>

              {/* Microphone / Voice Input Button */}
              <button
                className={`icon-btn ${isRecording ? "active-recording" : ""}`}
                type="button"
                onClick={toggleRecording}
                disabled={!voiceChatSupport?.supported || isTranscribing}
                style={{
                  backgroundColor: isRecording ? "#fee2e2" : isTranscribing ? "#eff6ff" : "transparent",
                  color: isRecording ? "#dc2626" : isTranscribing ? "#2563eb" : "currentColor",
                  border: isRecording ? "1px solid #f87171" : "none",
                  borderRadius: "50%",
                  transition: "all 0.2s ease",
                }}
                title={
                  isRecording
                    ? "Đang thu âm... Bấm để dừng và chuyển thành văn bản"
                    : isTranscribing
                      ? "Đang chuyển thành văn bản qua backend..."
                      : "Nhập liệu bằng giọng nói (Voice Chat STT)"
                }
                aria-label="Nhập liệu giọng nói"
              >
                {isTranscribing ? (
                  <div
                    style={{
                      width: 14,
                      height: 14,
                      border: "2px solid #93c5fd",
                      borderTopColor: "#2563eb",
                      borderRadius: "50%",
                      animation: "spin 1s linear infinite",
                    }}
                  />
                ) : (
                  <MicIcon size={17} color={isRecording ? "#dc2626" : "currentColor"} />
                )}
              </button>
            </div>

            {isGenerating ? (
              <button
                className="btn-composer-send btn-composer-stop"
                onClick={onStopResearch}
                type="button"
                title="Dừng phiên nghiên cứu ngay"
              >
                <StopIcon size={14} />
                <span>Dừng</span>
              </button>
            ) : (
              <button
                className="btn-composer-send"
                onClick={handleSend}
                disabled={!inputText.trim() && attachedFiles.length === 0}
                type="button"
                title="Gửi câu hỏi"
              >
                <SendIcon size={14} />
                <span>Gửi câu hỏi</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
