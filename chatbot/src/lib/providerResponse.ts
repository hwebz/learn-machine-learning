import { Message, StepLog } from "../types/chat";

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
  return s;
}

export function extractProviderResponse(
  provider: string,
  pSteps: StepLog[] = [],
  currentMessage?: Message
): string {
  const normTarget = normalizeProvider(provider);

  // 1. Check pSteps from newest to oldest for response_markdown or answer_markdown
  for (const st of [...pSteps].reverse()) {
    const data = st.data;
    if (data && typeof data === "object") {
      const resp = data.response_markdown || data.answer_markdown || data.response_text;
      if (resp && typeof resp === "string" && resp.trim().length > 0) {
        return resp.trim();
      }
    }
    if (st.step === "response_valid" || st.step === "response_partial") {
      const resp = (st as any).response_markdown || (st as any).answer_markdown;
      if (resp && typeof resp === "string" && resp.trim().length > 0) {
        return resp.trim();
      }
    }
  }

  // 2. Check currentMessage?.provider_runs
  if (currentMessage?.provider_runs) {
    const runs = currentMessage.provider_runs;
    if (Array.isArray(runs)) {
      const match = runs.find(
        (r) => r && normalizeProvider(String(r.provider || "")) === normTarget
      );
      if (match) {
        const resp = match.answer_markdown || match.answer_md || match.response_markdown || match.text;
        if (resp && typeof resp === "string" && resp.trim().length > 0) {
          return resp.trim();
        }
      }
    } else if (typeof runs === "object") {
      for (const [k, v] of Object.entries(runs)) {
        if (normalizeProvider(k) === normTarget) {
          if (typeof v === "string" && v.trim().length > 0) {
            return v.trim();
          }
          if (v && typeof v === "object") {
            const resp = (v as any).answer_markdown || (v as any).answer_md || (v as any).response_markdown || (v as any).text;
            if (resp && typeof resp === "string" && resp.trim().length > 0) {
              return resp.trim();
            }
          }
        }
      }
    }
  }

  // 3. Check currentMessage?.content for sectional header e.g. ## Qwen response or ## Copilot response
  if (currentMessage?.content) {
    const content = currentMessage.content;
    const sectionRegex = new RegExp(
      `(?:^|\\n)##+\\s*${normTarget}\\b[^\\n]*\\n+([\\s\\S]*?)(?=(?:\\n##+\\s*\\w+)|$)`,
      "i"
    );
    const match = content.match(sectionRegex);
    if (match && match[1] && match[1].trim().length > 0) {
      return match[1].trim();
    }

    // 4. If currentMessage has only 1 provider, or if this is the primary provider of this message:
    const msgProviders = (currentMessage.providers || (currentMessage.provider ? [currentMessage.provider] : []))
      .map(normalizeProvider);
    if (
      msgProviders.length === 1 &&
      (msgProviders[0] === normTarget || msgProviders[0] === "" || normTarget === "ai")
    ) {
      return content.trim();
    }
    if (msgProviders.length <= 1) {
      return content.trim();
    }
  }

  // 5. Fallback: check pSteps for streaming_text or response_preview
  for (const st of [...pSteps].reverse()) {
    const preview = st.streamingText || st.data?.streaming_text || st.data?.response_preview;
    if (preview && typeof preview === "string" && preview.trim().length > 0) {
      return preview.trim();
    }
  }

  // 6. If currentMessage has content and no providers array
  if (currentMessage?.content && !currentMessage.providers) {
    return currentMessage.content.trim();
  }

  return "";
}
