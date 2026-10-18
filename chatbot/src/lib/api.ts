import { DepthMode, SourceLink, StepLog, ProviderLiveCapabilities } from "../types/chat";

const DEFAULT_API_KEY = "changeme";

export interface ResearchRequestPayload {
  query: string;
  depth?: DepthMode;
  providers: string[];
  max_sources_per_provider?: number;
  provider_options?: Record<string, any>;
}

export interface ResearchResponseData {
  job_id: string;
  status: string;
  progress: { subtasks_total: number; subtasks_done: number };
  report_markdown: string;
  sources: SourceLink[];
  claims: any[];
  disagreements: any[];
  provider_runs: any[];
  error?: string | null;
  query?: string;
  title?: string;
  depth?: DepthMode;
  providers?: string[];
  provider_options?: Record<string, any>;
  created_at?: string;
  finished_at?: string;
  steps?: StepLog[];
  job_type?: "research" | "agent";
  orchestrator_provider?: string;
  lead_provider?: string;
  tone?: string;
  orchestrator_dispatch?: any[];
  delegated_providers?: string[];
  orchestrator_config?: Record<string, any>;
  lead_config?: Record<string, any>;
  providerConfigurations?: Record<string, any>;
}

export interface ResearchHistoryItem {
  job_id: string;
  query: string;
  status: "queued" | "running" | "completed" | "partial" | "failed" | "cancelled" | "orchestrating" | "leading";
  subtasks_total: number;
  subtasks_done: number;
  report_markdown: string;
  sources: SourceLink[];
  claims: any[];
  provider_runs: Record<string, any>;
  provider_options?: Record<string, any>;
  error?: string | null;
  depth?: DepthMode;
  providers: string[];
  job_type?: "research" | "agent";
  orchestrator_provider?: string;
  lead_provider?: string;
  tone?: string;
  orchestrator_dispatch?: any[];
  delegated_providers?: string[];
  orchestrator_config?: Record<string, any>;
  lead_config?: Record<string, any>;
  providerConfigurations?: Record<string, any>;
  created_at?: string;
  finished_at?: string;
}

export interface AgentResearchRequestPayload {
  query: string;
  orchestrator_provider: string;
  orchestrator_config?: Record<string, any>;
  lead_provider: string;
  lead_config?: Record<string, any>;
  tone: string;
  max_minutes?: number;
  delegated_providers?: string[];
  provider_configs?: Record<string, any>;
  provider_capabilities?: Record<string, any>;
}

export async function createAgentResearchJob(
  payload: AgentResearchRequestPayload,
  apiKey: string = DEFAULT_API_KEY
): Promise<{ job_id: string }> {
  const res = await fetch("/api/backend/agent-research", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Lỗi máy chủ (${res.status})`);
  }
  return await res.json();
}

export async function fetchResearchHistory(
  limit: number = 40,
  apiKey: string = DEFAULT_API_KEY
): Promise<ResearchHistoryItem[]> {
  try {
    const res = await fetch(`/api/backend/research?limit=${limit}`, {
      method: "GET",
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    return await res.json();
  } catch {
    return [];
  }
}

export async function checkBackendHealth(): Promise<{ online: boolean; data?: any }> {
  try {
    const res = await fetch("/api/backend/health", {
      method: "GET",
      cache: "no-store",
    });
    if (!res.ok) return { online: false };
    const data = await res.json();
    return { online: true, data };
  } catch {
    return { online: false };
  }
}

export async function createResearchJob(
  payload: ResearchRequestPayload,
  apiKey: string = DEFAULT_API_KEY
): Promise<{ job_id: string }> {
  const res = await fetch("/api/backend/research", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to create research job: ${res.status} ${errText}`);
  }

  return await res.json();
}

export async function getResearchResult(
  jobId: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<ResearchResponseData | null> {
  try {
    const res = await fetch(`/api/backend/research/${jobId}`, {
      method: "GET",
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });

    if (!res.ok) {
      return null;
    }

    return await res.json();
  } catch {
    return null;
  }
}

export async function updateResearchJob(
  jobId: string,
  payload: { title?: string; pinned?: boolean },
  apiKey: string = DEFAULT_API_KEY
): Promise<void> {
  try {
    await fetch(`/api/backend/research/${jobId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("Error updating research job on backend:", err);
  }
}

export async function deleteResearchJob(
  jobId: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<boolean> {
  try {
    const res = await fetch(`/api/backend/research/${jobId}`, {
      method: "DELETE",
      headers: {
        "X-API-Key": apiKey,
      },
      keepalive: true,
    });
    if (!res.ok && res.status !== 404) {
      console.warn("Failed to delete research job on backend:", res.status);
      return false;
    }
    return true;
  } catch (err) {
    console.warn("Error deleting research job on backend:", err);
    return false;
  }
}

export async function cancelResearchJob(
  jobId: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<boolean> {
  try {
    const res = await fetch(`/api/backend/research/${jobId}/cancel`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
      },
    });
    return res.ok || res.status === 204;
  } catch (err) {
    console.warn("Error cancelling research job on backend:", err);
    return false;
  }
}

export interface SSECallbacks {
  onStep: (stepLog: StepLog) => void;
  onProgress?: (progress: { subtasks_total: number; subtasks_done: number; status?: string }) => void;
  onStatus?: (status: string) => void;
  onResult: (result: ResearchResponseData) => void;
  onError: (err: string) => void;
  onDone: () => void;
}

/**
 * Subscribe to real-time SSE stream for a research job.
 * Uses Next.js API route proxy with EventSource, plus ReadableStream fallback.
 */
export function subscribeJobEvents(
  jobId: string,
  callbacks: SSECallbacks
): () => void {
  let isClosed = false;
  let resultDelivered = false;
  let eventSource: EventSource | null = null;
  let abortController: AbortController | null = null;

  const handleMessageData = (dataStr: string) => {
    try {
      const data = JSON.parse(dataStr);

      if (data.status && callbacks.onStatus) {
        callbacks.onStatus(data.status);
      }

      if (data.progress && callbacks.onProgress) {
        callbacks.onProgress({ ...data.progress, status: data.status });
      }

      if (data.message || data.step || data.event_type === "orchestrator_result") {
        const payloadData = data.data || {};
        const stepLog: StepLog = {
          id: data.id || (data.event_id ? `event-${data.event_id}` : `step-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`),
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
          provider: data.provider,
          step: data.step || data.event_type,
          message: data.message || `Processing on ${data.provider || "orchestrator"}...`,
          status:
            data.status === "completed"
              ? "completed"
              : data.status === "failed" || data.status === "error"
              ? "error"
              : data.status === "orchestrating" || data.status === "researching" || data.status === "leading"
              ? (data.status as any)
              : "running",
          data: {
            ...payloadData,
            job_status: data.status,
            event_type: data.event_type,
          },
          thinkingText: payloadData.thinking_text || undefined,
          thinkingSteps: payloadData.thinking_steps || undefined,
          citations: payloadData.citations || undefined,
          isThinking: Boolean(payloadData.is_thinking || data.event_type === "thinking"),
          streamingText: payloadData.streaming_text || payloadData.text_preview || undefined,
        };
        callbacks.onStep(stepLog);
      }

      // If payload is an explicit full result object with provider_runs
      if (data.event_type === "result" && data.data && typeof data.data === "object" && data.data.report_markdown && data.data.provider_runs) {
        if (!resultDelivered) {
          resultDelivered = true;
          callbacks.onResult(data.data);
        }
      }
    } catch (err) {
      console.warn("Failed to parse SSE payload:", err);
    }
  };

  // Try 1: EventSource via Next.js Proxy
  try {
    const proxyUrl = `/api/research/${jobId}/events`;
    eventSource = new EventSource(proxyUrl);

    eventSource.onmessage = (e) => {
      handleMessageData(e.data);
    };

    const sseEventNames = [
      "step",
      "thinking",
      "progress",
      "result",
      "orchestrator_result",
      "agent_status",
      "status",
      "completed",
    ];
    for (const evtName of sseEventNames) {
      eventSource.addEventListener(evtName, (e: MessageEvent) => {
        handleMessageData(e.data);
      });
    }

    eventSource.addEventListener("done", async () => {
      if (isClosed) return;
      isClosed = true;
      eventSource?.close();
      try {
        const finalResult = await getResearchResult(jobId);
        if (finalResult) {
          resultDelivered = true;
          callbacks.onResult(finalResult);
        }
      } catch (err: any) {
        if (!resultDelivered) {
          callbacks.onError(err?.message || "Failed to fetch final research result");
        }
      }
      callbacks.onDone();
    });

    eventSource.onerror = (err) => {
      console.warn("EventSource proxy error, attempting direct stream reader fallback...", err);
      eventSource?.close();
      eventSource = null;
      if (!isClosed) {
        startStreamReaderFallback();
      }
    };
  } catch {
    startStreamReaderFallback();
  }

  // Fallback: Fetch ReadableStream with explicit X-API-Key header
  async function startStreamReaderFallback() {
    if (isClosed) return;
    abortController = new AbortController();

    try {
      const response = await fetch(`/api/backend/research/${jobId}/events`, {
        headers: {
          "X-API-Key": DEFAULT_API_KEY,
          Accept: "text/event-stream",
        },
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`SSE HTTP error ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (!isClosed) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          const blockLines = block.split("\n");
          let eventType = "message";
          let dataStr = "";

          for (const line of blockLines) {
            if (line.startsWith("event: ")) {
              eventType = line.replace("event: ", "").trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.replace("data: ", "").trim();
            }
          }

          if (eventType === "done") {
            isClosed = true;
            try {
              const finalResult = await getResearchResult(jobId);
              if (finalResult) {
                resultDelivered = true;
                callbacks.onResult(finalResult);
              }
            } catch (err: any) {
              if (!resultDelivered) {
                callbacks.onError(err?.message || "Failed to load final result");
              }
            }
            callbacks.onDone();
            return;
          }

          if (dataStr) {
            handleMessageData(dataStr);
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError" && !isClosed) {
        callbacks.onError(err.message || "SSE stream connection lost");
      }
    }
  }

  return () => {
    isClosed = true;
    if (eventSource) {
      eventSource.close();
    }
    if (abortController) {
      abortController.abort();
    }
  };
}

export async function fetchConversationCitations(
  jobId: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<SourceLink[]> {
  try {
    const res = await fetch(`/api/backend/research/${jobId}/sources`, {
      method: "GET",
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn("Failed to fetch conversation citations:", err);
    return [];
  }
}

export interface AvailableBrowser {
  id: string;
  name: string;
  channel?: string;
  path?: string;
  executable_path?: string | null;
  is_machine_default: boolean;
  is_default: boolean;
}

export interface AppSettings {
  available_browsers: AvailableBrowser[];
  browser: string;
  work_mode: "async" | "sync";
  max_concurrent_browsers: number;
  headless_providers: Record<string, boolean>;
}

export interface AppSettingsUpdatePayload {
  browser?: string;
  browser_executable?: string | null;
  work_mode?: "async" | "sync";
  max_concurrent_browsers?: number;
  headless_providers?: Record<string, boolean>;
}

export async function fetchSettings(
  apiKey: string = DEFAULT_API_KEY
): Promise<AppSettings | null> {
  try {
    const res = await fetch("/api/backend/settings", {
      method: "GET",
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn("Failed to fetch settings:", err);
    return null;
  }
}

export async function updateSettings(
  payload: AppSettingsUpdatePayload,
  apiKey: string = DEFAULT_API_KEY
): Promise<AppSettings | null> {
  try {
    const res = await fetch("/api/backend/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to update settings:", err);
    return null;
  }
}

export async function openProviderBrowser(
  provider: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<{ status: string; url?: string; message?: string }> {
  const res = await fetch(`/api/backend/providers/${encodeURIComponent(provider)}/open-browser`, {
    method: "POST",
    headers: {
      "X-API-Key": apiKey,
    },
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to open browser for ${provider}: ${res.status} ${errText}`);
  }
  return await res.json();
}

export async function closeProviderBrowser(
  provider: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<{ status: string; message?: string }> {
  const res = await fetch(`/api/backend/providers/${encodeURIComponent(provider)}/close-browser`, {
    method: "POST",
    headers: {
      "X-API-Key": apiKey,
    },
  });
  if (!res.ok) {
    return { status: "error", message: `HTTP ${res.status}` };
  }
  return await res.json();
}

export async function getProviderBrowserStatus(
  provider: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<{ is_open: boolean }> {
  try {
    const res = await fetch(`/api/backend/providers/${encodeURIComponent(provider)}/browser-status`, {
      method: "GET",
      headers: {
        "X-API-Key": apiKey,
      },
      cache: "no-store",
    });
    if (!res.ok) return { is_open: false };
    return await res.json();
  } catch {
    return { is_open: false };
  }
}

export async function retryJobProvider(
  jobId: string,
  provider: string,
  apiKey: string = DEFAULT_API_KEY
): Promise<{ status: string; job_id: string; provider: string } | null> {
  try {
    const res = await fetch(`/api/backend/research/${encodeURIComponent(jobId)}/retry/${encodeURIComponent(provider)}`, {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
      },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.warn("Failed to retry provider:", err);
    return null;
  }
}

export async function fetchProviderCapabilities(
  provider: string,
  forceSync: boolean = false,
  apiKey: string = DEFAULT_API_KEY
): Promise<ProviderLiveCapabilities> {
  const url = forceSync
    ? `/api/backend/providers/${encodeURIComponent(provider)}/capabilities/sync`
    : `/api/backend/providers/${encodeURIComponent(provider)}/capabilities`;
  const method = forceSync ? "POST" : "GET";

  const res = await fetch(url, {
    method,
    headers: {
      "X-API-Key": apiKey,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch capabilities for ${provider}: ${res.status}`);
  }
  return await res.json();
}

export async function syncAllProviderCapabilities(
  apiKey: string = DEFAULT_API_KEY
): Promise<Record<string, ProviderLiveCapabilities>> {
  const res = await fetch("/api/backend/providers/capabilities/sync-all", {
    method: "POST",
    headers: {
      "X-API-Key": apiKey,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to sync all provider capabilities: ${res.status}`);
  }
  return await res.json();
}

export async function transcribeVoiceAudio(
  audioBlob: Blob,
  filename: string = "recording.webm",
  apiKey: string = DEFAULT_API_KEY
): Promise<{ text: string; success: boolean; error?: string }> {
  try {
    const res = await fetch("/api/backend/voice/transcribe", {
      method: "POST",
      headers: {
        "X-API-Key": apiKey,
        "Content-Type": audioBlob.type || "audio/webm",
        "X-Audio-Filename": filename,
      },
      body: audioBlob,
    });

    if (!res.ok) {
      const errText = await res.text();
      return { text: "", success: false, error: `Transcribe HTTP ${res.status}: ${errText}` };
    }

    return await res.json();
  } catch (err: any) {
    return { text: "", success: false, error: err?.message || String(err) };
  }
}


