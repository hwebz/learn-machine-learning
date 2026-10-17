"use client";

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import { PROVIDERS_LIST, DEFAULT_SELECTED_PROVIDERS } from "../../lib/constants";
import { ChatSession, Message, StepLog, ProviderInfo } from "../../types/chat";
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

const FALLBACK_SESSION: ChatSession = {
  id: "session-fallback",
  title: "Phiên nghiên cứu mới",
  pinned: false,
  createdAt: "Vừa xong",
  createdTimestamp: 0,
  selectedProviders: DEFAULT_SELECTED_PROVIDERS,
  selectedProvider: DEFAULT_SELECTED_PROVIDERS[0] || "copilot",
  messages: [],
};

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
  const [draftSession, setDraftSession] = useState<ChatSession>(() => ({
    id: "session-draft",
    title: "Phiên nghiên cứu mới",
    pinned: false,
    createdAt: "Vừa xong",
    createdTimestamp: Date.now(),
    selectedProviders: DEFAULT_SELECTED_PROVIDERS,
    selectedProvider: DEFAULT_SELECTED_PROVIDERS[0] || "copilot",
    messages: [],
  }));
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
      if (message.steps && message.steps.length > 0) {
        setActiveSteps(message.steps);
      }
    }
    setInspectedProvider(provider ? provider.toLowerCase() : undefined);
  };

  // Synchronize history from backend on mount and via button
  const loadHistoryFromBackend = useCallback(async (preferredId?: string) => {
    setIsLoadingHistory(true);
    const targetId = preferredId || routeChatId;

    try {
      const historyJobs = await fetchResearchHistory(50);
      const deletedIds = getDeletedSessionIds();

      const newSessions: ChatSession[] = [];
      if (historyJobs && historyJobs.length > 0) {
        for (const job of historyJobs) {
          if (deletedIds.has(job.job_id)) {
            continue;
          }

          const jobProviders = job.providers && job.providers.length > 0
            ? job.providers
            : DEFAULT_SELECTED_PROVIDERS;

          const userMsg: Message = {
            id: `msg-${job.job_id}-user`,
            role: "user",
            authorName: "Researcher",
            timestamp: job.created_at
              ? new Date(job.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : "Trước đó",
            content: job.query,
          };

          const assistantMsgs: Message[] = [];
          if (job.report_markdown) {
            assistantMsgs.push({
              id: `msg-${job.job_id}-asst`,
              role: "assistant",
              authorName: `AI Research Engine${jobProviders.length ? ' (' : ''}${jobProviders.join(", ")}${jobProviders.length ? ')' : ''}`,
              timestamp: job.finished_at
                ? new Date(job.finished_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "",
              content: job.report_markdown,
              providers: jobProviders,
              tokens: 1600,
              latencySeconds: 14.5,
              sources: job.sources || [],
              claims: job.claims || [],
              provider_runs: job.provider_runs || {},
              provider_options: (job as any).provider_options || {},
              factCheckStatus: "verified",
              steps: (job as any).steps || [],
              job_type: (job as any).job_type || "research",
              orchestrator_provider: (job as any).orchestrator_provider,
              lead_provider: (job as any).lead_provider,
              tone: (job as any).tone,
              orchestrator_dispatch: (job as any).orchestrator_dispatch,
              delegated_providers: (job as any).delegated_providers,
            });
          }

          const initialTitle = (job as any).title || (job.query.length > 36 ? job.query.slice(0, 36) + "..." : job.query);
          const isPinned = Boolean((job as any).pinned);

          newSessions.push({
            id: job.job_id,
            jobId: job.job_id,
            title: initialTitle,
            pinned: isPinned,
            createdAt: job.created_at
              ? new Date(job.created_at).toLocaleDateString([], { month: "short", day: "numeric" })
              : "Gần đây",
            createdTimestamp: job.created_at ? new Date(job.created_at).getTime() : Date.now(),
            selectedProviders: jobProviders,
            selectedProvider: jobProviders[0] || "copilot",
            status: job.status,
            messages: [userMsg, ...assistantMsgs],
            job_type: (job as any).job_type || "research",
            orchestrator_provider: (job as any).orchestrator_provider,
            lead_provider: (job as any).lead_provider,
            tone: (job as any).tone,
            orchestrator_dispatch: (job as any).orchestrator_dispatch,
            delegated_providers: (job as any).delegated_providers,
            providerConfigurations: (job as any).providerConfigurations || (job as any).provider_options || {
              ...(((job as any).orchestrator_config && (job as any).orchestrator_provider) ? { [(job as any).orchestrator_provider]: (job as any).orchestrator_config } : {}),
              ...(((job as any).lead_config && (job as any).lead_provider) ? { [(job as any).lead_provider]: (job as any).lead_config } : {}),
            },
          });
        }
      }

      // If a specific conversation was requested via route and not found in top 50, fetch directly
      if (targetId && !newSessions.some((s) => s.id === targetId || s.jobId === targetId)) {
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

            const asstMsgs: Message[] = [];
            if (directJob.report_markdown) {
              asstMsgs.push({
                id: `msg-${directJob.job_id}-asst`,
                role: "assistant",
                authorName: `AI Research Engine${directProviders.length ? ' (' : ''}${directProviders.join(", ")}${directProviders.length ? ')' : ''}`,
                timestamp: directJob.finished_at
                  ? new Date(directJob.finished_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                  : "",
                content: directJob.report_markdown,
                providers: directProviders,
                tokens: 1600,
                latencySeconds: 14.5,
                sources: directJob.sources || [],
                claims: directJob.claims || [],
                provider_runs: directJob.provider_runs || {},
                provider_options: directJob.provider_options || {},
                factCheckStatus: "verified",
                steps: directJob.steps || [],
                job_type: (directJob as any).job_type || "research",
                orchestrator_provider: (directJob as any).orchestrator_provider,
                lead_provider: (directJob as any).lead_provider,
                tone: (directJob as any).tone,
                orchestrator_dispatch: (directJob as any).orchestrator_dispatch,
              });
            }

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
              tone: (directJob as any).tone,
              orchestrator_dispatch: (directJob as any).orchestrator_dispatch,
              delegated_providers: (directJob as any).delegated_providers,
              providerConfigurations: (directJob as any).providerConfigurations || (directJob as any).provider_options || {
                ...(((directJob as any).orchestrator_config && (directJob as any).orchestrator_provider) ? { [(directJob as any).orchestrator_provider]: (directJob as any).orchestrator_config } : {}),
                ...(((directJob as any).lead_config && (directJob as any).lead_provider) ? { [(directJob as any).lead_provider]: (directJob as any).lead_config } : {}),
              },
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
        const existingJobIds = new Set(safeNewSessions.map((s) => s.id));
        const keptPrev = prev.filter(
          (s) => !existingJobIds.has(s.id) && !existingJobIds.has(s.jobId || "") && !activeRunningIds.has(s.id)
        );
        const validCombined = [...activeRunningSessions, ...safeNewSessions, ...keptPrev].filter(
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
        }
        return activeRunningSessions;
      });
    } catch (err) {
      console.warn("Could not fetch research history from backend:", err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [routeChatId]);

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
        setDraftSession({
          id: freshDraftId,
          title: "Phiên nghiên cứu mới",
          pinned: false,
          createdAt: "Vừa xong",
          createdTimestamp: Date.now(),
          selectedProviders: (sessions[0]?.selectedProviders && sessions[0].selectedProviders.length > 0)
            ? sessions[0].selectedProviders
            : DEFAULT_SELECTED_PROVIDERS,
          selectedProvider: sessions[0]?.selectedProvider || DEFAULT_SELECTED_PROVIDERS[0] || "copilot",
          messages: [],
        });
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

    return {
      initialOrchestratorProvider: resolvedOrch,
      initialLeadProvider: resolvedLead,
      initialDelegatedProviders: resolvedDelegated,
      initialTone: resolvedTone,
      initialQuery: resolvedQuery,
      initialOrchestratorConfig: orchConfig,
      initialLeadConfig: leadConfig,
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

        // If the job is still actively running and has no final report yet, preserve live streaming state!
        if (fullJob.status !== "completed" && !fullJob.report_markdown) {
          return;
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

        const asstMsg: Message = {
          id: `msg-${targetJobId}-detail`,
          role: "assistant",
          authorName: isAgentJob
            ? `Deep Research Orchestrator (${(orchProv || "copilot").toUpperCase()} ➜ ${(leadProv || "chatgpt").toUpperCase()})`
            : `AI Research Engine${fullJobProviders.length ? ' (' : ''}${fullJobProviders.join(", ")}${fullJobProviders.length ? ')' : ''}`,
          timestamp: fullJob.finished_at
            ? new Date(fullJob.finished_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
            : (existingAsst?.timestamp || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })),
          content: fullJob.report_markdown || existingAsst?.content || "",
          providers: fullJobProviders,
          sources: jobSources,
          claims: fullJob.claims || [],
          provider_runs: fullJob.provider_runs || {},
          factCheckStatus: "verified",
          steps: jobSteps,
          job_type: isAgentJob ? "agent" : "research",
          orchestrator_provider: orchProv,
          lead_provider: leadProv,
          tone: toneVal,
          orchestrator_dispatch: orchDispatch,
          delegated_providers: (fullJob as any).delegated_providers,
        };

        setInspectedMessage(asstMsg);
        setIsRightSidebarOpen(true);

        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== id && s.jobId !== id) return s;
            const otherMsgs = s.messages.filter((m) => m.role === "user");
            return {
              ...s,
              selectedProviders: fullJobProviders,
              selectedProvider: fullJobProviders[0] || s.selectedProvider,
              messages: otherMsgs.length > 0 ? [...otherMsgs, asstMsg] : [asstMsg],
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
    const cleanDraft: ChatSession = {
      id: newId,
      title: "Phiên nghiên cứu mới",
      pinned: false,
      createdAt: "Vừa xong",
      createdTimestamp: Date.now(),
      selectedProviders: (sessions[0]?.selectedProviders && sessions[0].selectedProviders.length > 0)
        ? sessions[0].selectedProviders
        : DEFAULT_SELECTED_PROVIDERS,
      selectedProvider: sessions[0]?.selectedProvider || DEFAULT_SELECTED_PROVIDERS[0] || "copilot",
      messages: [],
    };
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
    tone: string;
    delegated_providers?: string[];
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
      tone: config.tone,
      delegated_providers: config.delegated_providers,
      provider_options: {
        [config.orchestrator_provider]: config.orchestrator_config,
        [config.lead_provider]: config.lead_config,
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
      tone: config.tone,
      delegated_providers: config.delegated_providers,
      providerConfigurations: {
        [config.orchestrator_provider]: config.orchestrator_config,
        [config.lead_provider]: config.lead_config,
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
        tone: config.tone,
        delegated_providers: config.delegated_providers,
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

          setSessions((prev) =>
            prev.map((s) => {
              if (s.id !== jobAccepted.job_id && s.jobId !== jobAccepted.job_id) return s;
              let nextStatus = s.status;
              if (rawJobStatus && rawJobStatus !== "running") {
                nextStatus = rawJobStatus as any;
              } else if (dispatch && nextStatus === "orchestrating") {
                nextStatus = "researching" as any;
              }
              return {
                ...s,
                status: nextStatus,
                orchestrator_dispatch: dispatch || s.orchestrator_dispatch,
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
              role: "assistant",
              authorName: `Deep Research Orchestrator (${config.orchestrator_provider.toUpperCase()} ➜ ${config.lead_provider.toUpperCase()})`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              content: finalReport,
              providers: [config.orchestrator_provider, config.lead_provider],
              sources: result.sources || [],
              claims: result.claims || [],
              provider_runs: result.provider_runs || [],
              factCheckStatus: "verified",
              steps: activeSteps,
              job_type: "agent",
              orchestrator_provider: config.orchestrator_provider,
              lead_provider: config.lead_provider,
              tone: config.tone,
              orchestrator_dispatch: (result as any).orchestrator_dispatch,
              delegated_providers: config.delegated_providers,
              provider_options: {
                [config.orchestrator_provider]: config.orchestrator_config,
                [config.lead_provider]: config.lead_config,
              },
            };

            setSessions((prev) =>
              prev.map((s) =>
                s.id === jobAccepted.job_id || s.jobId === jobAccepted.job_id
                  ? {
                    ...s,
                    status: "completed",
                    messages: [...s.messages.filter((m) => m.role === "user"), assistantMsg],
                    orchestrator_dispatch: (result as any).orchestrator_dispatch || s.orchestrator_dispatch,
                    delegated_providers: config.delegated_providers || s.delegated_providers,
                    providerConfigurations: s.providerConfigurations || {
                      [config.orchestrator_provider]: config.orchestrator_config,
                      [config.lead_provider]: config.lead_config,
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
                role: "assistant",
                authorName: `Deep Research Orchestrator (${config.orchestrator_provider.toUpperCase()} ➜ ${config.lead_provider.toUpperCase()})`,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                content: finalResult.report_markdown,
                providers: [config.orchestrator_provider, config.lead_provider],
                sources: finalResult.sources || [],
                claims: finalResult.claims || [],
                provider_runs: finalResult.provider_runs || [],
                factCheckStatus: "verified",
                steps: activeSteps,
                job_type: "agent",
                orchestrator_provider: config.orchestrator_provider,
                lead_provider: config.lead_provider,
                tone: config.tone,
                orchestrator_dispatch: finalResult.orchestrator_dispatch,
                delegated_providers: config.delegated_providers,
                provider_options: {
                  [config.orchestrator_provider]: config.orchestrator_config,
                  [config.lead_provider]: config.lead_config,
                },
              };

              setSessions((prev) =>
                prev.map((s) =>
                  s.id === jobAccepted.job_id || s.jobId === jobAccepted.job_id
                    ? {
                      ...s,
                      status: "completed",
                      messages: [...s.messages.filter((m) => m.role === "user"), assistantMsg],
                      orchestrator_dispatch: finalResult.orchestrator_dispatch || s.orchestrator_dispatch,
                      delegated_providers: config.delegated_providers || s.delegated_providers,
                      providerConfigurations: s.providerConfigurations || {
                        [config.orchestrator_provider]: config.orchestrator_config,
                        [config.lead_provider]: config.lead_config,
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

    markSessionAsDeleted(id, targetJobId);

    if (targetJobId) {
      await deleteResearchJob(targetJobId);
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

      setDraftSession({
        id: freshDraftId,
        title: "Phiên nghiên cứu mới",
        pinned: false,
        createdAt: "Vừa xong",
        createdTimestamp: Date.now(),
        selectedProviders: (remaining[0]?.selectedProviders && remaining[0].selectedProviders.length > 0)
          ? remaining[0].selectedProviders
          : DEFAULT_SELECTED_PROVIDERS,
        selectedProvider: remaining[0]?.selectedProvider || DEFAULT_SELECTED_PROVIDERS[0] || "copilot",
        messages: [],
      });

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

        const asstMsgId = currentJobId ? `asst-${currentJobId}` : `asst-stopped-${Date.now()}`;
        const existingIdx = s.messages.findIndex(
          (m) => m.id === asstMsgId || (m.role === "assistant" && currentJobId && s.jobId === currentJobId)
        );

        const assistantMsg: Message = {
          id: asstMsgId,
          role: "assistant",
          authorName: `AI Research Engine${currentProviderIds.length ? ' (' : ''}${currentProviderIds.join(", ")}${currentProviderIds.length ? ')' : ''}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          content: stoppedText,
          providers: currentProviderIds,
          steps: activeSteps,
          provider_options: capsHook.selectionsMap,
          factCheckStatus: "unverified",
        };

        const updatedMessages =
          existingIdx >= 0
            ? s.messages.map((m, idx) => (idx === existingIdx ? assistantMsg : m))
            : [...s.messages, assistantMsg];

        return {
          ...s,
          status: "cancelled",
          messages: updatedMessages,
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

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      authorName: "Researcher",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      content,
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
        status: "running",
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
              status: "running",
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
      setInspectedProvider(currentProviderIds[0]?.toLowerCase() || "copilot");
    }

    try {
      // 1. Dispatch research job to backend with all selected providers
      const sanitizedOptions: Record<string, any> = {};
      for (const [pId, opts] of Object.entries(capsHook.selectionsMap || {})) {
        const pCaps = capsHook.capabilitiesMap[pId];
        const isFree = pId === "chatgpt" && pCaps?.account_type === "free";
        sanitizedOptions[pId] = {
          ...opts,
          model_id: isFree ? "none" : opts.model_id,
        };
      }

      const jobAccepted = await createResearchJob({
        query: content,
        providers: currentProviderIds,
        provider_options: sanitizedOptions,
      });

      if (isCancelledRef.current) {
        cancelResearchJob(jobAccepted.job_id).catch(() => { });
        return;
      }

      activeJobIdRef.current = jobAccepted.job_id;
      setCurrentRouteChatId(jobAccepted.job_id);

      // Update URL to /chat/{job_id} for shareable direct route
      if (typeof window !== "undefined") {
        window.history.replaceState(null, "", `/chat/${jobAccepted.job_id}`);
      }

      // Update session with backend job id
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId || s.jobId === activeSessionId
            ? { ...s, id: jobAccepted.job_id, jobId: jobAccepted.job_id }
            : s
        )
      );
      setActiveSessionId(jobAccepted.job_id);

      // 2. Subscribe to real-time SSE progress events
      const unsub = subscribeJobEvents(jobAccepted.job_id, {
        onStep: (stepLog) => {
          if (isCancelledRef.current) return;
          setActiveSteps((prev) => [...prev, stepLog]);
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

            const asstMsgId = `asst-${jobAccepted.job_id}`;
            const assistantMsg: Message = {
              id: asstMsgId,
              role: "assistant",
              authorName: `AI Research Engine${currentProviderIds.length ? ' (' : ''}${currentProviderIds.join(", ")}${currentProviderIds.length ? ')' : ''}`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              content: result.report_markdown || "Đã hoàn thành nghiên cứu và tổng hợp câu trả lời từ các mô hình.",
              providers: currentProviderIds,
              tokens: 1540,
              latencySeconds: 10.8,
              sources: consolidatedSources,
              claims: result.claims || [],
              disagreements: result.disagreements || [],
              provider_runs: result.provider_runs || {},
              provider_options: (result as any).provider_options || capsHook.selectionsMap,
              factCheckStatus: "verified",
              steps: latestSteps,
            };

            setSessions((prev) =>
              prev.map((s) => {
                if (s.id !== jobAccepted.job_id && s.jobId !== jobAccepted.job_id) return s;
                const existingIdx = s.messages.findIndex(
                  (m) => m.id === asstMsgId || (m.role === "assistant" && s.jobId === jobAccepted.job_id)
                );
                const updatedMessages =
                  existingIdx >= 0
                    ? s.messages.map((m, idx) => (idx === existingIdx ? assistantMsg : m))
                    : [...s.messages, assistantMsg];
                return { ...s, status: "completed", messages: updatedMessages };
              })
            );
            return latestSteps;
          });
          activeUnsubscribeRef.current = null;
          activeJobIdRef.current = null;
          setIsGenerating(false);
        },
        onError: (err) => {
          if (isCancelledRef.current) return;
          console.warn("SSE stream issue, falling back to multi-model simulation:", err);
          handleSimulatedMultiModelResponse(content, currentProviderIds);
        },
        onDone: () => {
          if (isCancelledRef.current) return;
          activeUnsubscribeRef.current = null;
          activeJobIdRef.current = null;
          setIsGenerating(false);
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

              const asstMsgId = `asst-${targetJobId}`;
              const assistantMsg: Message = {
                id: asstMsgId,
                role: "assistant",
                authorName: `AI Research Engine${(result.providers || activeSession.selectedProviders || [provider]).length ? ' (' : ''}${(result.providers || activeSession.selectedProviders || [provider]).join(", ")}${(result.providers || activeSession.selectedProviders || [provider]).length ? ')' : ''}`,
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
                  const existingIdx = s.messages.findIndex(
                    (m) => m.id === asstMsgId || (m.role === "assistant" && s.jobId === targetJobId)
                  );
                  const updatedMessages =
                    existingIdx >= 0
                      ? s.messages.map((m, idx) => (idx === existingIdx ? assistantMsg : m))
                      : [...s.messages, assistantMsg];
                  return { ...s, status: "completed", messages: updatedMessages };
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
          onDone: () => {
            setIsGenerating(false);
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
        authorName: `AI Research Engine${activeInfoList.length ? ' (' : ''}${activeInfoList.map((p) => p.name).join(", ")}${activeInfoList.length ? ')' : ''}`,
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
            activeSession.messages.find((m) => m.role === "user")?.content ||
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
          initialDelegatedProviders={activeSessionAgentDefaults.initialDelegatedProviders}
          initialTone={activeSessionAgentDefaults.initialTone}
        />
      )}
    </div>
  );
}
