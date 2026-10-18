import { StepLog, ThinkingStep, SourceLink, Message } from "../types/chat";
import { extractProviderResponse } from "./providerResponse";

export function normalizeProvider(name: string): string {
  const s = name.trim().toLowerCase();
  if (s.includes("qwen")) return "qwen";
  if (s.includes("copilot")) return "copilot";
  if (s.includes("gemini")) return "gemini";
  if (s.includes("deepseek")) return "deepseek";
  if (s.includes("chatgpt") || s.includes("openai")) return "chatgpt";
  if (s.includes("grok")) return "grok";
  if (s.includes("claude")) return "claude";
  if (s.includes("perplexity")) return "perplexity";
  if (s.includes("mistral")) return "mistral";
  if (s.includes("kimi") || s.includes("moonshot")) return "kimi";
  if (s.includes("zhipu") || s.includes("glm")) return "zhipu";
  if (s.includes("minimax") || s.includes("hailuo")) return "minimax";
  return s;
}

export function extractProvider(st: StepLog): string {
  if (st.provider) return normalizeProvider(st.provider);
  if (st.data?.provider) return normalizeProvider(String(st.data.provider));
  const match = st.message.match(
    /\b(qwen|copilot|gemini|deepseek|chatgpt|openai|grok|perplexity|claude|mistral|kimi|moonshot|zhipu|glm|minimax|hailuo)\b/i
  );
  if (match) return normalizeProvider(match[1]);
  return "";
}

export function isThinkingEvent(st: StepLog): boolean {
  if (st.step === "thinking_progress") return true;
  if (st.isThinking || st.data?.is_thinking) return true;
  if (/đang suy luận/i.test(st.message)) return true;
  return false;
}

export interface TimelineLogItem {
  kind: "log";
  key: string;
  message: string;
  timestamp: string;
  isLatest?: boolean;
}

export interface TimelineThinkingItem {
  kind: "thinking";
  key: string;
  provider: string;
  steps: ThinkingStep[];
  text?: string;
  citations: SourceLink[];
  isRunning: boolean;
  timestamp: string;
}

export type TimelineItem = TimelineLogItem | TimelineThinkingItem;

export function buildChronologicalTimeline(
  steps: StepLog[],
  isLive: boolean,
  message?: Message
): TimelineItem[] {
  if (!steps || steps.length === 0) return [];

  // 1. Identify all providers in order of appearance
  const providersOrder: string[] = [];
  for (const st of steps) {
    const p = extractProvider(st);
    if (p && !providersOrder.includes(p)) {
      providersOrder.push(p);
    }
  }
  if (providersOrder.length === 0) {
    providersOrder.push("");
  }

  // 2. Pre-aggregate thinking details per provider
  const providerDataMap = new Map<
    string,
    {
      thinkingSteps: ThinkingStep[];
      thinkingText: string;
      citations: SourceLink[];
      hasThinking: boolean;
      isRunning: boolean;
    }
  >();

  for (const p of providersOrder) {
    const pSteps = steps.filter((st) => {
      const sp = extractProvider(st);
      return sp === p || (providersOrder.length === 1 && !sp);
    });

    const stepMap = new Map<string, ThinkingStep>();
    for (const st of pSteps) {
      const raw = st.thinkingSteps || st.data?.thinking_steps || [];
      for (const item of raw) {
        if (!item || !item.title) continue;
        const normKey = item.title.trim().toLowerCase();

        // If transitioning from "thinking" to "worked for..." or "thought for...", update the existing thinking step in place
        if (/^(worked|thought)\s+for\b/i.test(normKey) && stepMap.has("thinking")) {
          const prev = stepMap.get("thinking")!;
          stepMap.delete("thinking");
          stepMap.set(normKey, {
            ...prev,
            title: item.title,
            status: item.status || "completed",
            description: (item.description && item.description.trim()) ? item.description : prev.description,
          });
          continue;
        }

        // If consecutive polls update the duration (e.g. "worked for 12s" -> "worked for 13s"), update the existing worked-for entry
        const existingWorkedKey = Array.from(stepMap.keys()).find(k => /^(worked|thought)\s+for\b/i.test(k));
        if (/^(worked|thought)\s+for\b/i.test(normKey) && existingWorkedKey) {
          const prev = stepMap.get(existingWorkedKey)!;
          stepMap.delete(existingWorkedKey);
          stepMap.set(normKey, {
            ...prev,
            title: item.title,
            status: item.status || "completed",
            description: (item.description && item.description.trim()) ? item.description : prev.description,
          });
          continue;
        }

        const existing = stepMap.get(normKey);
        if (!existing) {
          stepMap.set(normKey, { ...item });
        } else {
          existing.status = item.status || existing.status;
          if (item.description && item.description.trim()) {
            existing.description = item.description;
          }
        }
      }
    }
    const accumulatedSteps = Array.from(stepMap.values());

    const citMap = new Map<string, SourceLink>();
    for (const st of pSteps) {
      const rawCits = st.citations || st.data?.citations || [];
      for (const c of rawCits) {
        if (c && c.url && !citMap.has(c.url)) {
          citMap.set(c.url, {
            title: c.title || c.url,
            url: c.url,
            domain: c.domain,
          });
        }
      }
    }
    const accumulatedCitations = Array.from(citMap.values());

    let accumulatedText = "";
    for (const st of [...pSteps].reverse()) {
      const t = st.thinkingText || st.data?.thinking_text;
      if (t && typeof t === "string" && t.trim().length > 0) {
        accumulatedText = t;
        break;
      }
    }

    const isProviderFinished = pSteps.some(
      (st) =>
        st.step === "response_valid" ||
        st.step === "response_partial" ||
        st.step === "completed" ||
        st.step === "failed" ||
        st.status === "completed" ||
        (st.data && (st.data.status === "ok" || st.data.status === "partial" || Boolean(st.data.response_markdown))) ||
        /hoàn thành|phản hồi hợp lệ|kết quả một phần|thất bại|đã trả về|response_valid/i.test(st.message)
    );
    const isRunning = isLive && !isProviderFinished;

    if (!isRunning) {
      for (const s of accumulatedSteps) {
        s.status = "completed";
      }
    } else {
      const lastRunningIdx = accumulatedSteps.map((s) => s.status).lastIndexOf("running");
      if (lastRunningIdx >= 0) {
        for (let idx = 0; idx < lastRunningIdx; idx++) {
          accumulatedSteps[idx].status = "completed";
        }
      }
    }

    const providerResp = extractProviderResponse(p, pSteps, message);
    if (providerResp) {
      const filtered = accumulatedSteps.filter(
        (s) => !s.title.toLowerCase().includes("response generated")
      );
      filtered.push({
        title: "Response generated",
        description: providerResp,
        status: "completed",
      });
      accumulatedSteps.length = 0;
      accumulatedSteps.push(...filtered);
    }

    const hasThinking =
      accumulatedSteps.length > 0 ||
      Boolean(accumulatedText) ||
      accumulatedCitations.length > 0 ||
      (isLive && pSteps.some(isThinkingEvent));

    providerDataMap.set(p, {
      thinkingSteps: accumulatedSteps,
      thinkingText: accumulatedText,
      citations: accumulatedCitations,
      hasThinking,
      isRunning,
    });
  }

  // 3. Assemble chronological timeline
  const timeline: TimelineItem[] = [];
  const placedThinking = new Set<string>();
  let lastLogMessage = "";

  for (let i = 0; i < steps.length; i++) {
    const st = steps[i];
    const p = extractProvider(st);
    const pData =
      providerDataMap.get(p) ||
      (providersOrder.length === 1 ? providerDataMap.get(providersOrder[0]) : undefined);

    // If pure thinking event, skip adding as log line and insert thinking item if not yet placed
    if (isThinkingEvent(st)) {
      if (pData && pData.hasThinking && !placedThinking.has(p)) {
        timeline.push({
          kind: "thinking",
          key: `thinking-${p || "default"}-${i}`,
          provider: p,
          steps: pData.thinkingSteps,
          text: pData.thinkingText,
          citations: pData.citations,
          isRunning: pData.isRunning,
          timestamp: st.timestamp,
        });
        placedThinking.add(p);
      }
      continue;
    }

    // If generating step and thinking block has not been placed yet, insert thinking before generating
    if (
      pData &&
      pData.hasThinking &&
      !placedThinking.has(p) &&
      (st.step === "generating" || /đang đợi.*sinh câu trả lời/i.test(st.message))
    ) {
      timeline.push({
        kind: "thinking",
        key: `thinking-${p || "default"}-${i}`,
        provider: p,
        steps: pData.thinkingSteps,
        text: pData.thinkingText,
        citations: pData.citations,
        isRunning: pData.isRunning,
        timestamp: st.timestamp,
      });
      placedThinking.add(p);
    }

    // Normal pipeline log line (deduplicating consecutive identical messages)
    if (st.message && st.message !== lastLogMessage) {
      timeline.push({
        kind: "log",
        key: st.id || `log-${i}-${st.message}`,
        message: st.message,
        timestamp: st.timestamp,
      });
      lastLogMessage = st.message;
    }

    // If submitting step and thinking block has not been placed yet, insert thinking right after submitting
    if (
      pData &&
      pData.hasThinking &&
      !placedThinking.has(p) &&
      (st.step === "submitting" || /đã gửi câu hỏi/i.test(st.message))
    ) {
      timeline.push({
        kind: "thinking",
        key: `thinking-${p || "default"}-${i}`,
        provider: p,
        steps: pData.thinkingSteps,
        text: pData.thinkingText,
        citations: pData.citations,
        isRunning: pData.isRunning,
        timestamp: st.timestamp,
      });
      placedThinking.add(p);
    }
  }

  // 4. Fallback: Place any unplaced provider thinking block
  for (const [prov, data] of providerDataMap.entries()) {
    if (data.hasThinking && !placedThinking.has(prov)) {
      timeline.push({
        kind: "thinking",
        key: `thinking-${prov || "default"}-end`,
        provider: prov,
        steps: data.thinkingSteps,
        text: data.thinkingText,
        citations: data.citations,
        isRunning: data.isRunning,
        timestamp: "",
      });
      placedThinking.add(prov);
    }
  }

  // Mark latest item for live spinner
  if (isLive && timeline.length > 0) {
    const lastItem = timeline[timeline.length - 1];
    if (lastItem.kind === "log") {
      lastItem.isLatest = true;
    }
  }

  return timeline;
}
