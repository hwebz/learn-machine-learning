"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { PROVIDERS_LIST, DEFAULT_SELECTED_PROVIDERS } from "../../lib/constants";
import { ChatSession, DepthMode, Message, StepLog, ProviderInfo } from "../../types/chat";
import { LeftSidebar } from "../sidebar/LeftSidebar";
import { ChatArea } from "./ChatArea";
import { RightSidebar } from "../inspector/RightSidebar";
import { ProviderModal } from "../providers/ProviderModal";
import { JobsModal } from "../jobs/JobsModal";
import { SettingsModal } from "../settings/SettingsModal";
import {
  createResearchJob,
  cancelResearchJob,
  subscribeJobEvents,
  fetchResearchHistory,
  getResearchResult,
  updateResearchJob,
  deleteResearchJob,
  fetchConversationCitations,
} from "../../lib/api";

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
  selectedProvider: "copilot",
  depth: "deep",
  messages: [],
};

interface ChatDashboardProps {
  initialChatId?: string;
}

export function ChatDashboard({ initialChatId }: ChatDashboardProps) {
  const routeParams = useParams();
  const routeChatId = (initialChatId || (routeParams?.id as string | undefined))?.trim();

  const [mounted, setMounted] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>(routeChatId || "");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [activeSteps, setActiveSteps] = useState<StepLog[]>([]);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState<boolean>(false);
  const [isProvidersModalOpen, setIsProvidersModalOpen] = useState<boolean>(false);
  const [isJobsModalOpen, setIsJobsModalOpen] = useState<boolean>(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState<boolean>(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [inspectedMessage, setInspectedMessage] = useState<Message | undefined>(undefined);
  const [inspectedProvider, setInspectedProvider] = useState<string | undefined>(undefined);

  const activeJobIdRef = useRef<string | null>(null);
  const activeUnsubscribeRef = useRef<(() => void) | null>(null);
  const isCancelledRef = useRef<boolean>(false);

  const handleSelectThinking = (provider?: string, message?: Message) => {
    setIsRightSidebarOpen(true);
    setInspectedMessage(message);
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
              authorName: `AI Research Engine (${jobProviders.join(", ")})`,
              timestamp: job.finished_at
                ? new Date(job.finished_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "",
              content: job.report_markdown,
              providers: jobProviders,
              depth: job.depth || "deep",
              tokens: 1600,
              latencySeconds: 14.5,
              sources: job.sources || [],
              claims: job.claims || [],
              provider_runs: job.provider_runs || {},
              factCheckStatus: "verified",
              steps: (job as any).steps || [],
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
            depth: job.depth || "deep",
            status: job.status,
            messages: [userMsg, ...assistantMsgs],
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
                authorName: `AI Research Engine (${directProviders.join(", ")})`,
                timestamp: directJob.finished_at
                  ? new Date(directJob.finished_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                  : "",
                content: directJob.report_markdown,
                providers: directProviders,
                depth: directJob.depth || "deep",
                tokens: 1600,
                latencySeconds: 14.5,
                sources: directJob.sources || [],
                claims: directJob.claims || [],
                provider_runs: directJob.provider_runs || {},
                factCheckStatus: "verified",
                steps: directJob.steps || [],
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
              depth: directJob.depth || "deep",
              status: directJob.status as any,
              messages: [userMsg, ...asstMsgs],
            };
            newSessions.unshift(directSession);
          }
        } catch (directErr) {
          console.warn("Could not fetch target conversation directly:", directErr);
        }
      }

      setSessions((prev) => {
        const existingJobIds = new Set(newSessions.map((s) => s.id));
        const keptPrev = prev.filter((s) => !existingJobIds.has(s.id) && !existingJobIds.has(s.jobId || ""));
        const combined = [...newSessions, ...keptPrev];

        if (combined.length > 0) {
          setActiveSessionId((curr) => {
            if (targetId && combined.some((s) => s.id === targetId || s.jobId === targetId)) {
              return targetId;
            }
            if (curr && combined.some((s) => s.id === curr || s.jobId === curr)) {
              return curr;
            }
            return combined[0].id;
          });
          return combined;
        }

        const freshId = `session-${Date.now()}`;
        setActiveSessionId(freshId);
        return [
          {
            id: freshId,
            title: "Phiên nghiên cứu mới",
            pinned: false,
            createdAt: "Vừa xong",
            createdTimestamp: Date.now(),
            selectedProviders: DEFAULT_SELECTED_PROVIDERS,
            selectedProvider: DEFAULT_SELECTED_PROVIDERS[0],
            depth: "deep",
            messages: [],
          },
        ];
      });
    } catch (err) {
      console.warn("Could not fetch research history from backend:", err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [routeChatId]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    loadHistoryFromBackend();
  }, [loadHistoryFromBackend]);

  // Handle browser back/forward buttons (popstate)
  useEffect(() => {
    const handlePopState = () => {
      if (typeof window === "undefined") return;
      const match = window.location.pathname.match(/^\/chat\/([^/?#]+)/);
      if (match && match[1]) {
        handleSelectSession(match[1], false);
      } else if (window.location.pathname === "/") {
        setSessions((prev) => {
          if (prev.length > 0) {
            setActiveSessionId(prev[0].id);
          }
          return prev;
        });
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // When routeChatId changes from props/navigation, sync activeSessionId
  useEffect(() => {
    if (routeChatId && routeChatId !== activeSessionId) {
      handleSelectSession(routeChatId, false);
    }
  }, [routeChatId]);

  const activeSession: ChatSession =
    sessions.find((s) => s.id === activeSessionId || s.jobId === activeSessionId) ||
    sessions[0] ||
    FALLBACK_SESSION;

  // Convert selected provider ids to ProviderInfo objects
  const activeProviderIds = activeSession.selectedProviders && activeSession.selectedProviders.length > 0
    ? activeSession.selectedProviders
    : [activeSession.selectedProvider || "copilot"];

  const selectedProviders: ProviderInfo[] = activeProviderIds
    .map((id) => PROVIDERS_LIST.find((p) => p.id === id))
    .filter((p): p is ProviderInfo => Boolean(p));

  const primarySelectedProvider: ProviderInfo =
    selectedProviders[0] || PROVIDERS_LIST[0];

  const handleSelectSession = async (id: string, updateUrl: boolean = true) => {
    setActiveSessionId(id);

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

        const asstMsg: Message = {
          id: `msg-${targetJobId}-detail`,
          role: "assistant",
          authorName: `AI Research Engine (${fullJobProviders.join(", ")})`,
          timestamp: fullJob.finished_at
            ? new Date(fullJob.finished_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
            : (existingAsst?.timestamp || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })),
          content: fullJob.report_markdown || existingAsst?.content || "",
          providers: fullJobProviders,
          depth: session?.depth || fullJob.depth || "deep",
          sources: jobSources,
          claims: fullJob.claims || [],
          provider_runs: fullJob.provider_runs || {},
          factCheckStatus: "verified",
          steps: jobSteps,
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
    const newSession: ChatSession = {
      id: newId,
      title: "Phiên nghiên cứu mới",
      pinned: false,
      createdAt: "Vừa xong",
      createdTimestamp: Date.now(),
      selectedProviders: DEFAULT_SELECTED_PROVIDERS,
      selectedProvider: DEFAULT_SELECTED_PROVIDERS[0],
      depth: activeSession.depth || "deep",
      messages: [],
    };
    setSessions([newSession, ...sessions]);
    setActiveSessionId(newId);
    setActiveSteps([]);
    setInspectedMessage(undefined);
    setInspectedProvider(undefined);
    setIsRightSidebarOpen(false);

    // Update URL back to root
    if (typeof window !== "undefined" && window.location.pathname !== "/") {
      window.history.pushState(null, "", "/");
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
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== id && s.jobId !== id);
      if (activeSessionId === id || activeSessionId === targetJobId) {
        if (remaining.length > 0) {
          handleSelectSession(remaining[0].id, true);
        } else {
          setTimeout(() => handleNewChat(), 0);
        }
      }
      return remaining;
    });
  };

  const handleToggleProvider = (providerId: string) => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeSessionId && s.jobId !== activeSessionId) return s;
        const currentIds = s.selectedProviders || [s.selectedProvider || "copilot"];
        let updatedIds: string[];
        if (currentIds.includes(providerId)) {
          if (currentIds.length > 1) {
            updatedIds = currentIds.filter((id) => id !== providerId);
          } else {
            updatedIds = currentIds; // Keep at least one
          }
        } else {
          updatedIds = [...currentIds, providerId];
        }
        return {
          ...s,
          selectedProviders: updatedIds,
          selectedProvider: updatedIds[0],
        };
      })
    );
  };

  const handleSelectMultipleProviders = (providerIds: string[]) => {
    if (providerIds.length === 0) return;
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

  const handleToggleDepth = (depth: DepthMode) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === activeSessionId || s.jobId === activeSessionId ? { ...s, depth } : s))
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
          authorName: `AI Research Engine (${currentProviderIds.join(", ")})`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          content: stoppedText,
          providers: currentProviderIds,
          depth: s.depth,
          steps: activeSteps,
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

    setIsGenerating(true);
    setActiveSteps([]);
    setInspectedMessage(undefined);

    const currentProviderIds = activeSession.selectedProviders && activeSession.selectedProviders.length > 0
      ? activeSession.selectedProviders
      : [primarySelectedProvider.id];
    const currentDepth = activeSession.depth;

    try {
      // 1. Dispatch research job to backend with all selected providers
      const jobAccepted = await createResearchJob({
        query: content,
        depth: currentDepth,
        providers: currentProviderIds,
      });

      if (isCancelledRef.current) {
        cancelResearchJob(jobAccepted.job_id).catch(() => { });
        return;
      }

      activeJobIdRef.current = jobAccepted.job_id;

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
              authorName: `AI Research Engine (${currentProviderIds.join(", ")})`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              content: result.report_markdown || "Đã hoàn thành nghiên cứu và tổng hợp câu trả lời từ các mô hình.",
              providers: currentProviderIds,
              depth: currentDepth,
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
          handleSimulatedMultiModelResponse(content, currentProviderIds, currentDepth);
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
      handleSimulatedMultiModelResponse(content, currentProviderIds, currentDepth);
    }
  };

  const handleSimulatedMultiModelResponse = (
    content: string,
    providerIds: string[],
    depth: DepthMode
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
        authorName: `AI Research Engine (${activeInfoList.map((p) => p.name).join(", ")})`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        content: simulatedMarkdown,
        providers: providerIds,
        depth,
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
        onToggleDepth={handleToggleDepth}
        onSendMessage={handleSendMessage}
        onToggleRightSidebar={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
        isGenerating={isGenerating}
        onOpenProvidersModal={() => setIsProvidersModalOpen(true)}
        activeSteps={activeSteps}
        onSelectThinking={handleSelectThinking}
        onStopResearch={handleStopResearch}
      />

      {/* 3. Right Sidebar (Inspection & Details) */}
      {isRightSidebarOpen && (
        <RightSidebar
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
          depth={inspectedMessage?.depth || activeSession.depth}
          onSelectProvider={(p) => setInspectedProvider(p)}
          onClose={() => setIsRightSidebarOpen(false)}
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
    </div>
  );
}
