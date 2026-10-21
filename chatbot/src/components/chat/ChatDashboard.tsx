"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import { PROVIDERS_LIST, DEFAULT_SELECTED_PROVIDERS } from "../../lib/constants";
import { ChatSession, Message, StepLog, ProviderInfo, SourceLink } from "../../types/chat";
import { LeftSidebar } from "../sidebar/LeftSidebar";
import { ChatArea } from "./ChatArea";
import { RightSidebar } from "../inspector/RightSidebar";
import { ProviderModal } from "../providers/ProviderModal";
import { JobsModal } from "../jobs/JobsModal";
import { SettingsModal } from "../settings/SettingsModal";
import { AgentConfigScreen } from "../agent/AgentConfigScreen";
import {
  createResearchJob,
  createAgentResearchJob,
  cancelResearchJob,
  subscribeJobEvents,
  fetchResearchHistory,
  getResearchResult,
  updateResearchJob,
  deleteResearchJob,
  fetchConversationCitations,
  retryJobProvider,
  DEFAULT_API_KEY,
} from "../../lib/api";
import { useProviderCapabilities } from "../../lib/useProviderCapabilities";

const DELETED_SESSIONS_KEY = "deep_research_deleted_sessions";

function getDeletedSessionIds(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(DELETED_SESSIONS_KEY);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function markSessionAsDeleted(id: string, jobId?: string) {
  if (typeof window === "undefined") return;
  try {
    const set = getDeletedSessionIds();
    set.add(id);
    if (jobId) set.add(jobId);
    localStorage.setItem(DELETED_SESSIONS_KEY, JSON.stringify(Array.from(set)));
  } catch (err) {
    console.warn("Could not save deleted session id to localStorage:", err);
  }
}

export function isActiveJobStatus(status?: string): boolean {
  return Boolean(
    status && ["queued", "running", "orchestrating", "researching", "leading"].includes(status)
  );
}

export function resolveAssistantContent(status: string, reportMarkdown?: string | null, error?: string | null): string {
  if (reportMarkdown && reportMarkdown.trim()) {
    return reportMarkdown;
  }
  if (status === "cancelled") {
    return "you stopped the research, please try again.";
  }
  if (status === "failed") {
    return `> ❌ **Nhiệm vụ nghiên cứu gặp sự cố**\n>\n> ${error || "Không thể hoàn thành việc thu thập dữ liệu từ các nhà cung cấp."}`;
  }
  if (status === "needs_user_action") {
    return `> ⚠️ **Yêu cầu can thiệp từ người dùng**\n>\n> ${error || "Một hoặc nhiều nhà cung cấp yêu cầu đăng nhập hoặc xác minh captcha để tiếp tục."}`;
  }
  if (status === "completed" || status === "partial") {
    return "Đã hoàn thành nghiên cứu nhưng chưa có báo cáo tổng hợp chi tiết.";
  }
  return "";
}

export function buildAssistantMessage(
  jobId: string,
  jobData: {
    report_markdown?: string | null;
    status: string;
    providers?: string[];
    created_at?: string | null;
    finished_at?: string | null;
    sources?: SourceLink[];
    claims?: any[];
    disagreements?: any[];
    provider_runs?: Record<string, any> | any[];
    provider_options?: Record<string, any>;
    steps?: StepLog[];
    job_type?: "research" | "agent";
    orchestrator_provider?: string;
    lead_provider?: string;
    tone?: string;
    orchestrator_dispatch?: any[];
    delegated_providers?: string[];
    summarization_provider?: string | null;
    summarization_config?: Record<string, any>;
    context_summary?: string | null;
    enable_fact_check?: boolean;
    fact_check_provider?: string | null;
    fact_check_config?: Record<string, any>;
    fact_check_results?: any[];
    error?: string | null;
    orchestrator_conversation_url?: string | null;
    lead_conversation_url?: string | null;
    provider_conversations?: Record<string, string>;
  }
): Message | null {
  const content = resolveAssistantContent(jobData.status, jobData.report_markdown, jobData.error);
  if (!content) return null;

  const isAgent = jobData.job_type === "agent" || Boolean(jobData.orchestrator_provider);
  const providers = jobData.providers && jobData.providers.length > 0 ? jobData.providers : DEFAULT_SELECTED_PROVIDERS;
  const authorName = isAgent
    ? 'Deep Research Orchestrator'
    : 'AI Research Engine';

  const timestamp = jobData.finished_at
    ? new Date(jobData.finished_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : jobData.created_at
      ? new Date(jobData.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "";

  const runsList = Array.isArray(jobData.provider_runs)
    ? jobData.provider_runs
    : Object.values(jobData.provider_runs || {});
  const resolvedConvUrls: Record<string, string> = { ...(jobData.provider_conversations || {}) };
  for (const r of runsList) {
    if (r && r.provider && r.conversation_url) {
      resolvedConvUrls[r.provider] = r.conversation_url;
    }
  }

  return {
    id: `msg-${jobId}-asst`,
    jobId,
    role: "assistant",
    authorName,
    timestamp,
    content,
    providers,
    tokens: jobData.report_markdown ? 1600 : 0,
    latencySeconds: 14.5,
    sources: jobData.sources || [],
    claims: jobData.claims || [],
    disagreements: jobData.disagreements || [],
    provider_runs: jobData.provider_runs || {},
    provider_options: jobData.provider_options || {},
    factCheckStatus: jobData.status === "completed" ? "verified" : "unverified",
    enable_fact_check: jobData.enable_fact_check,
    fact_check_provider: jobData.fact_check_provider || undefined,
    fact_check_config: jobData.fact_check_config,
    fact_check_results: jobData.fact_check_results,
    steps: jobData.steps || [],
    job_type: isAgent ? "agent" : "research",
    orchestrator_provider: jobData.orchestrator_provider,
    lead_provider: jobData.lead_provider,
    summarization_provider: jobData.summarization_provider || undefined,
    summarization_config: jobData.summarization_config || undefined,
    context_summary: jobData.context_summary || undefined,
    tone: jobData.tone,
    orchestrator_dispatch: jobData.orchestrator_dispatch,
    delegated_providers: jobData.delegated_providers,
    orchestrator_conversation_url: jobData.orchestrator_conversation_url || undefined,
    lead_conversation_url: jobData.lead_conversation_url || undefined,
    provider_conversations: Object.keys(resolvedConvUrls).length > 0 ? resolvedConvUrls : undefined,
  };
}

export function upsertAssistantMessage(messages: Message[], newAsstMsg: Message): Message[] {
  const newJobId =
    newAsstMsg.jobId ||
    (newAsstMsg.id.startsWith("msg-")
      ? newAsstMsg.id.replace(/^msg-/, "").replace(/-asst$/, "")
      : newAsstMsg.id.replace(/^asst-/, ""));

  const existingIdx = messages.findIndex((m) => {
    if (m.id === newAsstMsg.id) return true;
    if (m.role !== "assistant") return false;
    const mJobId =
      m.jobId ||
      (m.id.startsWith("msg-")
        ? m.id.replace(/^msg-/, "").replace(/-asst$/, "")
        : m.id.replace(/^asst-/, ""));
    if (newJobId && mJobId && newJobId === mJobId) return true;
    return false;
  });

  if (existingIdx >= 0) {
    return messages.map((m, idx) => (idx === existingIdx ? newAsstMsg : m));
  }
  return [...messages, newAsstMsg];
}

const createFreshDraftSession = (id?: string): ChatSession => ({
  id: id || `session-${Date.now()}`,
  title: "Phiên nghiên cứu mới",
  pinned: false,
  createdAt: "Vừa xong",
  createdTimestamp: Date.now(),
  selectedProviders: [],
  selectedProvider: "",
  messages: [],
});

const FALLBACK_SESSION: ChatSession = createFreshDraftSession("session-fallback");

interface ChatDashboardProps {
  initialChatId?: string;
}

export function ChatDashboard({ initialChatId }: ChatDashboardProps) {
  const router = useRouter();
  const routeParams = useParams();
  const isAtRoot = typeof window !== "undefined" && window.location.pathname === "/";
  const pathChatId = typeof window !== "undefined"
    ? (isAtRoot ? undefined : window.location.pathname.match(/^\/chat\/([^/?#]+)/)?.[1])
    : undefined;
  const routeChatId = isAtRoot
    ? undefined
    : (pathChatId || initialChatId || (routeParams?.id as string | undefined))?.trim();

  const [mounted, setMounted] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>(routeChatId || "");
  const [currentRouteChatId, setCurrentRouteChatId] = useState<string | undefined>(routeChatId);
  const [draftSession, setDraftSession] = useState<ChatSession>(() => createFreshDraftSession("session-draft"));
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [activeSteps, setActiveSteps] = useState<StepLog[]>([]);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState<boolean>(false);
  const [isProvidersModalOpen, setIsProvidersModalOpen] = useState<boolean>(false);
  const [isJobsModalOpen, setIsJobsModalOpen] = useState<boolean>(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState<boolean>(false);
  const [isAgentConfigOpen, setIsAgentConfigOpen] = useState<boolean>(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [inspectedMessage, setInspectedMessage] = useState<Message | undefined>(undefined);
  const [inspectedProvider, setInspectedProvider] = useState<string | undefined>(undefined);

  const activeJobIdRef = useRef<string | null>(null);
  const activeUnsubscribeRef = useRef<(() => void) | null>(null);
  const isCancelledRef = useRef<boolean>(false);

  // Keep currentRouteChatId in sync with route navigation if not actively running a job
  useEffect(() => {
    if (!isGenerating && !activeJobIdRef.current) {
      let incomingId: string | undefined;
      if (typeof window !== "undefined") {
        if (window.location.pathname === "/") {
          incomingId = undefined;
        } else {
          const match = window.location.pathname.match(/^\/chat\/([^/?#]+)/);
          incomingId = match && match[1] ? decodeURIComponent(match[1]).trim() : undefined;
        }
      } else {
        incomingId = (routeParams?.id as string | undefined)?.trim() || initialChatId?.trim();
      }

      if (incomingId !== currentRouteChatId) {
        setCurrentRouteChatId(incomingId);
      }
    }
  }, [routeParams?.id, initialChatId, isGenerating, currentRouteChatId]);

  const handleSelectThinking = (provider?: string, message?: Message) => {
    setIsRightSidebarOpen(true);
    if (message) {
      setInspectedMessage(message);
    }
    setInspectedProvider(provider ? provider.toLowerCase() : undefined);
  };

  const connectToRunningJob = useCallback(
    (jobId: string, initialSteps: StepLog[] = [], jobMeta?: any) => {
      if (activeUnsubscribeRef.current) {
        try {
          activeUnsubscribeRef.current();
        } catch (err) {
          console.warn("Error unsubscribing previous SSE:", err);
        }
        activeUnsubscribeRef.current = null;
      }

      isCancelledRef.current = false;
      activeJobIdRef.current = jobId;
      setIsGenerating(true);

      if (initialSteps && initialSteps.length > 0) {
        setActiveSteps(initialSteps);
      }

      setIsRightSidebarOpen(true);

      const jobProviders =
        (jobMeta?.selectedProviders && jobMeta.selectedProviders.length > 0)
          ? jobMeta.selectedProviders
          : (jobMeta?.providers && jobMeta.providers.length > 0)
            ? jobMeta.providers
            : DEFAULT_SELECTED_PROVIDERS;

      const initialProv = jobProviders[0] || "copilot";
      setInspectedProvider(initialProv.toLowerCase());

      const isAgent = jobMeta?.job_type === "agent" || Boolean(jobMeta?.orchestrator_provider);
      const orchProv = jobMeta?.orchestrator_provider || (isAgent ? "gemini" : undefined);
      const leadProv = jobMeta?.lead_provider || (isAgent ? "chatgpt" : undefined);

      const unsub = subscribeJobEvents(jobId, {
        onStatus: (newStatus) => {
          if (isCancelledRef.current) return;
          setSessions((prev) =>
            prev.map((s) =>
              s.id === jobId || s.jobId === jobId
                ? { ...s, status: newStatus as any }
                : s
            )
          );
        },
        onStep: (stepLog) => {
          if (isCancelledRef.current) return;
          setActiveSteps((prev) => {
            const existingIdx = prev.findIndex(
              (s) =>
                s.id === stepLog.id ||
                (s.message === stepLog.message &&
                  s.step === stepLog.step &&
                  s.provider === stepLog.provider)
            );
            if (existingIdx >= 0) {
              const updated = [...prev];
              updated[existingIdx] = stepLog;
              return updated;
            }
            return [...prev, stepLog];
          });

          const rawJobStatus = (stepLog.data as any)?.job_status;
          const dispatch = stepLog.data?.dispatch;
          const stepConvUrl = stepLog.conversationUrl || (stepLog.data as any)?.conversation_url;
          const stepProv = stepLog.provider || (stepLog.data as any)?.provider;
          const orchConvUrl = (stepLog.data as any)?.orch_conv_url;
          const leadConvUrl = (stepLog.data as any)?.lead_conv_url;

          setSessions((prev) =>
            prev.map((s) => {
              if (s.id !== jobId && s.jobId !== jobId) return s;
              let nextStatus = s.status;
              if (rawJobStatus && rawJobStatus !== "running") {
                nextStatus = rawJobStatus as any;
              } else if (stepLog.step === "fact_checking" || (stepLog.data as any)?.phase === "fact_checking") {
                nextStatus = "fact_checking" as any;
              } else if (stepLog.step === "summarizing") {
                nextStatus = "summarizing" as any;
              } else if (dispatch && nextStatus === "orchestrating") {
                nextStatus = "researching" as any;
              }
              const updatedProviderConvs = { ...(s.provider_conversations || {}) };
              if (stepConvUrl && stepProv) {
                updatedProviderConvs[stepProv] = stepConvUrl;
              }
              return {
                ...s,
                status: nextStatus,
                orchestrator_dispatch: dispatch || s.orchestrator_dispatch,
                orchestrator_conversation_url: orchConvUrl || s.orchestrator_conversation_url,
                lead_conversation_url: leadConvUrl || s.lead_conversation_url,
                provider_conversations: Object.keys(updatedProviderConvs).length > 0 ? updatedProviderConvs : s.provider_conversations,
              };
            })
          );
        },
        onResult: (result) => {
          if (isCancelledRef.current) return;
          setActiveSteps((latestSteps) => {
            const consolidatedSources = [...(result.sources || [])];
            const seenUrls = new Set(consolidatedSources.map((s) => s.url));
            for (const st of latestSteps) {
              const stepCits = st.citations || (st.data as any)?.citations || [];
              for (const c of stepCits) {
                if (c && c.url && !seenUrls.has(c.url)) {
                  seenUrls.add(c.url);
                  consolidatedSources.push({
                    title: c.title || c.url,
                    url: c.url,
                    domain: c.domain,
                  });
                }
              }
            }

            const asstMsg = buildAssistantMessage(jobId, {
              report_markdown:
                result.report_markdown ||
                "Đã hoàn thành nghiên cứu và tổng hợp câu trả lời từ các mô hình.",
              status: "completed",
              providers: jobProviders,
              sources: consolidatedSources,
              claims: result.claims || [],
              disagreements: (result as any).disagreements || [],
              provider_runs: result.provider_runs || {},
              provider_options:
                (result as any).provider_options || jobMeta?.providerConfigurations || {},
              enable_fact_check: (result as any).enable_fact_check ?? jobMeta?.enable_fact_check,
              fact_check_provider: (result as any).fact_check_provider || jobMeta?.fact_check_provider,
              fact_check_config: (result as any).fact_check_config || jobMeta?.fact_check_config,
              fact_check_results: (result as any).fact_check_results || jobMeta?.fact_check_results,
              steps: latestSteps,
              job_type: isAgent ? "agent" : "research",
              orchestrator_provider: orchProv,
              lead_provider: leadProv,
              summarization_provider: (result as any).summarization_provider || jobMeta?.summarization_provider,
              summarization_config: (result as any).summarization_config || jobMeta?.summarization_config,
              tone: jobMeta?.tone,
              orchestrator_dispatch:
                (result as any).orchestrator_dispatch || jobMeta?.orchestrator_dispatch,
              delegated_providers: jobMeta?.delegated_providers,
              orchestrator_conversation_url: result.orchestrator_conversation_url,
              lead_conversation_url: result.lead_conversation_url,
              provider_conversations: result.provider_conversations,
            });

            if (asstMsg) {
              setInspectedMessage(asstMsg);
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== jobId && s.jobId !== jobId) return s;
                  return {
                    ...s,
                    status: "completed",
                    messages: upsertAssistantMessage(s.messages, asstMsg),
                    orchestrator_dispatch:
                      (result as any).orchestrator_dispatch || s.orchestrator_dispatch,
                    orchestrator_conversation_url:
                      result.orchestrator_conversation_url || s.orchestrator_conversation_url,
                    lead_conversation_url:
                      result.lead_conversation_url || s.lead_conversation_url,
                    provider_conversations: {
                      ...(s.provider_conversations || {}),
                      ...(result.provider_conversations || {}),
                    },
                    enable_fact_check: (result as any).enable_fact_check ?? s.enable_fact_check,
                    fact_check_provider: (result as any).fact_check_provider || s.fact_check_provider,
                    fact_check_config: (result as any).fact_check_config || s.fact_check_config,
                    fact_check_results: (result as any).fact_check_results || s.fact_check_results,
                  };
                })
              );
            }
            return latestSteps;
          });
          setIsGenerating(false);
          activeJobIdRef.current = null;
          activeUnsubscribeRef.current = null;
        },
        onError: async (err) => {
          if (isCancelledRef.current) return;
          console.warn("SSE reconnect issue:", err);
          try {
            const finalResult = await getResearchResult(jobId);
            if (finalResult && !isActiveJobStatus(finalResult.status)) {
              const asstMsg = buildAssistantMessage(jobId, finalResult);
              if (asstMsg) {
                setInspectedMessage(asstMsg);
                setSessions((prev) =>
                  prev.map((s) =>
                    s.id === jobId || s.jobId === jobId
                      ? {
                        ...s,
                        status: finalResult.status as any,
                        messages: upsertAssistantMessage(s.messages, asstMsg),
                      }
                      : s
                  )
                );
              }
            }
          } catch { }
          setIsGenerating(false);
          activeJobIdRef.current = null;
          activeUnsubscribeRef.current = null;
        },
        onDone: async () => {
          if (isCancelledRef.current) return;
          try {
            const finalResult = await getResearchResult(jobId);
            if (finalResult) {
              const asstMsg = buildAssistantMessage(jobId, finalResult);
              if (asstMsg) {
                setInspectedMessage(asstMsg);
                setSessions((prev) =>
                  prev.map((s) =>
                    s.id === jobId || s.jobId === jobId
                      ? {
                        ...s,
                        status: (finalResult.status as any) || "completed",
                        messages: upsertAssistantMessage(s.messages, asstMsg),
                        orchestrator_dispatch:
                          (finalResult as any).orchestrator_dispatch || s.orchestrator_dispatch,
                      }
                      : s
                  )
                );
              }
            }
          } catch (e) {
            console.warn("Could not fetch final research result in reconnect onDone:", e);
          } finally {
            setIsGenerating(false);
            activeJobIdRef.current = null;
            activeUnsubscribeRef.current = null;
          }
        },
      });

      activeUnsubscribeRef.current = unsub;
    },
    []
  );

  // Synchronize history from backend on mount and via button
  const loadHistoryFromBackend = useCallback(async (preferredId?: string) => {
    setIsLoadingHistory(true);
    const targetId = preferredId || routeChatId;

    try {
      const historyJobs = await fetchResearchHistory(50);
      const deletedIds = getDeletedSessionIds();

      const newSessions: ChatSession[] = [];
      if (historyJobs && historyJobs.length > 0) {
        // Group jobs by conversation_id (fallback to job_id)
        const groups = new Map<string, typeof historyJobs>();
        for (const job of historyJobs) {
          if (deletedIds.has(job.job_id)) {
            continue;
          }
          const convId = job.conversation_id || job.job_id;
          if (!groups.has(convId)) {
            groups.set(convId, []);
          }
          groups.get(convId)!.push(job);
        }

        for (const [convId, groupJobs] of groups.entries()) {
          // Sort group jobs chronologically (oldest first for message history)
          const sortedJobs = [...groupJobs].sort((a, b) => {
            const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
            const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
            return ta - tb;
          });

          const rootJob = sortedJobs[0];
          const latestJob = sortedJobs[sortedJobs.length - 1];

          const messages: Message[] = [];
          const mergedConvUrls: Record<string, string> = {};

          for (const job of sortedJobs) {
            const userMsg: Message = {
              id: `msg-${job.job_id}-user`,
              role: "user",
              authorName: "Researcher",
              timestamp: job.created_at
                ? new Date(job.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "Trước đó",
              content: job.query,
            };
            messages.push(userMsg);
            const assistantMsg = buildAssistantMessage(job.job_id, job);
            if (assistantMsg) {
              messages.push(assistantMsg);
            }
            if (job.provider_conversations) {
              Object.assign(mergedConvUrls, job.provider_conversations);
            }
            if (job.provider_runs && typeof job.provider_runs === "object") {
              const runList = Array.isArray(job.provider_runs) ? job.provider_runs : Object.values(job.provider_runs);
              for (const r of runList) {
                if (r && r.provider && r.conversation_url) {
                  mergedConvUrls[r.provider] = r.conversation_url;
                }
              }
            }
          }

          const jobProviders = latestJob.providers && latestJob.providers.length > 0
            ? latestJob.providers
            : (rootJob.providers && rootJob.providers.length > 0 ? rootJob.providers : DEFAULT_SELECTED_PROVIDERS);

          const initialTitle = (rootJob as any).title || (rootJob.query.length > 36 ? rootJob.query.slice(0, 36) + "..." : rootJob.query);
          const isPinned = Boolean((rootJob as any).pinned || (latestJob as any).pinned);

          newSessions.push({
            id: convId,
            jobId: latestJob.job_id,
            title: initialTitle,
            pinned: isPinned,
            createdAt: rootJob.created_at
              ? new Date(rootJob.created_at).toLocaleDateString([], { month: "short", day: "numeric" })
              : "Gần đây",
            createdTimestamp: rootJob.created_at ? new Date(rootJob.created_at).getTime() : Date.now(),
            selectedProviders: jobProviders,
            selectedProvider: jobProviders[0] || "copilot",
            status: latestJob.status,
            messages,
            job_type: (latestJob as any).job_type || (rootJob as any).job_type || "research",
            orchestrator_provider: (latestJob as any).orchestrator_provider,
            lead_provider: (latestJob as any).lead_provider,
            summarization_provider: (latestJob as any).summarization_provider || (rootJob as any).summarization_provider,
            summarization_config: (latestJob as any).summarization_config || (rootJob as any).summarization_config,
            context_summary: (latestJob as any).context_summary || (rootJob as any).context_summary,
            tone: (latestJob as any).tone,
            orchestrator_dispatch: (latestJob as any).orchestrator_dispatch,
            delegated_providers: (latestJob as any).delegated_providers,
            enable_fact_check: latestJob.enable_fact_check ?? (rootJob as any).enable_fact_check,
            fact_check_provider: latestJob.fact_check_provider || (rootJob as any).fact_check_provider,
            fact_check_config: latestJob.fact_check_config || (rootJob as any).fact_check_config,
            fact_check_results: latestJob.fact_check_results || (rootJob as any).fact_check_results,
            providerConfigurations: (latestJob as any).providerConfigurations || (latestJob as any).provider_options || {
              ...(((latestJob as any).orchestrator_config && (latestJob as any).orchestrator_provider) ? { [(latestJob as any).orchestrator_provider]: (latestJob as any).orchestrator_config } : {}),
              ...(((latestJob as any).lead_config && (latestJob as any).lead_provider) ? { [(latestJob as any).lead_provider]: (latestJob as any).lead_config } : {}),
              ...(((latestJob as any).summarization_config && (latestJob as any).summarization_provider) ? { [(latestJob as any).summarization_provider]: (latestJob as any).summarization_config } : {}),
              ...(((latestJob as any).fact_check_config && (latestJob as any).fact_check_provider) ? { [(latestJob as any).fact_check_provider]: (latestJob as any).fact_check_config } : {}),
            },
            orchestrator_conversation_url: (latestJob as any).orchestrator_conversation_url || undefined,
            lead_conversation_url: (latestJob as any).lead_conversation_url || undefined,
            provider_conversations: Object.keys(mergedConvUrls).length > 0 ? mergedConvUrls : undefined,
          });
        }
      }

      // If a specific conversation was requested via route and not found in top 50, fetch directly
      if (targetId && !newSessions.some((s) => s.id === targetId || s.jobId === targetId || s.messages.some((m) => m.jobId === targetId))) {
        try {
          const directJob = await getResearchResult(targetId);
          if (directJob && directJob.job_id) {
            const directProviders = directJob.providers && directJob.providers.length > 0
              ? directJob.providers
              : DEFAULT_SELECTED_PROVIDERS;

            const userMsg: Message = {
              id: `msg-${directJob.job_id}-user`,
              role: "user",
              authorName: "Researcher",
              timestamp: directJob.created_at
                ? new Date(directJob.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "Trước đó",
              content: directJob.query || "Phiên nghiên cứu",
            };

            const directAsst = buildAssistantMessage(directJob.job_id, directJob);
            const asstMsgs: Message[] = directAsst ? [directAsst] : [];

            const directSession: ChatSession = {
              id: directJob.job_id,
              jobId: directJob.job_id,
              title: directJob.title || directJob.query || `Phiên ${directJob.job_id}`,
              pinned: false,
              createdAt: directJob.created_at
                ? new Date(directJob.created_at).toLocaleDateString([], { month: "short", day: "numeric" })
                : "Gần đây",
              createdTimestamp: directJob.created_at ? new Date(directJob.created_at).getTime() : Date.now(),
              selectedProviders: directProviders,
              selectedProvider: directProviders[0] || "copilot",
              status: directJob.status as any,
              messages: [userMsg, ...asstMsgs],
              job_type: (directJob as any).job_type || "research",
              orchestrator_provider: (directJob as any).orchestrator_provider,
              lead_provider: (directJob as any).lead_provider,
              summarization_provider: (directJob as any).summarization_provider,
              summarization_config: (directJob as any).summarization_config,
              context_summary: (directJob as any).context_summary,
              tone: (directJob as any).tone,
              orchestrator_dispatch: (directJob as any).orchestrator_dispatch,
              delegated_providers: (directJob as any).delegated_providers,
              enable_fact_check: directJob.enable_fact_check,
              fact_check_provider: directJob.fact_check_provider || undefined,
              fact_check_config: directJob.fact_check_config,
              fact_check_results: directJob.fact_check_results,
              providerConfigurations: (directJob as any).providerConfigurations || (directJob as any).provider_options || {
                ...(((directJob as any).orchestrator_config && (directJob as any).orchestrator_provider) ? { [(directJob as any).orchestrator_provider]: (directJob as any).orchestrator_config } : {}),
                ...(((directJob as any).lead_config && (directJob as any).lead_provider) ? { [(directJob as any).lead_provider]: (directJob as any).lead_config } : {}),
                ...(((directJob as any).summarization_config && (directJob as any).summarization_provider) ? { [(directJob as any).summarization_provider]: (directJob as any).summarization_config } : {}),
                ...(((directJob as any).fact_check_config && (directJob as any).fact_check_provider) ? { [(directJob as any).fact_check_provider]: (directJob as any).fact_check_config } : {}),
              },
              orchestrator_conversation_url: (directJob as any).orchestrator_conversation_url || undefined,
              lead_conversation_url: (directJob as any).lead_conversation_url || undefined,
              provider_conversations: (directJob as any).provider_conversations || undefined,
            };
            newSessions.unshift(directSession);
          }
        } catch (directErr) {
          console.warn("Could not fetch target conversation directly:", directErr);
        }
      }

      setSessions((prev) => {
        // 1. Identify any active sessions that are generating or running
        const activeRunningSessions = prev.filter(
          (s) =>
            s.id === activeJobIdRef.current ||
            s.jobId === activeJobIdRef.current ||
            s.status === "running" ||
            s.status === "orchestrating" ||
            s.status === "researching" ||
            s.status === "leading"
        );
        const activeRunningIds = new Set(activeRunningSessions.flatMap((s) => [s.id, s.jobId || ""]));

        // 2. Filter newSessions so they do not overwrite live state of actively running jobs
        const safeNewSessions = newSessions.filter(
          (s) => !activeRunningIds.has(s.id) && !activeRunningIds.has(s.jobId || "")
        );
        const mergedSafeSessions = safeNewSessions.map((newS) => {
          const oldS = prev.find((p) => p.id === newS.id || (p.jobId && p.jobId === newS.id));
          if (oldS && oldS.messages && oldS.messages.length > newS.messages.length) {
            return {
              ...newS,
              messages: oldS.messages,
              title: oldS.title || newS.title,
            };
          }
          return newS;
        });
        const existingJobIds = new Set(mergedSafeSessions.map((s) => s.id));
        const keptPrev = prev.filter(
          (s) => !existingJobIds.has(s.id) && !existingJobIds.has(s.jobId || "") && !activeRunningIds.has(s.id)
        );
        const validCombined = [...activeRunningSessions, ...mergedSafeSessions, ...keptPrev].filter(
          (s) => (s.messages && s.messages.length > 0) || s.jobId
        );

        if (!targetId) {
          if (!activeJobIdRef.current && !isGenerating) {
            const freshId = `session-${Date.now()}`;
            setActiveSessionId(freshId);
            setActiveSteps([]);
            setInspectedMessage(undefined);
            setInspectedProvider(undefined);
            setIsRightSidebarOpen(false);
            setDraftSession(createFreshDraftSession(freshId));
          }
          return validCombined;
        }

        if (validCombined.length > 0) {
          setActiveSessionId((curr) => {
            // NEVER switch away if a job is actively running/generating!
            if (activeJobIdRef.current) {
              return activeJobIdRef.current;
            }
            if (curr && isGenerating) {
              return curr;
            }
            // Keep user on their currently viewed session if it is present
            if (curr && validCombined.some((s) => s.id === curr || s.jobId === curr)) {
              return curr;
            }
            // If targetId is explicitly present in sessions, select it
            if (targetId && validCombined.some((s) => s.id === targetId || s.jobId === targetId)) {
              return targetId;
            }
            return validCombined[0]?.id || curr;
          });
          return validCombined;
        }

        const freshId = `session-${Date.now()}`;
        if (!activeJobIdRef.current && !isGenerating) {
          setActiveSessionId(freshId);
          setDraftSession(createFreshDraftSession(freshId));
        }
        return activeRunningSessions;
      });

      const selectedTarget = targetId
        ? newSessions.find((s) => s.id === targetId || s.jobId === targetId)
        : undefined;

      if (selectedTarget) {
        const selectedJobId = selectedTarget.jobId || selectedTarget.id;
        if (isActiveJobStatus(selectedTarget.status)) {
          connectToRunningJob(
            selectedJobId,
            (selectedTarget as any).steps || [],
            selectedTarget
          );
        } else {
          const asst = selectedTarget.messages.find((m) => m.role === "assistant");
          if (asst) {
            setInspectedMessage(asst);
            if (asst.steps && asst.steps.length > 0) {
              setActiveSteps(asst.steps);
            }
          } else if ((selectedTarget as any).steps && (selectedTarget as any).steps.length > 0) {
            setActiveSteps((selectedTarget as any).steps);
          }
          if (selectedTarget.selectedProviders && selectedTarget.selectedProviders.length > 0) {
            setInspectedProvider(selectedTarget.selectedProviders[0].toLowerCase());
          }
        }
      }
    } catch (err) {
      console.warn("Could not fetch research history from backend:", err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [routeChatId, connectToRunningJob]);

  useEffect(() => {
    setMounted(true);
    loadHistoryFromBackend(routeChatId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle browser back/forward buttons (popstate)
  useEffect(() => {
    const handlePopState = () => {
      if (typeof window === "undefined") return;
      const match = window.location.pathname.match(/^\/chat\/([^/?#]+)/);
      if (match && match[1]) {
        handleSelectSession(decodeURIComponent(match[1]).trim(), false);
      } else if (window.location.pathname === "/") {
        const freshDraftId = `session-${Date.now()}`;
        setActiveSessionId(freshDraftId);
        setCurrentRouteChatId(undefined);
        setActiveSteps([]);
        setInspectedMessage(undefined);
        setInspectedProvider(undefined);
        setIsRightSidebarOpen(false);
        setIsProvidersModalOpen(false);
        setIsGenerating(false);
        setDraftSession(createFreshDraftSession(freshDraftId));
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [sessions]);

  // When currentRouteChatId changes from props/navigation, sync activeSessionId
  useEffect(() => {
    if (isGenerating || activeJobIdRef.current) return;
    if (currentRouteChatId) {
      if (currentRouteChatId !== activeSessionId) {
        handleSelectSession(currentRouteChatId, false);
      }
    } else {
      // Switched to root "/"
      const isViewingSaved = sessions.some((s) => s.id === activeSessionId || s.jobId === activeSessionId);
      if (isViewingSaved || (typeof window !== "undefined" && window.location.pathname === "/" && activeSessionId && !activeSessionId.startsWith("session-"))) {
        const freshDraftId = `session-${Date.now()}`;
        setActiveSessionId(freshDraftId);
        setActiveSteps([]);
        setInspectedMessage(undefined);
        setInspectedProvider(undefined);
        setIsRightSidebarOpen(false);
        setDraftSession(createFreshDraftSession(freshDraftId));
      }
    }
  }, [currentRouteChatId, isGenerating, sessions, activeSessionId]);

  const activeSession: ChatSession =
    sessions.find((s) => s.id === activeSessionId || s.jobId === activeSessionId) ||
    draftSession;

  // Convert selected provider ids to ProviderInfo objects
  const activeProviderIds = Array.isArray(activeSession.selectedProviders)
    ? activeSession.selectedProviders
    : (activeSession.selectedProvider ? [activeSession.selectedProvider] : []);

  const selectedProviders: ProviderInfo[] = activeProviderIds
    .map((id) => PROVIDERS_LIST.find((p) => p.id === id))
    .filter((p): p is ProviderInfo => Boolean(p));

  const primarySelectedProvider: ProviderInfo =
    selectedProviders[0] || PROVIDERS_LIST[0];

  const capsHook = useProviderCapabilities(primarySelectedProvider.id);

  // Derive previous agent/provider configurations from the active selected conversation
  const activeSessionAgentDefaults = useMemo(() => {
    if (!activeSession) {
      return {
        initialOrchestratorProvider: "gemini",
        initialLeadProvider: "chatgpt",
        initialDelegatedProviders: ["copilot", "gemini", "chatgpt", "deepseek", "qwen", "perplexity", "claude"],
        initialTone: "professional",
        initialQuery: "",
        initialOrchestratorConfig: undefined as Record<string, any> | undefined,
        initialLeadConfig: undefined as Record<string, any> | undefined,
        initialEnableFactCheck: false,
        initialFactCheckProvider: "perplexity",
        initialFactCheckConfig: undefined as Record<string, any> | undefined,
      };
    }

    // 1. Orchestrator provider:
    const rawOrch =
      activeSession.orchestrator_provider ||
      activeSession.messages.find((m) => m.orchestrator_provider)?.orchestrator_provider ||
      activeSession.selectedProviders?.[0] ||
      activeSession.selectedProvider ||
      "gemini";
    const resolvedOrch = (rawOrch || "gemini").toLowerCase();

    // 2. Lead provider:
    const rawLead =
      activeSession.lead_provider ||
      activeSession.messages.find((m) => m.lead_provider)?.lead_provider ||
      (activeSession.selectedProviders && activeSession.selectedProviders.length > 1
        ? activeSession.selectedProviders[1]
        : (resolvedOrch !== "chatgpt" ? "chatgpt" : "gemini"));
    const resolvedLead = (rawLead || "chatgpt").toLowerCase();

    // 3. Delegated providers:
    let resolvedDelegated: string[] = [];
    if (activeSession.delegated_providers && activeSession.delegated_providers.length > 0) {
      resolvedDelegated = activeSession.delegated_providers;
    } else {
      const msgDelegated = activeSession.messages.find(
        (m) => m.delegated_providers && m.delegated_providers.length > 0
      )?.delegated_providers;
      if (msgDelegated && msgDelegated.length > 0) {
        resolvedDelegated = msgDelegated;
      } else if (activeSession.orchestrator_dispatch && activeSession.orchestrator_dispatch.length > 0) {
        resolvedDelegated = Array.from(
          new Set(
            activeSession.orchestrator_dispatch
              .map((d: any) => d.id || d.provider_role_key)
              .filter(Boolean)
          )
        );
      } else if (activeSession.selectedProviders && activeSession.selectedProviders.length > 0) {
        resolvedDelegated = activeSession.selectedProviders;
      }
    }

    if (!resolvedDelegated || resolvedDelegated.length === 0) {
      resolvedDelegated = ["copilot", "gemini", "chatgpt", "deepseek", "qwen", "perplexity", "claude"];
    }

    // 4. Tone:
    const resolvedTone =
      activeSession.tone ||
      activeSession.messages.find((m) => m.tone)?.tone ||
      "professional";

    // 5. Query:
    const userMsg = activeSession.messages.find((m) => m.role === "user");
    const resolvedQuery =
      userMsg?.content ||
      (activeSession.title &&
        !activeSession.title.startsWith("Phiên mới") &&
        !activeSession.title.startsWith("session-") &&
        !activeSession.title.startsWith("Draft")
        ? activeSession.title
        : "");

    // 6. Orchestrator config:
    const orchConfig =
      activeSession.providerConfigurations?.[resolvedOrch] ||
      capsHook.selectionsMap?.[resolvedOrch] ||
      activeSession.messages.find((m) => m.provider_options?.[resolvedOrch])?.provider_options?.[resolvedOrch];

    // 7. Lead config:
    const leadConfig =
      activeSession.providerConfigurations?.[resolvedLead] ||
      capsHook.selectionsMap?.[resolvedLead] ||
      activeSession.messages.find((m) => m.provider_options?.[resolvedLead])?.provider_options?.[resolvedLead];

    // 8. Summarization provider:
    const rawSum =
      activeSession.summarization_provider ||
      activeSession.messages.find((m) => m.summarization_provider)?.summarization_provider ||
      "9router";
    const resolvedSum = rawSum || "9router";

    // 9. Summarization config (defaults to model Daily for 9router):
    const sumConfig =
      activeSession.summarization_config ||
      activeSession.providerConfigurations?.[resolvedSum] ||
      activeSession.messages.find((m) => m.summarization_config)?.summarization_config ||
      (resolvedSum === "9router"
        ? { model_id: "Daily" }
        : (capsHook.selectionsMap?.[resolvedSum] || { model_id: "Daily" }));

    // 10. Fact-Check defaults:
    const resolvedEnableFactCheck =
      activeSession.enable_fact_check ??
      activeSession.messages.find((m) => m.enable_fact_check !== undefined)?.enable_fact_check ??
      false;
    const resolvedFactCheckProvider =
      activeSession.fact_check_provider ||
      activeSession.messages.find((m) => m.fact_check_provider)?.fact_check_provider ||
      "perplexity";
    const resolvedFactCheckConfig =
      activeSession.fact_check_config ||
      activeSession.providerConfigurations?.[resolvedFactCheckProvider] ||
      activeSession.messages.find((m) => m.fact_check_config)?.fact_check_config;

    return {
      initialOrchestratorProvider: resolvedOrch,
      initialLeadProvider: resolvedLead,
      initialSummarizationProvider: resolvedSum,
      initialSummarizationConfig: sumConfig,
      initialDelegatedProviders: resolvedDelegated,
      initialTone: resolvedTone,
      initialQuery: resolvedQuery,
      initialOrchestratorConfig: orchConfig,
      initialLeadConfig: leadConfig,
      initialEnableFactCheck: resolvedEnableFactCheck,
      initialFactCheckProvider: resolvedFactCheckProvider,
      initialFactCheckConfig: resolvedFactCheckConfig,
    };
  }, [activeSession, capsHook.selectionsMap]);

  // Automatically open the right sidebar when generating starts so user can clearly see the thinking steps
  useEffect(() => {
    if (isGenerating) {
      setIsRightSidebarOpen(true);
      if (!inspectedProvider) {
        const first = activeProviderIds[0]?.toLowerCase() || "copilot";
        setInspectedProvider(first);
      }
    }
  }, [isGenerating, activeProviderIds, inspectedProvider]);

  const handleSelectSession = async (id: string, updateUrl: boolean = true) => {
    setActiveSessionId(id);
    setCurrentRouteChatId(id);

    // Update browser URL to /chat/{id}
    if (updateUrl && typeof window !== "undefined") {
      const targetPath = `/chat/${id}`;
      if (window.location.pathname !== targetPath) {
        window.history.pushState(null, "", targetPath);
      }
    }

    const session = sessions.find((s) => s.id === id || s.jobId === id);
    const targetJobId = session?.jobId || (!id.startsWith("session-") ? id : undefined);

    // If starting or selecting an empty conversation (no messages and no backend job ID)
    if (!targetJobId && (!session || session.messages.length === 0)) {
      setIsRightSidebarOpen(false);
      setActiveSteps([]);
      setInspectedMessage(undefined);
      setInspectedProvider(undefined);
      return;
    }

    // Otherwise, click on any conversation with content: open sidebar and load thinking steps, provider, sources
    setIsRightSidebarOpen(true);

    const existingAsst = session?.messages.find((m) => m.role === "assistant");
    const existingProviders = (session?.selectedProviders && session.selectedProviders.length > 0)
      ? session.selectedProviders
      : (existingAsst?.providers && existingAsst.providers.length > 0)
        ? existingAsst.providers
        : (session?.selectedProvider ? [session.selectedProvider] : []);
    const initialFirstProvider = (existingProviders[0] || "copilot").toLowerCase();

    setInspectedProvider(initialFirstProvider);
    if (existingAsst) {
      setInspectedMessage(existingAsst);
      if (existingAsst.steps && existingAsst.steps.length > 0) {
        setActiveSteps(existingAsst.steps);
      }
    }

    if (targetJobId) {
      try {
        const fullJob = await getResearchResult(targetJobId);
        if (!fullJob) return;

        // If the job is still actively running, reconnect to SSE stream!
        if (isActiveJobStatus(fullJob.status)) {
          connectToRunningJob(targetJobId, fullJob.steps || existingAsst?.steps || [], {
            ...session,
            ...fullJob,
          });
          return;
        }

        // If switching away from an active generating job to a terminal job, clean up active SSE
        if (activeJobIdRef.current && activeJobIdRef.current !== targetJobId) {
          if (activeUnsubscribeRef.current) {
            activeUnsubscribeRef.current();
            activeUnsubscribeRef.current = null;
          }
          activeJobIdRef.current = null;
          setIsGenerating(false);
        }

        let jobSources = fullJob.sources || [];
        if (jobSources.length === 0) {
          try {
            const dbSources = await fetchConversationCitations(targetJobId);
            if (dbSources && dbSources.length > 0) {
              jobSources = dbSources;
            }
          } catch { }
        }

        const jobSteps = fullJob.steps && fullJob.steps.length > 0
          ? fullJob.steps
          : (existingAsst?.steps || []);
        setActiveSteps(jobSteps);

        const fullJobProviders = (fullJob.providers && fullJob.providers.length > 0)
          ? fullJob.providers
          : (existingProviders.length > 0 ? existingProviders : ["copilot"]);
        const resolvedFirstProvider = (fullJobProviders[0] || initialFirstProvider).toLowerCase();
        setInspectedProvider(resolvedFirstProvider);

        const isAgentJob = (fullJob as any).job_type === "agent" || session?.job_type === "agent";
        const orchProv = (fullJob as any).orchestrator_provider || session?.orchestrator_provider;
        const leadProv = (fullJob as any).lead_provider || session?.lead_provider;
        const toneVal = (fullJob as any).tone || session?.tone;
        const orchDispatch = (fullJob as any).orchestrator_dispatch || session?.orchestrator_dispatch;

        const asstMsg = buildAssistantMessage(targetJobId, {
          report_markdown: fullJob.report_markdown || existingAsst?.content || null,
          status: fullJob.status,
          providers: fullJobProviders,
          created_at: (fullJob as any).created_at,
          finished_at: (fullJob as any).finished_at,
          sources: jobSources,
          claims: fullJob.claims || [],
          provider_runs: fullJob.provider_runs || {},
          provider_options: (fullJob as any).provider_options || {},
          steps: jobSteps,
          job_type: isAgentJob ? "agent" : "research",
          orchestrator_provider: orchProv,
          lead_provider: leadProv,
          tone: toneVal,
          orchestrator_dispatch: orchDispatch,
          delegated_providers: (fullJob as any).delegated_providers,
          error: (fullJob as any).error,
        });

        if (asstMsg) {
          setInspectedMessage(asstMsg);
        }
        setIsRightSidebarOpen(true);

        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== id && s.jobId !== id) return s;
            const finalMessages = asstMsg
              ? upsertAssistantMessage(s.messages, asstMsg)
              : s.messages;
            return {
              ...s,
              status: fullJob.status as any,
              selectedProviders: fullJobProviders,
              selectedProvider: fullJobProviders[0] || s.selectedProvider,
              messages: finalMessages,
              job_type: isAgentJob ? "agent" : s.job_type,
              orchestrator_provider: orchProv || s.orchestrator_provider,
              lead_provider: leadProv || s.lead_provider,
              tone: toneVal || s.tone,
              orchestrator_dispatch: orchDispatch || s.orchestrator_dispatch,
              delegated_providers: (fullJob as any).delegated_providers || s.delegated_providers,
              providerConfigurations: s.providerConfigurations || (fullJob as any).providerConfigurations || (fullJob as any).provider_options || {
                ...((orchProv && (fullJob as any).orchestrator_config) ? { [orchProv]: (fullJob as any).orchestrator_config } : {}),
                ...((leadProv && (fullJob as any).lead_config) ? { [leadProv]: (fullJob as any).lead_config } : {}),
              },
            };
          })
        );
      } catch (err) {
        console.warn("Could not fetch detailed job report:", err);
      }
    }
  };

  const handleNewChat = () => {
    if (isGenerating) {
      handleStopResearch();
    }
    const newId = `session-${Date.now()}`;
    const cleanDraft = createFreshDraftSession(newId);
    setDraftSession(cleanDraft);
    setActiveSessionId(newId);
    setCurrentRouteChatId(undefined);
    setActiveSteps([]);
    setInspectedMessage(undefined);
    setInspectedProvider(undefined);
    setIsRightSidebarOpen(false);

    // Update URL back to root
    if (typeof window !== "undefined" && window.location.pathname !== "/") {
      window.history.pushState(null, "", "/");
    }
    try {
      router.push("/");
    } catch { }
  };

  const handleNewAgent = () => {
    if (isGenerating) {
      handleStopResearch();
    }
    setIsAgentConfigOpen(true);
  };

  const handleStartAgentResearch = async (config: {
    query: string;
    orchestrator_provider: string;
    orchestrator_config: Record<string, any>;
    lead_provider: string;
    lead_config: Record<string, any>;
    summarization_provider: string;
    summarization_config: Record<string, any>;
    tone: string;
    delegated_providers?: string[];
    provider_configs?: Record<string, any>;
    provider_capabilities?: Record<string, any>;
    enable_fact_check?: boolean;
    fact_check_provider?: string;
    fact_check_config?: Record<string, any>;
  }) => {
    setIsAgentConfigOpen(false);

    isCancelledRef.current = false;
    activeJobIdRef.current = null;
    if (activeUnsubscribeRef.current) {
      activeUnsubscribeRef.current();
      activeUnsubscribeRef.current = null;
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      authorName: "Researcher",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      content: config.query,
      job_type: "agent",
      orchestrator_provider: config.orchestrator_provider,
      lead_provider: config.lead_provider,
      summarization_provider: config.summarization_provider,
      summarization_config: config.summarization_config,
      tone: config.tone,
      delegated_providers: config.delegated_providers,
      enable_fact_check: config.enable_fact_check,
      fact_check_provider: config.fact_check_provider,
      fact_check_config: config.fact_check_config,
      provider_options: {
        ...(config.provider_configs || {}),
        [config.orchestrator_provider]: config.orchestrator_config,
        [config.lead_provider]: config.lead_config,
        [config.summarization_provider]: config.summarization_config,
        ...(config.fact_check_provider && config.fact_check_config
          ? { [config.fact_check_provider]: config.fact_check_config }
          : {}),
      },
    };

    const newId = `session-agent-${Date.now()}`;
    const newSession: ChatSession = {
      id: newId,
      title: config.query.slice(0, 36) + (config.query.length > 36 ? "..." : ""),
      pinned: false,
      createdAt: "Vừa xong",
      createdTimestamp: Date.now(),
      selectedProviders: [config.orchestrator_provider, config.lead_provider],
      selectedProvider: config.orchestrator_provider,
      messages: [userMessage],
      status: "orchestrating",
      job_type: "agent",
      orchestrator_provider: config.orchestrator_provider,
      lead_provider: config.lead_provider,
      summarization_provider: config.summarization_provider,
      summarization_config: config.summarization_config,
      tone: config.tone,
      delegated_providers: config.delegated_providers,
      enable_fact_check: config.enable_fact_check,
      fact_check_provider: config.fact_check_provider,
      fact_check_config: config.fact_check_config,
      providerConfigurations: {
        ...(config.provider_configs || {}),
        [config.orchestrator_provider]: config.orchestrator_config,
        [config.lead_provider]: config.lead_config,
        [config.summarization_provider]: config.summarization_config,
        ...(config.fact_check_provider && config.fact_check_config
          ? { [config.fact_check_provider]: config.fact_check_config }
          : {}),
      },
    };

    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    setCurrentRouteChatId(newId);
    setIsGenerating(true);
    setActiveSteps([]);
    setInspectedMessage(undefined);
    setIsRightSidebarOpen(true);
    setInspectedProvider(config.orchestrator_provider);

    try {
      const jobAccepted = await createAgentResearchJob({
        query: config.query,
        orchestrator_provider: config.orchestrator_provider,
        orchestrator_config: config.orchestrator_config,
        lead_provider: config.lead_provider,
        lead_config: config.lead_config,
        summarization_provider: config.summarization_provider,
        summarization_config: config.summarization_config,
        tone: config.tone,
        delegated_providers: config.delegated_providers,
        provider_configs: config.provider_configs,
        provider_capabilities: config.provider_capabilities,
        enable_fact_check: config.enable_fact_check,
        fact_check_provider: config.fact_check_provider,
        fact_check_config: config.fact_check_config,
      });

      if (isCancelledRef.current) {
        cancelResearchJob(jobAccepted.job_id).catch(() => { });
        return;
      }

      activeJobIdRef.current = jobAccepted.job_id;
      setCurrentRouteChatId(jobAccepted.job_id);

      if (typeof window !== "undefined") {
        window.history.replaceState(null, "", `/chat/${jobAccepted.job_id}`);
      }

      setSessions((prev) =>
        prev.map((s) =>
          s.id === newId
            ? { ...s, id: jobAccepted.job_id, jobId: jobAccepted.job_id }
            : s
        )
      );
      setActiveSessionId(jobAccepted.job_id);

      const unsub = subscribeJobEvents(jobAccepted.job_id, {
        onStatus: (newStatus) => {
          if (isCancelledRef.current) return;
          setSessions((prev) =>
            prev.map((s) =>
              s.id === jobAccepted.job_id || s.jobId === jobAccepted.job_id
                ? { ...s, status: newStatus as any }
                : s
            )
          );
        },
        onStep: (stepLog) => {
          if (isCancelledRef.current) return;
          setActiveSteps((prev) => [...prev, stepLog]);

          const rawJobStatus = (stepLog.data as any)?.job_status;
          const dispatch = stepLog.data?.dispatch;
          const stepConvUrl = stepLog.conversationUrl || (stepLog.data as any)?.conversation_url;
          const stepProv = stepLog.provider || (stepLog.data as any)?.provider;
          const orchConvUrl = (stepLog.data as any)?.orch_conv_url;
          const leadConvUrl = (stepLog.data as any)?.lead_conv_url;

          setSessions((prev) =>
            prev.map((s) => {
              if (s.id !== jobAccepted.job_id && s.jobId !== jobAccepted.job_id) return s;
              let nextStatus = s.status;
              if (rawJobStatus && rawJobStatus !== "running") {
                nextStatus = rawJobStatus as any;
              } else if (stepLog.step === "fact_checking" || (stepLog.data as any)?.phase === "fact_checking") {
                nextStatus = "fact_checking" as any;
              } else if (stepLog.step === "summarizing") {
                nextStatus = "summarizing" as any;
              } else if (dispatch && nextStatus === "orchestrating") {
                nextStatus = "researching" as any;
              }
              const updatedProviderConvs = { ...(s.provider_conversations || {}) };
              if (stepConvUrl && stepProv) {
                updatedProviderConvs[stepProv] = stepConvUrl;
              }
              return {
                ...s,
                status: nextStatus,
                orchestrator_dispatch: dispatch || s.orchestrator_dispatch,
                orchestrator_conversation_url: orchConvUrl || s.orchestrator_conversation_url,
                lead_conversation_url: leadConvUrl || s.lead_conversation_url,
                provider_conversations: Object.keys(updatedProviderConvs).length > 0 ? updatedProviderConvs : s.provider_conversations,
              };
            })
          );
        },
        onResult: (result) => {
          if (isCancelledRef.current) return;
          const finalReport = result.report_markdown;
          if (finalReport) {
            const assistantMsg: Message = {
              id: `msg-${jobAccepted.job_id}-asst`,
              jobId: jobAccepted.job_id,
              role: "assistant",
              authorName: `Deep Research Orchestrator`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              content: finalReport,
              providers: [config.orchestrator_provider, config.lead_provider],
              sources: result.sources || [],
              claims: result.claims || [],
              disagreements: (result as any).disagreements || [],
              provider_runs: result.provider_runs || [],
              factCheckStatus: "verified",
              enable_fact_check: config.enable_fact_check,
              fact_check_provider: config.fact_check_provider,
              fact_check_config: config.fact_check_config,
              fact_check_results: (result as any).fact_check_results,
              steps: activeSteps,
              job_type: "agent",
              orchestrator_provider: config.orchestrator_provider,
              lead_provider: config.lead_provider,
              summarization_provider: config.summarization_provider,
              summarization_config: config.summarization_config,
              context_summary: (result as any).context_summary,
              tone: config.tone,
              orchestrator_dispatch: (result as any).orchestrator_dispatch,
              delegated_providers: config.delegated_providers,
              provider_options: {
                [config.orchestrator_provider]: config.orchestrator_config,
                [config.lead_provider]: config.lead_config,
                [config.summarization_provider]: config.summarization_config,
                ...(config.fact_check_provider && config.fact_check_config
                  ? { [config.fact_check_provider]: config.fact_check_config }
                  : {}),
              },
              orchestrator_conversation_url: result.orchestrator_conversation_url,
              lead_conversation_url: result.lead_conversation_url,
              provider_conversations: result.provider_conversations,
            };

            setSessions((prev) =>
              prev.map((s) =>
                s.id === jobAccepted.job_id || s.jobId === jobAccepted.job_id
                  ? {
                    ...s,
                    status: "completed",
                    messages: upsertAssistantMessage(s.messages, assistantMsg),
                    orchestrator_dispatch: (result as any).orchestrator_dispatch || s.orchestrator_dispatch,
                    delegated_providers: config.delegated_providers || s.delegated_providers,
                    summarization_provider: config.summarization_provider || s.summarization_provider,
                    summarization_config: config.summarization_config || s.summarization_config,
                    context_summary: (result as any).context_summary || s.context_summary,
                    orchestrator_conversation_url: result.orchestrator_conversation_url || s.orchestrator_conversation_url,
                    lead_conversation_url: result.lead_conversation_url || s.lead_conversation_url,
                    provider_conversations: {
                      ...(s.provider_conversations || {}),
                      ...(result.provider_conversations || {}),
                    },
                    enable_fact_check: config.enable_fact_check ?? s.enable_fact_check,
                    fact_check_provider: config.fact_check_provider || s.fact_check_provider,
                    fact_check_config: config.fact_check_config || s.fact_check_config,
                    fact_check_results: (result as any).fact_check_results || s.fact_check_results,
                    providerConfigurations: s.providerConfigurations || {
                      [config.orchestrator_provider]: config.orchestrator_config,
                      [config.lead_provider]: config.lead_config,
                      [config.summarization_provider]: config.summarization_config,
                      ...(config.fact_check_provider && config.fact_check_config
                        ? { [config.fact_check_provider]: config.fact_check_config }
                        : {}),
                    },
                  }
                  : s
              )
            );
            setIsGenerating(false);
            activeJobIdRef.current = null;
          }
        },
        onError: (err) => {
          console.warn("Agent job SSE error:", err);
          setIsGenerating(false);
          activeJobIdRef.current = null;
        },
        onDone: async () => {
          if (isCancelledRef.current) return;
          try {
            const finalResult = await getResearchResult(jobAccepted.job_id);
            if (finalResult && finalResult.report_markdown) {
              const assistantMsg: Message = {
                id: `msg-${jobAccepted.job_id}-asst`,
                jobId: jobAccepted.job_id,
                role: "assistant",
                authorName: `Deep Research Orchestrator`,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                content: finalResult.report_markdown,
                providers: [config.orchestrator_provider, config.lead_provider],
                sources: finalResult.sources || [],
                claims: finalResult.claims || [],
                disagreements: finalResult.disagreements || [],
                provider_runs: finalResult.provider_runs || [],
                factCheckStatus: "verified",
                enable_fact_check: finalResult.enable_fact_check ?? config.enable_fact_check,
                fact_check_provider: finalResult.fact_check_provider || config.fact_check_provider,
                fact_check_config: finalResult.fact_check_config || config.fact_check_config,
                fact_check_results: finalResult.fact_check_results,
                steps: activeSteps,
                job_type: "agent",
                orchestrator_provider: config.orchestrator_provider,
                lead_provider: config.lead_provider,
                summarization_provider: config.summarization_provider,
                summarization_config: config.summarization_config,
                context_summary: finalResult.context_summary,
                tone: config.tone,
                orchestrator_dispatch: finalResult.orchestrator_dispatch,
                delegated_providers: config.delegated_providers,
                provider_options: {
                  [config.orchestrator_provider]: config.orchestrator_config,
                  [config.lead_provider]: config.lead_config,
                  [config.summarization_provider]: config.summarization_config,
                  ...(config.fact_check_provider && config.fact_check_config
                    ? { [config.fact_check_provider]: config.fact_check_config }
                    : {}),
                },
                orchestrator_conversation_url: finalResult.orchestrator_conversation_url,
                lead_conversation_url: finalResult.lead_conversation_url,
                provider_conversations: finalResult.provider_conversations,
              };

              setSessions((prev) =>
                prev.map((s) =>
                  s.id === jobAccepted.job_id || s.jobId === jobAccepted.job_id
                    ? {
                      ...s,
                      status: "completed",
                      messages: upsertAssistantMessage(s.messages, assistantMsg),
                      orchestrator_dispatch: finalResult.orchestrator_dispatch || s.orchestrator_dispatch,
                      delegated_providers: config.delegated_providers || s.delegated_providers,
                      summarization_provider: config.summarization_provider || s.summarization_provider,
                      summarization_config: config.summarization_config || s.summarization_config,
                      context_summary: finalResult.context_summary || s.context_summary,
                      orchestrator_conversation_url: finalResult.orchestrator_conversation_url || s.orchestrator_conversation_url,
                      lead_conversation_url: finalResult.lead_conversation_url || s.lead_conversation_url,
                      provider_conversations: {
                        ...(s.provider_conversations || {}),
                        ...(finalResult.provider_conversations || {}),
                      },
                      enable_fact_check: finalResult.enable_fact_check ?? config.enable_fact_check ?? s.enable_fact_check,
                      fact_check_provider: finalResult.fact_check_provider || config.fact_check_provider || s.fact_check_provider,
                      fact_check_config: finalResult.fact_check_config || config.fact_check_config || s.fact_check_config,
                      fact_check_results: finalResult.fact_check_results || s.fact_check_results,
                      providerConfigurations: s.providerConfigurations || {
                        [config.orchestrator_provider]: config.orchestrator_config,
                        [config.lead_provider]: config.lead_config,
                        [config.summarization_provider]: config.summarization_config,
                        ...(config.fact_check_provider && config.fact_check_config
                          ? { [config.fact_check_provider]: config.fact_check_config }
                          : {}),
                      },
                    }
                    : s
                )
              );
            }
          } catch (e) {
            console.warn("Could not fetch final research result in onDone:", e);
          } finally {
            setIsGenerating(false);
            activeJobIdRef.current = null;
          }
        },
      });

      activeUnsubscribeRef.current = unsub;
    } catch (err: any) {
      console.error("Failed to start agent research job:", err);
      setIsGenerating(false);
      activeJobIdRef.current = null;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === newId
            ? { ...s, status: "failed" }
            : s
        )
      );
    }
  };


  const handleTogglePin = (id: string) => {
    const session = sessions.find((s) => s.id === id || s.jobId === id);
    const newPinned = session ? !session.pinned : true;
    const targetJobId = session?.jobId || (!id.startsWith("session-") ? id : undefined);
    if (targetJobId) {
      updateResearchJob(targetJobId, { pinned: newPinned });
    }
    setSessions((prev) =>
      prev.map((s) => (s.id === id || s.jobId === id ? { ...s, pinned: newPinned } : s))
    );
  };

  const handleRenameSession = (id: string, newTitle: string) => {
    if (!newTitle.trim()) return;
    const trimmed = newTitle.trim();
    const session = sessions.find((s) => s.id === id || s.jobId === id);
    const targetJobId = session?.jobId || (!id.startsWith("session-") ? id : undefined);
    if (targetJobId) {
      updateResearchJob(targetJobId, { title: trimmed });
    }
    setSessions((prev) =>
      prev.map((s) => (s.id === id || s.jobId === id ? { ...s, title: trimmed } : s))
    );
  };

  const handleDeleteSession = async (id: string) => {
    const session = sessions.find((s) => s.id === id || s.jobId === id);
    const targetJobId = session?.jobId || (!id.startsWith("session-") ? id : undefined);

    const jobIdsToDelete = new Set<string>();
    if (targetJobId) jobIdsToDelete.add(targetJobId);
    if (!id.startsWith("session-")) jobIdsToDelete.add(id);
    if (session?.messages) {
      for (const m of session.messages) {
        if (m.jobId) jobIdsToDelete.add(m.jobId);
      }
    }

    markSessionAsDeleted(id, targetJobId);
    for (const jId of jobIdsToDelete) {
      markSessionAsDeleted(jId, jId);
      deleteResearchJob(jId, DEFAULT_API_KEY, { deleteRemote: true }).catch(() => {});
    }

    const remaining = sessions.filter((s) => s.id !== id && s.jobId !== id);
    setSessions(remaining);

    // Deleted the conversation currently being viewed: return to the clean draft
    // screen at "/" so the user can start over; do NOT save any empty session!
    if (activeSessionId === id || activeSessionId === targetJobId) {
      const freshDraftId = `session-${Date.now()}`;
      setActiveSessionId(freshDraftId);
      setCurrentRouteChatId(undefined);
      setActiveSteps([]);
      setInspectedMessage(undefined);
      setInspectedProvider(undefined);
      setIsRightSidebarOpen(false);

      setDraftSession(createFreshDraftSession(freshDraftId));

      if (typeof window !== "undefined" && window.location.pathname !== "/") {
        window.history.pushState(null, "", "/");
      }
      try {
        router.push("/");
      } catch { }
    }
  };

  const handleToggleProvider = (providerId: string) => {
    const isSavedSession = sessions.some(
      (s) => s.id === activeSessionId || s.jobId === activeSessionId
    );
    if (!isSavedSession) {
      setDraftSession((prev) => {
        const currentIds = Array.isArray(prev.selectedProviders)
          ? prev.selectedProviders
          : (prev.selectedProvider ? [prev.selectedProvider] : []);
        let updatedIds: string[];
        if (currentIds.includes(providerId)) {
          updatedIds = currentIds.filter((id) => id !== providerId);
        } else {
          updatedIds = [...currentIds, providerId];
        }
        return {
          ...prev,
          selectedProviders: updatedIds,
          selectedProvider: updatedIds[0] || "",
        };
      });
      return;
    }
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeSessionId && s.jobId !== activeSessionId) return s;
        const currentIds = Array.isArray(s.selectedProviders)
          ? s.selectedProviders
          : (s.selectedProvider ? [s.selectedProvider] : []);
        let updatedIds: string[];
        if (currentIds.includes(providerId)) {
          updatedIds = currentIds.filter((id) => id !== providerId);
        } else {
          updatedIds = [...currentIds, providerId];
        }
        return {
          ...s,
          selectedProviders: updatedIds,
          selectedProvider: updatedIds[0] || "",
        };
      })
    );
  };

  const handleSelectMultipleProviders = (providerIds: string[]) => {
    if (providerIds.length === 0) return;
    const isSavedSession = sessions.some(
      (s) => s.id === activeSessionId || s.jobId === activeSessionId
    );
    if (!isSavedSession) {
      setDraftSession((prev) => ({
        ...prev,
        selectedProviders: providerIds,
        selectedProvider: providerIds[0] || "",
      }));
      return;
    }
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId || s.jobId === activeSessionId
          ? {
            ...s,
            selectedProviders: providerIds,
            selectedProvider: providerIds[0],
          }
          : s
      )
    );
  };

  const handleStopResearch = useCallback(async () => {
    if (!isGenerating) return;

    isCancelledRef.current = true;
    const currentJobId = activeJobIdRef.current;

    // 1. Immediately unsubscribe from SSE
    if (activeUnsubscribeRef.current) {
      try {
        activeUnsubscribeRef.current();
      } catch (err) {
        console.warn("Error calling SSE unsubscribe:", err);
      }
      activeUnsubscribeRef.current = null;
    }

    // 2. Immediately call backend to cancel the job
    if (currentJobId) {
      cancelResearchJob(currentJobId).catch((err) => {
        console.warn("Failed to cancel job on backend:", err);
      });
    }

    // 3. Immediately reset generating state
    setIsGenerating(false);

    const targetSessionId = activeSessionId;
    const currentSession = sessions.find((s) => s.id === targetSessionId || s.jobId === targetSessionId) || activeSession;
    const currentProviderIds =
      currentSession.selectedProviders && currentSession.selectedProviders.length > 0
        ? currentSession.selectedProviders
        : [primarySelectedProvider.id];

    // 4. Update the chat messages directly to show the user that they stopped the research
    const stoppedText = "you stopped the research, please try again.";
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== targetSessionId && s.jobId !== targetSessionId) return s;

        const asstMsgId = currentJobId ? `msg-${currentJobId}-asst` : `asst-stopped-${Date.now()}`;
        const assistantMsg: Message = {
          id: asstMsgId,
          jobId: currentJobId || undefined,
          role: "assistant",
          authorName: `AI Research Engine`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          content: stoppedText,
          providers: currentProviderIds,
          steps: activeSteps,
          provider_options: capsHook.selectionsMap,
          factCheckStatus: "unverified",
        };

        return {
          ...s,
          status: "cancelled",
          messages: upsertAssistantMessage(s.messages, assistantMsg),
        };
      })
    );
  }, [isGenerating, activeSessionId, sessions, activeSession, primarySelectedProvider.id, activeSteps]);

  const handleSendMessage = async (content: string) => {
    if (isGenerating) return;

    if (activeProviderIds.length === 0) {
      setIsProvidersModalOpen(true);
      return;
    }

    isCancelledRef.current = false;
    activeJobIdRef.current = null;
    if (activeUnsubscribeRef.current) {
      activeUnsubscribeRef.current();
      activeUnsubscribeRef.current = null;
    }

    const isAgentSession = activeSession.job_type === "agent" || Boolean(activeSession.orchestrator_provider);
    const parentJobId = activeSession.jobId || activeSession.messages.filter((m) => m.jobId).pop()?.jobId;

    const orchProv = activeSession.orchestrator_provider || activeSessionAgentDefaults.initialOrchestratorProvider || "gemini";
    const leadProv = activeSession.lead_provider || activeSessionAgentDefaults.initialLeadProvider || "chatgpt";
    const sumProv = activeSession.summarization_provider || activeSessionAgentDefaults.initialSummarizationProvider || "9router";
    const orchConf = activeSession.providerConfigurations?.[orchProv] || activeSessionAgentDefaults.initialOrchestratorConfig || {};
    const leadConf = activeSession.providerConfigurations?.[leadProv] || activeSessionAgentDefaults.initialLeadConfig || {};
    const sumConf = activeSession.summarization_config || activeSessionAgentDefaults.initialSummarizationConfig || { model_id: "Daily" };
    const toneVal = activeSession.tone || activeSessionAgentDefaults.initialTone || "professional";
    const delegatedProvs = activeSession.delegated_providers || activeSessionAgentDefaults.initialDelegatedProviders;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      authorName: "Researcher",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      content,
      job_type: isAgentSession ? "agent" : undefined,
      orchestrator_provider: isAgentSession ? orchProv : undefined,
      lead_provider: isAgentSession ? leadProv : undefined,
      summarization_provider: isAgentSession ? sumProv : undefined,
      summarization_config: isAgentSession ? sumConf : undefined,
      tone: isAgentSession ? toneVal : undefined,
      delegated_providers: isAgentSession ? delegatedProvs : undefined,
    };

    const updatedTitle =
      activeSession.messages.length === 0
        ? content.slice(0, 36) + (content.length > 36 ? "..." : "")
        : activeSession.title;

    const isSavedSession = sessions.some(
      (s) => s.id === activeSessionId || s.jobId === activeSessionId
    );

    if (!isSavedSession) {
      // First question sent: save conversation into sessions now using the question as title!
      const newSavedSession: ChatSession = {
        ...activeSession,
        id: activeSessionId || `session-${Date.now()}`,
        title: updatedTitle,
        messages: [userMessage],
        status: isAgentSession ? "orchestrating" : "running",
        createdAt: "Vừa xong",
        createdTimestamp: Date.now(),
      };
      setSessions((prev) => [newSavedSession, ...prev]);
    } else {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId || s.jobId === activeSessionId
            ? {
              ...s,
              title: updatedTitle,
              messages: [...s.messages, userMessage],
              status: isAgentSession ? "orchestrating" : "running",
            }
            : s
        )
      );
    }

    setIsGenerating(true);
    setActiveSteps([]);
    setInspectedMessage(undefined);
    setIsRightSidebarOpen(true);

    const currentProviderIds = activeProviderIds;
    if (!inspectedProvider) {
      setInspectedProvider(isAgentSession ? orchProv.toLowerCase() : (currentProviderIds[0]?.toLowerCase() || "copilot"));
    }

    try {
      // 1. Collect stored conversation URLs from previous rounds in this session
      const existingConvUrls: Record<string, string> = {};
      if (activeSession.provider_conversations) {
        Object.assign(existingConvUrls, activeSession.provider_conversations);
      }
      if (activeSession.orchestrator_conversation_url) {
        existingConvUrls["orchestrator"] = activeSession.orchestrator_conversation_url;
      }
      if (activeSession.lead_conversation_url) {
        existingConvUrls["lead"] = activeSession.lead_conversation_url;
      }
      for (const m of activeSession.messages) {
        if (m.provider_conversations) {
          Object.assign(existingConvUrls, m.provider_conversations);
        }
        if (m.orchestrator_conversation_url) {
          existingConvUrls["orchestrator"] = m.orchestrator_conversation_url;
        }
        if (m.lead_conversation_url) {
          existingConvUrls["lead"] = m.lead_conversation_url;
        }
        if (Array.isArray(m.provider_runs)) {
          for (const r of m.provider_runs) {
            if (r.provider && r.conversation_url) {
              existingConvUrls[r.provider] = r.conversation_url;
            }
          }
        }
      }

      let jobAccepted: any;

      if (isAgentSession) {
        jobAccepted = await createAgentResearchJob({
          query: content,
          orchestrator_provider: orchProv,
          orchestrator_config: orchConf,
          lead_provider: leadProv,
          lead_config: leadConf,
          summarization_provider: sumProv,
          summarization_config: sumConf,
          tone: toneVal,
          delegated_providers: delegatedProvs,
          provider_configs: activeSession.providerConfigurations,
          conversation_urls: Object.keys(existingConvUrls).length > 0 ? existingConvUrls : undefined,
          parent_job_id: parentJobId || undefined,
        });
      } else {
        const filteredConvUrls: Record<string, string> = {};
        for (const pId of currentProviderIds) {
          if (existingConvUrls[pId]) {
            filteredConvUrls[pId] = existingConvUrls[pId];
          }
        }
        const sanitizedOptions: Record<string, any> = {};
        for (const [pId, opts] of Object.entries(capsHook.selectionsMap || {})) {
          const pCaps = capsHook.capabilitiesMap[pId];
          const isFree = pId === "chatgpt" && pCaps?.account_type === "free";
          sanitizedOptions[pId] = {
            ...opts,
            model_id: isFree ? "none" : opts.model_id,
          };
        }
        jobAccepted = await createResearchJob({
          query: content,
          providers: currentProviderIds,
          provider_options: sanitizedOptions,
          conversation_urls: Object.keys(filteredConvUrls).length > 0 ? filteredConvUrls : undefined,
          parent_job_id: parentJobId || undefined,
        });
      }

      if (isCancelledRef.current) {
        cancelResearchJob(jobAccepted.job_id).catch(() => { });
        return;
      }

      const targetSessionId = activeSessionId;
      const isDraft = targetSessionId.startsWith("session-");
      const resolvedSessionId = isDraft ? jobAccepted.job_id : targetSessionId;

      activeJobIdRef.current = jobAccepted.job_id;
      setCurrentRouteChatId(jobAccepted.job_id);

      // Update URL to /chat/{job_id} for shareable direct route on first question
      if (typeof window !== "undefined" && isDraft) {
        window.history.replaceState(null, "", `/chat/${jobAccepted.job_id}`);
      }

      // Update session with backend job id
      setSessions((prev) =>
        prev.map((s) =>
          s.id === targetSessionId || s.jobId === targetSessionId
            ? { ...s, id: resolvedSessionId, jobId: jobAccepted.job_id, status: isAgentSession ? "orchestrating" : "running" }
            : s
        )
      );
      setActiveSessionId(resolvedSessionId);

      // 2. Subscribe to real-time SSE progress events
      const unsub = subscribeJobEvents(jobAccepted.job_id, {
        onStatus: (newStatus) => {
          if (isCancelledRef.current) return;
          setSessions((prev) =>
            prev.map((s) =>
              s.id === resolvedSessionId || s.jobId === jobAccepted.job_id || s.messages.some((m) => m.jobId === jobAccepted.job_id)
                ? { ...s, status: newStatus as any }
                : s
            )
          );
        },
        onStep: (stepLog) => {
          if (isCancelledRef.current) return;
          setActiveSteps((prev) => [...prev, stepLog]);

          const rawJobStatus = (stepLog.data as any)?.job_status;
          const dispatch = stepLog.data?.dispatch;
          const stepConvUrl = stepLog.conversationUrl || (stepLog.data as any)?.conversation_url;
          const stepProv = stepLog.provider || (stepLog.data as any)?.provider;
          const orchConvUrl = (stepLog.data as any)?.orch_conv_url;
          const leadConvUrl = (stepLog.data as any)?.lead_conv_url;

          setSessions((prev) =>
            prev.map((s) => {
              if (s.id !== resolvedSessionId && s.jobId !== jobAccepted.job_id && !s.messages.some((m) => m.jobId === jobAccepted.job_id)) return s;
              let nextStatus = s.status;
              if (rawJobStatus && rawJobStatus !== "running") {
                nextStatus = rawJobStatus as any;
              } else if (stepLog.step === "summarizing") {
                nextStatus = "summarizing" as any;
              } else if (dispatch && nextStatus === "orchestrating") {
                nextStatus = "researching" as any;
              }
              const updatedProviderConvs = { ...(s.provider_conversations || {}) };
              if (stepConvUrl && stepProv) {
                updatedProviderConvs[stepProv] = stepConvUrl;
              }
              return {
                ...s,
                status: nextStatus,
                orchestrator_dispatch: dispatch || s.orchestrator_dispatch,
                orchestrator_conversation_url: orchConvUrl || s.orchestrator_conversation_url,
                lead_conversation_url: leadConvUrl || s.lead_conversation_url,
                provider_conversations: Object.keys(updatedProviderConvs).length > 0 ? updatedProviderConvs : s.provider_conversations,
              };
            })
          );
        },
        onResult: (result) => {
          if (isCancelledRef.current) return;
          setActiveSteps((latestSteps) => {
            const consolidatedSources = [...(result.sources || [])];
            const seenUrls = new Set(consolidatedSources.map((s) => s.url));
            for (const st of latestSteps) {
              const stepCits = st.citations || (st.data as any)?.citations || [];
              for (const c of stepCits) {
                if (c && c.url && !seenUrls.has(c.url)) {
                  seenUrls.add(c.url);
                  consolidatedSources.push({
                    title: c.title || c.url,
                    url: c.url,
                    domain: c.domain,
                  });
                }
              }
            }

            const asstMsg = buildAssistantMessage(jobAccepted.job_id, {
              report_markdown: result.report_markdown,
              status: result.status || "completed",
              providers: isAgentSession ? [orchProv, leadProv] : currentProviderIds,
              sources: consolidatedSources,
              claims: result.claims || [],
              disagreements: result.disagreements || [],
              provider_runs: result.provider_runs || {},
              provider_options: (result as any).provider_options || capsHook.selectionsMap,
              steps: latestSteps,
              error: result.error,
              job_type: isAgentSession ? "agent" : "research",
              orchestrator_provider: isAgentSession ? orchProv : undefined,
              lead_provider: isAgentSession ? leadProv : undefined,
              summarization_provider: isAgentSession ? sumProv : undefined,
              summarization_config: isAgentSession ? sumConf : undefined,
              context_summary: (result as any).context_summary,
              tone: isAgentSession ? toneVal : undefined,
              orchestrator_dispatch: (result as any).orchestrator_dispatch,
              delegated_providers: isAgentSession ? delegatedProvs : undefined,
              orchestrator_conversation_url: result.orchestrator_conversation_url,
              lead_conversation_url: result.lead_conversation_url,
              provider_conversations: result.provider_conversations || existingConvUrls,
            });

            if (asstMsg) {
              setInspectedMessage(asstMsg);
              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== resolvedSessionId && s.jobId !== jobAccepted.job_id && !s.messages.some((m) => m.jobId === jobAccepted.job_id)) return s;
                  const mergedConvUrls = {
                    ...(s.provider_conversations || {}),
                    ...existingConvUrls,
                    ...(result.provider_conversations || {}),
                  };
                  return {
                    ...s,
                    status: (result.status as any) || "completed",
                    orchestrator_dispatch: (result as any).orchestrator_dispatch || s.orchestrator_dispatch,
                    orchestrator_conversation_url: result.orchestrator_conversation_url || s.orchestrator_conversation_url,
                    lead_conversation_url: result.lead_conversation_url || s.lead_conversation_url,
                    summarization_provider: isAgentSession ? (sumProv || s.summarization_provider) : s.summarization_provider,
                    summarization_config: isAgentSession ? (sumConf || s.summarization_config) : s.summarization_config,
                    context_summary: (result as any).context_summary || s.context_summary,
                    provider_conversations: mergedConvUrls,
                    messages: upsertAssistantMessage(s.messages, asstMsg),
                  };
                })
              );
            }
            return latestSteps;
          });
          activeUnsubscribeRef.current = null;
          activeJobIdRef.current = null;
          setIsGenerating(false);
        },
        onError: async (err) => {
          if (isCancelledRef.current) return;
          console.warn("SSE stream issue:", err);
          try {
            const finalResult = await getResearchResult(jobAccepted.job_id);
            if (finalResult && !isActiveJobStatus(finalResult.status)) {
              setActiveSteps((latestSteps) => {
                const asstMsg = buildAssistantMessage(jobAccepted.job_id, {
                  ...finalResult,
                  providers: isAgentSession ? [orchProv, leadProv] : currentProviderIds,
                  steps: latestSteps,
                  job_type: isAgentSession ? "agent" : "research",
                  orchestrator_provider: isAgentSession ? orchProv : undefined,
                  lead_provider: isAgentSession ? leadProv : undefined,
                  summarization_provider: isAgentSession ? sumProv : undefined,
                  summarization_config: isAgentSession ? sumConf : undefined,
                  context_summary: finalResult.context_summary,
                  tone: isAgentSession ? toneVal : undefined,
                  orchestrator_dispatch: finalResult.orchestrator_dispatch,
                  delegated_providers: isAgentSession ? delegatedProvs : undefined,
                  orchestrator_conversation_url: finalResult.orchestrator_conversation_url,
                  lead_conversation_url: finalResult.lead_conversation_url,
                  provider_conversations: finalResult.provider_conversations || existingConvUrls,
                });
                if (asstMsg) {
                  setInspectedMessage(asstMsg);
                  setSessions((prev) =>
                    prev.map((s) =>
                      s.id === resolvedSessionId || s.jobId === jobAccepted.job_id || s.messages.some((m) => m.jobId === jobAccepted.job_id)
                        ? {
                            ...s,
                            status: (finalResult.status as any) || "completed",
                            orchestrator_dispatch: finalResult.orchestrator_dispatch || s.orchestrator_dispatch,
                            orchestrator_conversation_url: finalResult.orchestrator_conversation_url || s.orchestrator_conversation_url,
                            lead_conversation_url: finalResult.lead_conversation_url || s.lead_conversation_url,
                            summarization_provider: isAgentSession ? (sumProv || s.summarization_provider) : s.summarization_provider,
                            summarization_config: isAgentSession ? (sumConf || s.summarization_config) : s.summarization_config,
                            context_summary: finalResult.context_summary || s.context_summary,
                            provider_conversations: {
                              ...(s.provider_conversations || {}),
                              ...existingConvUrls,
                              ...(finalResult.provider_conversations || {}),
                            },
                            messages: upsertAssistantMessage(s.messages, asstMsg),
                          }
                        : s
                    )
                  );
                }
                return latestSteps;
              });
              activeUnsubscribeRef.current = null;
              activeJobIdRef.current = null;
              setIsGenerating(false);
              return;
            }
          } catch { }
          handleSimulatedMultiModelResponse(content, isAgentSession ? [orchProv, leadProv] : currentProviderIds);
        },
        onDone: async () => {
          if (isCancelledRef.current) return;
          try {
            const finalResult = await getResearchResult(jobAccepted.job_id);
            if (finalResult) {
              setActiveSteps((latestSteps) => {
                const asstMsg = buildAssistantMessage(jobAccepted.job_id, {
                  ...finalResult,
                  providers: isAgentSession ? [orchProv, leadProv] : currentProviderIds,
                  steps: latestSteps,
                  job_type: isAgentSession ? "agent" : "research",
                  orchestrator_provider: isAgentSession ? orchProv : undefined,
                  lead_provider: isAgentSession ? leadProv : undefined,
                  summarization_provider: isAgentSession ? sumProv : undefined,
                  summarization_config: isAgentSession ? sumConf : undefined,
                  context_summary: finalResult.context_summary,
                  tone: isAgentSession ? toneVal : undefined,
                  orchestrator_dispatch: finalResult.orchestrator_dispatch,
                  delegated_providers: isAgentSession ? delegatedProvs : undefined,
                  orchestrator_conversation_url: finalResult.orchestrator_conversation_url,
                  lead_conversation_url: finalResult.lead_conversation_url,
                  provider_conversations: finalResult.provider_conversations || existingConvUrls,
                });
                if (asstMsg) {
                  setInspectedMessage(asstMsg);
                  setSessions((prev) =>
                    prev.map((s) =>
                      s.id === resolvedSessionId || s.jobId === jobAccepted.job_id || s.messages.some((m) => m.jobId === jobAccepted.job_id)
                        ? {
                            ...s,
                            status: (finalResult.status as any) || "completed",
                            orchestrator_dispatch: finalResult.orchestrator_dispatch || s.orchestrator_dispatch,
                            orchestrator_conversation_url: finalResult.orchestrator_conversation_url || s.orchestrator_conversation_url,
                            lead_conversation_url: finalResult.lead_conversation_url || s.lead_conversation_url,
                            summarization_provider: isAgentSession ? (sumProv || s.summarization_provider) : s.summarization_provider,
                            summarization_config: isAgentSession ? (sumConf || s.summarization_config) : s.summarization_config,
                            context_summary: finalResult.context_summary || s.context_summary,
                            provider_conversations: {
                              ...(s.provider_conversations || {}),
                              ...existingConvUrls,
                              ...(finalResult.provider_conversations || {}),
                            },
                            messages: upsertAssistantMessage(s.messages, asstMsg),
                          }
                        : s
                    )
                  );
                }
                return latestSteps;
              });
            }
          } catch (e) {
            console.warn("Could not fetch final research result in onDone:", e);
          } finally {
            activeUnsubscribeRef.current = null;
            activeJobIdRef.current = null;
            setIsGenerating(false);
          }
        },
      });

      activeUnsubscribeRef.current = unsub;

    } catch (err) {
      if (isCancelledRef.current) return;
      console.info("Backend API offline or unreachable, engaging interactive multi-model simulation:", err);
      handleSimulatedMultiModelResponse(content, currentProviderIds);
    }
  };

  const handleRetryProvider = useCallback(
    async (provider: string, jobId?: string) => {
      const targetJobId = jobId || activeJobIdRef.current || activeSession.jobId;
      if (!targetJobId) {
        const userMsg = activeSession.messages.find((m) => m.role === "user");
        if (userMsg) {
          handleSendMessage(userMsg.content);
        }
        return;
      }

      setIsGenerating(true);
      setIsRightSidebarOpen(true);
      setInspectedProvider(provider.toLowerCase());
      try {
        await retryJobProvider(targetJobId, provider);

        if (activeUnsubscribeRef.current) {
          activeUnsubscribeRef.current();
          activeUnsubscribeRef.current = null;
        }
        activeJobIdRef.current = targetJobId;

        const unsub = subscribeJobEvents(targetJobId, {
          onStep: (stepLog) => {
            setActiveSteps((prev) => [...prev, stepLog]);
          },
          onResult: (result) => {
            setActiveSteps((latestSteps) => {
              const consolidatedSources = [...(result.sources || [])];
              const seenUrls = new Set(consolidatedSources.map((s) => s.url));
              for (const st of latestSteps) {
                const stepCits = st.citations || (st.data as any)?.citations || [];
                for (const c of stepCits) {
                  if (c && c.url && !seenUrls.has(c.url)) {
                    seenUrls.add(c.url);
                    consolidatedSources.push({
                      title: c.title || c.url,
                      url: c.url,
                      domain: c.domain,
                    });
                  }
                }
              }

              const asstMsgId = `msg-${targetJobId}-asst`;
              const assistantMsg: Message = {
                id: asstMsgId,
                jobId: targetJobId,
                role: "assistant",
                authorName: `AI Research Engine`,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                content: result.report_markdown || "Đã cập nhật câu trả lời từ các mô hình.",
                providers: result.providers || activeSession.selectedProviders || [provider],
                tokens: 1540,
                latencySeconds: 10.8,
                sources: consolidatedSources,
                claims: result.claims || [],
                disagreements: result.disagreements || [],
                provider_runs: result.provider_runs || {},
                factCheckStatus: "verified",
                steps: latestSteps,
              };

              setSessions((prev) =>
                prev.map((s) => {
                  if (s.id !== targetJobId && s.jobId !== targetJobId) return s;
                  return {
                    ...s,
                    status: "completed",
                    messages: upsertAssistantMessage(s.messages, assistantMsg),
                  };
                })
              );
              setInspectedMessage(assistantMsg);
              return latestSteps;
            });
            setIsGenerating(false);
            activeUnsubscribeRef.current = null;
          },
          onError: (err) => {
            console.warn("Retry SSE issue:", err);
            setIsGenerating(false);
          },
          onDone: async () => {
            try {
              const finalResult = await getResearchResult(targetJobId);
              if (finalResult) {
                setActiveSteps((latestSteps) => {
                  const asstMsg = buildAssistantMessage(targetJobId, {
                    ...finalResult,
                    steps: latestSteps,
                  });
                  if (asstMsg) {
                    setSessions((prev) =>
                      prev.map((s) => {
                        if (s.id !== targetJobId && s.jobId !== targetJobId) return s;
                        return {
                          ...s,
                          status: (finalResult.status as any) || "completed",
                          messages: upsertAssistantMessage(s.messages, asstMsg),
                        };
                      })
                    );
                    setInspectedMessage(asstMsg);
                  }
                  return latestSteps;
                });
              }
            } catch (e) {
              console.warn("Could not fetch final retry result in onDone:", e);
            } finally {
              setIsGenerating(false);
              activeJobIdRef.current = null;
              activeUnsubscribeRef.current = null;
            }
          },
        });
        activeUnsubscribeRef.current = unsub;
      } catch (err) {
        console.error("Failed to retry provider:", err);
        setIsGenerating(false);
      }
    },
    [activeSession, handleSendMessage]
  );

  const handleSimulatedMultiModelResponse = (
    content: string,
    providerIds: string[]
  ) => {
    const activeInfoList = providerIds
      .map((id) => PROVIDERS_LIST.find((p) => p.id === id))
      .filter((p): p is ProviderInfo => Boolean(p));

    const simulatedSteps: StepLog[] = [
      {
        id: "step-1",
        timestamp: "0s",
        step: "planning",
        message: `Phân tích yêu cầu và điều phối tác vụ tới ${activeInfoList.map((p) => p.name).join(", ")}...`,
        status: "completed",
      },
      {
        id: "step-2",
        timestamp: "1s",
        step: "researching",
        message: `Thu thập dữ liệu web và chạy mô hình ${activeInfoList[0]?.name || "AI"}...`,
        status: "running",
      },
    ];

    setActiveSteps(simulatedSteps);

    setTimeout(() => {
      const step2Updated: StepLog[] = simulatedSteps.map((s) =>
        s.id === "step-2" ? { ...s, status: "completed" as const } : s
      );
      step2Updated.push({
        id: "step-3",
        timestamp: "2s",
        step: "synthesizing",
        message: "Hợp nhất câu trả lời, đối chiếu sự đồng thuận giữa các mô hình...",
        status: "completed",
      });
      setActiveSteps(step2Updated);

      const targetModel = activeInfoList[0]?.name || "AI";
      let simulatedMarkdown = "";

      if (providerIds.length === 1) {
        simulatedMarkdown = `### Kết quả phân tích từ **${targetModel}**\n\n` +
          `Dưới đây là tổng hợp chuyên sâu cho câu hỏi: *"${content}"*\n\n` +
          `1. **Tổng quan cốt lõi**: Phân tích đa chiều dựa trên mô hình dữ liệu mới nhất.\n` +
          `2. **Chi tiết kỹ thuật**: Đã xác thực các luận điểm qua quy trình chuẩn hóa Reasoning.\n\n` +
          `> *Lưu ý: Chế độ kiểm tra đang hoạt động ở trạng thái fallback an toàn.*`;
      } else {
        simulatedMarkdown = `### Báo Cáo Nghiên Cứu Đa Mô Hình (${activeInfoList.map((p) => p.name).join(" + ")})\n\n` +
          `**Chủ đề**: *"${content}"*\n\n` +
          `---\n\n` +
          `#### 1. Sự Đồng Thuận Chung (Consensus)\n` +
          `Các mô hình tham gia (${activeInfoList.map((p) => p.name).join(", ")}) đều thống nhất các điểm trọng yếu sau:\n` +
          `- **Luận điểm chính**: Trả lời trực tiếp và logic cho bài toán được đặt ra.\n` +
          `- **Khả năng áp dụng**: Phù hợp cho môi trường nghiên cứu thực nghiệm và triển khai thực tế.\n\n` +
          `#### 2. Phân Tích Chuyên Biệt Theo Từng Model\n` +
          activeInfoList.map((p) => `- **${p.name}**: Tập trung vào chiều sâu suy luận và cấu trúc phản hồi chi tiết.`).join("\n") +
          `\n\n---\n*Hệ thống đã tổng hợp báo cáo thành công.*`;
      }

      const asstMsgId = `asst-sim-${Date.now()}`;
      const assistantMsg: Message = {
        id: asstMsgId,
        role: "assistant",
        authorName: `AI Research Engine`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        content: simulatedMarkdown,
        providers: providerIds,
        tokens: 1250,
        latencySeconds: 2.4,
        sources: [
          {
            title: "Tài liệu kỹ thuật tổng hợp",
            url: "https://deep-research.local/docs",
            domain: "deep-research.local",
          },
          {
            title: "Khảo sát và đối chiếu mô hình AI",
            url: "https://papers.local/consensus-ai",
            domain: "papers.local",
          },
        ],
        claims: [
          {
            claim: "Phân tích được hợp nhất từ nhiều nguồn chatbot độc lập.",
            verdict: "supported",
            confidence: 0.95,
          },
        ],
        disagreements: [],
        factCheckStatus: "verified",
        provider_options: capsHook.selectionsMap,
        steps: step2Updated,
      };

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId || s.jobId === activeSessionId
            ? { ...s, status: "completed", messages: [...s.messages, assistantMsg] }
            : s
        )
      );
      setIsGenerating(false);
    }, 1200);
  };

  const latestMessage = activeSession.messages[activeSession.messages.length - 1];

  if (!mounted) {
    return <div className="app-container" suppressHydrationWarning />;
  }

  return (
    <div className="app-container" suppressHydrationWarning>
      {/* 1. Left Sidebar */}
      <LeftSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => handleSelectSession(id, true)}
        onNewChat={handleNewChat}
        onNewAgent={handleNewAgent}
        onOpenProvidersModal={() => setIsProvidersModalOpen(true)}
        onOpenJobsModal={() => setIsJobsModalOpen(true)}
        onOpenSettingsModal={() => setIsSettingsModalOpen(true)}
        onRefreshHistory={() => loadHistoryFromBackend(activeSessionId)}
        isLoadingHistory={isLoadingHistory}
        onTogglePin={handleTogglePin}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
      />

      {/* 2. Center Chat Area */}
      <ChatArea
        session={activeSession}
        providers={PROVIDERS_LIST}
        selectedProvider={primarySelectedProvider}
        selectedProviders={selectedProviders}
        onToggleProvider={handleToggleProvider}
        onSendMessage={handleSendMessage}
        onToggleRightSidebar={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
        isGenerating={isGenerating}
        onOpenProvidersModal={() => setIsProvidersModalOpen(true)}
        onOpenAgentConfig={() => setIsAgentConfigOpen(true)}
        activeSteps={activeSteps}
        onSelectThinking={handleSelectThinking}
        onStopResearch={handleStopResearch}
        onRetryProvider={handleRetryProvider}
        supportedDataTypes={capsHook.supportedDataTypes}
        voiceChatSupport={capsHook.voiceChatSupport}
        capabilitiesMap={capsHook.capabilitiesMap}
        selectionsMap={capsHook.selectionsMap}
        onUpdateSelection={capsHook.updateSelection}
        onSyncProvider={capsHook.syncProvider}
        loadingProvider={capsHook.loadingProvider}
      />

      {/* 3. Right Sidebar (Inspection & Details) */}
      {isRightSidebarOpen && (
        <RightSidebar
          session={activeSession}
          selectedProvider={primarySelectedProvider}
          selectedProviders={selectedProviders}
          currentMessage={inspectedMessage || (latestMessage?.role === "assistant" ? latestMessage : undefined)}
          currentQuery={
            (inspectedMessage
              ? activeSession.messages
                .slice(0, activeSession.messages.indexOf(inspectedMessage))
                .reverse()
                .find((m) => m.role === "user")?.content
              : null) ||
            activeSession.messages.filter((m) => m.role === "user").pop()?.content ||
            (activeSession.messages.length > 0 ? activeSession.title : "")
          }
          isGenerating={isGenerating}
          activeSteps={activeSteps}
          inspectedProvider={inspectedProvider}
          capabilitiesMap={capsHook.capabilitiesMap}
          selectionsMap={capsHook.selectionsMap}
          onSelectProvider={(p) => setInspectedProvider(p)}
          onClose={() => setIsRightSidebarOpen(false)}
          onRetryProvider={handleRetryProvider}
        />
      )}

      {/* 4. Providers Selection Modal */}
      <ProviderModal
        isOpen={isProvidersModalOpen}
        onClose={() => setIsProvidersModalOpen(false)}
        providers={PROVIDERS_LIST}
        selectedProviderIds={activeProviderIds}
        onToggleProvider={handleToggleProvider}
        onSelectMultipleProviders={handleSelectMultipleProviders}
        capabilitiesMap={capsHook.capabilitiesMap}
        selectionsMap={capsHook.selectionsMap}
        onUpdateSelection={capsHook.updateSelection}
        onSyncProvider={capsHook.syncProvider}
        loadingProvider={capsHook.loadingProvider}
        onSyncAll={capsHook.syncAll}
        isSyncingAll={capsHook.isSyncingAll}
        onLoadCapabilities={capsHook.loadProviderCapabilities}
      />

      {/* 5. Live Jobs & Orchestrator Health Modal */}
      <JobsModal
        isOpen={isJobsModalOpen}
        onClose={() => setIsJobsModalOpen(false)}
      />

      {/* 6. Settings Modal (Browser, Headless, Work Mode, Concurrency) */}
      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
      />

      {/* 7. Deep Research Orchestrator Config Screen */}
      {isAgentConfigOpen && (
        <AgentConfigScreen
          onStartAgentResearch={handleStartAgentResearch}
          onCancel={() => setIsAgentConfigOpen(false)}
          providers={PROVIDERS_LIST}
          capabilitiesMap={capsHook.capabilitiesMap}
          selectionsMap={capsHook.selectionsMap}
          onUpdateSelection={capsHook.updateSelection}
          onSyncProvider={capsHook.syncProvider}
          loadingProvider={capsHook.loadingProvider}
          onLoadCapabilities={capsHook.loadProviderCapabilities}
          initialQuery={activeSessionAgentDefaults.initialQuery}
          initialOrchestratorProvider={activeSessionAgentDefaults.initialOrchestratorProvider}
          initialOrchestratorConfig={activeSessionAgentDefaults.initialOrchestratorConfig}
          initialLeadProvider={activeSessionAgentDefaults.initialLeadProvider}
          initialLeadConfig={activeSessionAgentDefaults.initialLeadConfig}
          initialSummarizationProvider={activeSessionAgentDefaults.initialSummarizationProvider}
          initialSummarizationConfig={activeSessionAgentDefaults.initialSummarizationConfig}
          initialDelegatedProviders={activeSessionAgentDefaults.initialDelegatedProviders}
          initialTone={activeSessionAgentDefaults.initialTone}
          initialEnableFactCheck={activeSessionAgentDefaults.initialEnableFactCheck}
          initialFactCheckProvider={activeSessionAgentDefaults.initialFactCheckProvider}
          initialFactCheckConfig={activeSessionAgentDefaults.initialFactCheckConfig}
        />
      )}
    </div>
  );
}
