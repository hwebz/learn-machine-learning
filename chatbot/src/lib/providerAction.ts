import { Message, StepLog } from "../types/chat";
import { normalizeProvider } from "./providerResponse";

export interface ProviderActionInfo {
  provider: string;
  normalizedProvider: string;
  needsAction: boolean;
  reason?: string;
  kind?: "login" | "captcha" | "rate_limit" | "verification";
}

// Routine in-progress operational steps that must NEVER be treated as blocking or errors
const ROUTINE_IN_PROGRESS_STEPS = new Set([
  "checking_auth",
  "recovering_auth",
  "navigating",
  "locating_input",
  "selecting_mode",
  "entering_prompt",
  "submitting",
  "thinking_progress",
  "extracting",
  "progress",
  "researching",
  "queued",
  "running",
]);

// Auth/captcha specific patterns to identify real login walls vs generic errors
const AUTH_ERROR_REGEX =
  /(?:needs_user_action|blocked|login|sign[- ]?in|signin|đăng nhập|captcha|cloudflare|unusual traffic|verify you are human|session expired|re-authenticate)/i;

const AUTH_WALL_BODY_REGEX =
  /^(?:.*)(?:please sign in|sign in to continue|log in to continue|log in to chat|vui lòng đăng nhập|you must be logged in|blocked \(login\)|blocked \(captcha\))(?:.*)$/i;

export function detectProviderActionNeeded(
  provider: string,
  message?: Message,
  steps?: StepLog[]
): ProviderActionInfo {
  const norm = normalizeProvider(provider);
  const result: ProviderActionInfo = {
    provider,
    normalizedProvider: norm,
    needsAction: false,
  };

  // 1. Authoritative check: message.provider_runs (when a run completed or recorded terminal state)
  if (message?.provider_runs) {
    const runs = message.provider_runs;
    let matchingRun: any = null;
    if (Array.isArray(runs)) {
      matchingRun = runs.find(
        (r) => r && normalizeProvider(String(r.provider || "")) === norm
      );
    } else if (typeof runs === "object") {
      for (const [k, v] of Object.entries(runs)) {
        if (normalizeProvider(k) === norm) {
          matchingRun = v;
          break;
        }
      }
    }

    if (matchingRun) {
      // If the provider succeeded with status "ok", it NEVER needs user action
      if (matchingRun.status === "ok") {
        return result;
      }

      // Explicit needs_user_action status from backend
      if (matchingRun.status === "needs_user_action") {
        result.needsAction = true;
        result.reason = matchingRun.error || "Yêu cầu đăng nhập hoặc xác thực người dùng";
        result.kind = String(matchingRun.error || "").toLowerCase().includes("captcha")
          ? "captcha"
          : "login";
        return result;
      }

      // Failed or error runs: ONLY trigger if error specifically mentions auth/login/captcha/blocked
      if (matchingRun.status === "error" || matchingRun.status === "failed") {
        const err = String(matchingRun.error || "");
        if (AUTH_ERROR_REGEX.test(err)) {
          result.needsAction = true;
          result.reason = err;
          result.kind = err.toLowerCase().includes("captcha") ? "captcha" : "login";
          return result;
        }
      }

      // If answer markdown is very short and matches explicit auth wall banner
      const ans = String(matchingRun.answer_markdown || matchingRun.answer_md || "");
      if (ans.length > 0 && ans.length < 500 && AUTH_WALL_BODY_REGEX.test(ans)) {
        result.needsAction = true;
        result.reason = "Phát hiện thông báo yêu cầu đăng nhập trên màn hình phản hồi";
        result.kind = "login";
        return result;
      }
    }
  }

  // 2. Timeline steps check (during live generation or when examining logs)
  const targetSteps = steps || message?.steps || [];
  const provSteps = targetSteps.filter((st) => {
    const p = normalizeProvider(st.provider || "");
    return !p || p === norm;
  });

  // If this provider has a step indicating valid completion, do NOT flag action needed
  const hasSucceeded = provSteps.some(
    (st) =>
      st.step === "response_valid" ||
      st.data?.status === "ok" ||
      (st.status === "completed" && Boolean(st.data?.response_markdown))
  );
  if (hasSucceeded) {
    return result;
  }

  // Inspect provider steps in reverse (newest first) for actual blocked or auth-failed events
  for (const st of [...provSteps].reverse()) {
    // Completely ignore normal routine in-progress steps
    if (st.step && ROUTINE_IN_PROGRESS_STEPS.has(st.step.toLowerCase())) {
      continue;
    }

    // Explicit blocked step from adapter
    if (st.step === "blocked" || st.data?.status === "needs_user_action" || st.data?.needs_user_action) {
      result.needsAction = true;
      result.reason = st.data?.error || st.data?.blocking_detail || st.message || "Yêu cầu đăng nhập hoặc xác thực";
      result.kind = (st.data?.blocking_kind as any) || (String(result.reason).toLowerCase().includes("captcha") ? "captcha" : "login");
      return result;
    }

    // Failed or error step with auth-specific indicators
    if (st.step === "failed" || st.step === "error" || st.status === "error") {
      const errorText = `${st.data?.error || ""} ${st.data?.blocking_detail || ""}`;
      if (AUTH_ERROR_REGEX.test(errorText)) {
        result.needsAction = true;
        result.reason = st.data?.error || st.data?.blocking_detail || st.message || "Yêu cầu đăng nhập hoặc xác thực";
        result.kind = errorText.toLowerCase().includes("captcha") ? "captcha" : "login";
        return result;
      }

      // Check message ONLY if it's an explicit error/failure message (and not a check progress message)
      const msg = st.message || "";
      if (
        !msg.toLowerCase().includes("kiểm tra") &&
        /(?:yêu cầu xác thực|yêu cầu đăng nhập|bị chặn|blocked|needs_user_action)/i.test(msg)
      ) {
        result.needsAction = true;
        result.reason = msg;
        result.kind = msg.toLowerCase().includes("captcha") ? "captcha" : "login";
        return result;
      }
    }
  }

  // 3. Synthesized report / summary check (only if not already marked successful)
  if (message?.content) {
    const content = message.content;
    const issueRegex = new RegExp(
      `-\\s*${norm}\\s*:\\s*(needs_user_action|blocked|login|captcha)`,
      "i"
    );
    if (issueRegex.test(content)) {
      result.needsAction = true;
      result.reason = `${provider.toUpperCase()} yêu cầu đăng nhập hoặc xác thực người dùng.`;
      result.kind = "login";
      return result;
    }
  }

  return result;
}

export function detectAllProvidersNeedingAction(
  message?: Message,
  steps?: StepLog[]
): ProviderActionInfo[] {
  const providersSet = new Set<string>();

  if (message?.providers) {
    for (const p of message.providers) providersSet.add(p);
  }
  if (message?.provider_runs) {
    const runs = message.provider_runs;
    if (Array.isArray(runs)) {
      for (const r of runs) if (r?.provider) providersSet.add(r.provider);
    } else if (typeof runs === "object") {
      for (const k of Object.keys(runs)) providersSet.add(k);
    }
  }
  const targetSteps = steps || message?.steps || [];
  for (const st of targetSteps) {
    if (st.provider) providersSet.add(st.provider);
  }

  const results: ProviderActionInfo[] = [];
  const handled = new Set<string>();

  for (const p of providersSet) {
    const norm = normalizeProvider(p);
    if (handled.has(norm)) continue;
    handled.add(norm);
    const info = detectProviderActionNeeded(p, message, steps);
    if (info.needsAction) {
      results.push(info);
    }
  }
  return results;
}
