/**
 * Utility functions for parsing and formatting duration / time taken across the chatbot.
 */

/**
 * Parses any duration input (number of seconds, ms string, or duration string) into a number of seconds.
 */
export function parseSeconds(val: number | string | undefined | null): number {
  if (val === undefined || val === null) return 0;
  if (typeof val === "number") {
    return isNaN(val) ? 0 : val;
  }
  const str = String(val).trim();
  if (!str || str === "--") return 0;

  // Match e.g. "1m 15s", "1m15s", "2m 5s", "1h 2m 15s"
  const hMatch = str.match(/(\d+)\s*h(?:our)?/i);
  const mMatch = str.match(/(\d+)\s*m(?:in)?/i);
  const sMatch = str.match(/(\d+(?:\.\d+)?)\s*s(?:ec)?/i);

  if (hMatch || mMatch || sMatch) {
    const hours = hMatch ? parseFloat(hMatch[1]) : 0;
    const mins = mMatch ? parseFloat(mMatch[1]) : 0;
    const secs = sMatch ? parseFloat(sMatch[1]) : 0;
    return hours * 3600 + mins * 60 + secs;
  }

  // Handle "1500ms"
  if (str.endsWith("ms")) {
    const num = parseFloat(str);
    return isNaN(num) ? 0 : num / 1000;
  }

  // Handle plain number string or ending with "s" e.g. "75s" or "75"
  const cleanStr = str.replace(/s$/i, "").trim();
  const parsed = parseFloat(cleanStr);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Formats seconds into a normalized minute + second format.
 * - Under 10s with fraction: e.g. "8.4s"
 * - Under 60s: e.g. "45s"
 * - 60s and above: e.g. "1m 15s", "2m 5s"
 * - 3600s and above: e.g. "1h 5m 20s"
 */
export function formatDuration(val: number | string | undefined | null): string {
  if (val === "--") return "--";
  if (val === undefined || val === null || val === "") return "0s";

  const sec = parseSeconds(val);
  if (sec <= 0) return "0s";

  if (sec < 60) {
    const hasDecimals = sec % 1 !== 0;
    if (sec < 10 && hasDecimals) {
      return `${sec.toFixed(1)}s`;
    }
    return `${Math.round(sec)}s`;
  }

  const totalSeconds = Math.round(sec);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;

  if (m >= 60) {
    const h = Math.floor(m / 60);
    const remM = m % 60;
    return `${h}h ${remM}m ${s}s`;
  }

  return `${m}m ${s}s`;
}
