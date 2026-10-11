from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any

import structlog

from app.browser.locators import SelectorChain, resolve_locator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CompletionResult:
    done: bool
    reason: str  # stable | done_marker | blocked | timeout | error
    text: str
    blocking_detail: str | None = None


@dataclass(frozen=True, slots=True)
class BlockingState:
    kind: str  # login | captcha | verification | rate_limit
    detail: str


_TARGET_CLOSED_MARKERS = (
    "Target page, context or browser has been closed",
    "Target closed",
    "Browser has been closed",
)


def is_target_closed_error(exc: BaseException) -> bool:
    """True when a Playwright error means the tab/browser is gone (not just slow)."""
    text = str(exc)
    return any(marker in text for marker in _TARGET_CLOSED_MARKERS)


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without a browser)
# ---------------------------------------------------------------------------


def match_blocking_url(url: str, patterns: list[str]) -> str | None:
    lowered = url.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return pattern
    return None


def match_blocking_text(text: str, patterns: list[str]) -> str | None:
    lowered = (text or "").lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return pattern
    return None


def classify_blocking(pattern: str) -> str:
    p = pattern.lower()
    if "captcha" in p or "verify" in p or "unusual traffic" in p:
        return "captcha"
    if "rate" in p or "limit" in p:
        return "rate_limit"
    if "login" in p or "signin" in p or "sign in" in p or "accounts.google" in p:
        return "login"
    return "verification"


def evaluate_completion(
    *,
    input_editable: bool,
    text_stable: bool,
    done_marker_visible: bool,
    generating: bool = False,
) -> tuple[bool, str]:
    """Complete when a done marker (e.g. Copy button) is visible AND generation
    has finished, or when the model is not generating, the answer text is stable,
    and input is editable.
    """
    if generating:
        return False, "in_progress"
    if done_marker_visible:
        return True, "done_marker"
    if input_editable and text_stable:
        return True, "stable"
    return False, "in_progress"


class StabilityTracker:
    """Tracks answer text stability over time (pure, clock injectable)."""

    def __init__(self, stable_seconds: float, clock: Any = time.monotonic) -> None:
        self.stable_seconds = stable_seconds
        self._clock = clock
        self._prev_text: str | None = None
        self._stable_since: float | None = None

    def update(self, text: str) -> bool:
        """Feed the latest answer text; return True once text has been unchanged
        for at least stable_seconds (non-empty text required)."""
        now = self._clock()
        if not text.strip():
            self._prev_text = text
            self._stable_since = None
            return False
        if text != self._prev_text:
            self._prev_text = text
            self._stable_since = now
            return False
        if self._stable_since is None:
            self._stable_since = now
            return False
        return (now - self._stable_since) >= self.stable_seconds


# ---------------------------------------------------------------------------
# Page-dependent detection
# ---------------------------------------------------------------------------


async def wait_for_input(
    page: Any,
    question_input: SelectorChain,
    *,
    timeout_s: float = 30,
    poll_s: float = 1.0,
) -> Any | None:
    """Poll until any rung of the input chain matches, network conditions permitting.

    SPAs (e.g., Mistral) hydrate their editors several seconds after page load,
    and the delay varies with the network — so poll instead of sleeping a fixed
    amount. Returns the first matching locator, or None on timeout.
    """
    import time as _time

    deadline = _time.monotonic() + timeout_s
    while True:
        locator, rung = await resolve_locator(page, question_input)
        if locator is not None:
            return locator
        if _time.monotonic() >= deadline:
            return None
        await asyncio.sleep(poll_s)


async def detect_blocking_state(page: Any, blocking: dict[str, Any]) -> BlockingState | None:
    """Check URL + visible text against blocking patterns. Never attempts bypass.

    Raises when the page/browser has been closed — callers must not treat a
    dead tab as a slow-loading page.
    """
    url = getattr(page, "url", "") or ""
    url_pattern = match_blocking_url(url, blocking.get("url_patterns", []) or [])
    if url_pattern:
        return BlockingState(kind=classify_blocking(url_pattern), detail=f"URL matched pattern {url_pattern!r}: {url}")

    text = ""
    try:
        text = await page.locator("body").inner_text(timeout=3000)
    except Exception as exc:  # noqa: BLE001 — page may still be loading
        if is_target_closed_error(exc):
            raise
        pass
    text_pattern = match_blocking_text(text, blocking.get("text_patterns", []) or [])
    if text_pattern:
        return BlockingState(kind=classify_blocking(text_pattern), detail=f"Visible text matched pattern {text_pattern!r}")
    return None


async def _answer_text(page: Any, answer_container: SelectorChain) -> str:
    locator, _ = await resolve_locator(page, answer_container)
    if locator is None:
        return ""
    try:
        count = await locator.count()
        if count == 0:
            return ""
        target = locator
        if count > 1 and hasattr(locator, "last"):
            target = locator.last
        return (await target.inner_text(timeout=3000)).strip()
    except Exception as exc:  # noqa: BLE001
        if is_target_closed_error(exc):
            raise
        return ""


async def _indicator_visible(page: Any, chain: SelectorChain | None) -> bool:
    if not chain:
        return False
    locator, _ = await resolve_locator(page, chain)
    if locator is None:
        return False
    try:
        count = await locator.count()
        if count == 0:
            return False
        if hasattr(locator, "nth"):
            for i in range(count):
                if await locator.nth(i).is_visible(timeout=500):
                    return True
            return False
        return await locator.is_visible(timeout=500)
    except Exception as exc:  # noqa: BLE001
        if is_target_closed_error(exc):
            raise
        return False


async def _input_editable(page: Any, question_input: SelectorChain) -> bool:
    locator, _ = await resolve_locator(page, question_input)
    if locator is None:
        return False
    try:
        count = await locator.count()
        if count == 0:
            return False
        target = locator
        if count > 1 and hasattr(locator, "first"):
            target = locator.first
        return await target.is_editable(timeout=1000)
    except Exception as exc:  # noqa: BLE001
        if is_target_closed_error(exc):
            raise
        return False


DOM_SCAN_THINKING_AND_CITATIONS = """
(provider) => {
    let thinkingText = "";
    let isThinking = false;
    const thinkingSteps = [];

    const clean = (txt) => (txt || "").trim().replace(/\\s+/g, " ");

    const triggerClick = (el) => {
        if (!el) return;
        try { el.click(); } catch (e) {}
        try {
            const evt = new MouseEvent("click", {
                bubbles: true,
                cancelable: true,
                view: window
            });
            el.dispatchEvent(evt);
        } catch (e) {}
    };

    // 1. Qwen-specific: Open the "Thinking and Search" detailed right sidebar if closed
    if (provider === "qwen" || !provider) {
        try {
            const sidebar = document.querySelector(".qwen-chat-thinking-and-sources-content");
            if (!sidebar) {
                const toggleIcons = document.querySelectorAll(
                    ".anticon.qwen-chat-status-card-after, " +
                    "[class*='qwen-chat-status-card-after'], " +
                    ".qwen-chat-package-comp-source-list, " +
                    "button.qwen-chat-package-comp-source-list, " +
                    ".qwen-chat-tool-status-card"
                );
                for (const icon of toggleIcons) {
                    const attempts = parseInt(icon.dataset.expandAttempts || "0", 10);
                    if (attempts < 5) {
                        icon.dataset.expandAttempts = (attempts + 1).toString();
                        triggerClick(icon);
                        const parentCard = icon.closest(".qwen-chat-tool-status-card, [class*='status-card']");
                        if (parentCard && parentCard !== icon) {
                            triggerClick(parentCard);
                        }
                    }
                }
            }
        } catch (e) {}
    }

    // 2. Extract structured thinking steps without duplicates
    const seenStepKeys = new Set();
    try {
        let statusCards = [];
        const sidebar = document.querySelector(".qwen-chat-thinking-and-sources-content");
        if (sidebar) {
            const phaseCards = sidebar.querySelectorAll("div.qwen-chat-thinking-status-card[data-phase-id]");
            if (phaseCards && phaseCards.length > 0) {
                statusCards = Array.from(phaseCards);
            } else {
                const container = sidebar.querySelector(".qwen-chat-thinking-and-sources-content-thinking-container");
                if (container && container.children.length > 0) {
                    statusCards = Array.from(container.children);
                } else {
                    statusCards = Array.from(sidebar.querySelectorAll("div.qwen-chat-thinking-status-card"));
                }
            }
        }

        // Fallback: main chat thinking cards (filter out nested cards to avoid duplicates)
        if (statusCards.length === 0) {
            const mainContainer = document.querySelector(".qwen-chat-thinking-tool-status-card-wraper");
            if (mainContainer) {
                const topCards = mainContainer.querySelectorAll("div.qwen-chat-tool-status-card, div.qwen-chat-thinking-status-card");
                if (topCards && topCards.length > 0) {
                    statusCards = Array.from(topCards);
                }
            } else {
                const rawCards = document.querySelectorAll(
                    "div.qwen-chat-thinking-status-card[data-phase-id], " +
                    "div.qwen-chat-thinking-status-card, " +
                    "div.thinking-chain-container"
                );
                const topLevel = [];
                for (const el of rawCards) {
                    if (!topLevel.some(parent => parent.contains(el) && parent !== el)) {
                        topLevel.push(el);
                    }
                }
                statusCards = topLevel;
            }
        }

        for (const card of statusCards) {
            let title = "";
            const titleEl = card.querySelector(
                "div[class*='thinking-status-card-title-text'], " +
                "div[class*='status-card-title-text'], " +
                "div[class*='qwen-chat-thinking-status-card-title'], " +
                "div[class*='status-card-title'], " +
                "div[class*='tool-status-card-title']"
            );
            if (titleEl) {
                const clone = titleEl.cloneNode(true);
                clone.querySelectorAll(".anticon, svg, button").forEach(i => i.remove());
                title = clean(clone.innerText || clone.textContent);
            } else {
                const headerEl = card.querySelector("div[class*='header']");
                if (headerEl) {
                    const clone = headerEl.cloneNode(true);
                    clone.querySelectorAll(".anticon, svg, button").forEach(i => i.remove());
                    title = clean(clone.innerText || clone.textContent);
                }
            }

            // Skip summary/completion footer
            if (!title || /^(Thinking and Searching Completed|Thinking completed)$/i.test(title)) {
                if (title) isThinking = true;
                continue;
            }

            let description = "";
            // A. Markdown text: only take top container to avoid duplicating inner spans
            const mdEl = card.querySelector(".qwen-markdown, .markdown-body, .markdown");
            if (mdEl) {
                description = clean(mdEl.innerText || mdEl.textContent);
            } else {
                const textEl = card.querySelector(".qwen-markdown-text");
                if (textEl) {
                    description = clean(textEl.innerText || textEl.textContent);
                }
            }

            // B. Search domain pills for search/source cards
            if (!description) {
                const searchCardEls = card.querySelectorAll(".qwen-chat-search-card, [class*='search-card']");
                if (searchCardEls && searchCardEls.length > 0) {
                    const domains = [];
                    for (const sc of searchCardEls) {
                        const divs = sc.querySelectorAll("div");
                        let d = "";
                        if (divs.length > 0) {
                            d = clean(divs[divs.length - 1].innerText || divs[divs.length - 1].textContent);
                        }
                        if (!d) {
                            d = clean(sc.innerText || sc.textContent);
                        }
                        if (d && !d.startsWith("#") && !domains.includes(d)) {
                            domains.push(d);
                        }
                    }
                    if (domains.length > 0) {
                        if (/source|nguồn/i.test(title)) {
                            description = "Nguồn đã đọc: " + domains.join(", ");
                        } else {
                            description = "Đã tìm kiếm: " + domains.join(", ");
                        }
                    }
                }
            }

            // C. Generic content fallback
            if (!description) {
                const descEl = card.querySelector(
                    "div[class*='status-card-content'], " +
                    "div[class*='thinking-status-card-content'], " +
                    "div[class*='tool-status-card-content'], " +
                    "div[class*='status-card-body'], " +
                    "div[class*='status-card-detail']"
                );
                if (descEl) {
                    const clone = descEl.cloneNode(true);
                    clone.querySelectorAll("[class*='title'], .anticon, svg").forEach(i => i.remove());
                    description = clean(clone.innerText || clone.textContent);
                }
            }

            const cardClass = card.className || "";
            const isCompleted = cardClass.includes("-completed") ||
                                cardClass.includes("completed") ||
                                card.querySelector(".anticon-circleCheck, .anticon-check, [class*='circleCheck'], [class*='check'], [class*='success']") !== null;
            const isRunning = card.querySelector(".anticon-spin, .anticon-loading, [class*='loading'], [class*='spin']") !== null;
            const stepStatus = isCompleted ? "completed" : (isRunning ? "running" : (description ? "completed" : "running"));

            // Deduplicate: avoid pushing identical (title, description)
            const dedupeKey = title + "::" + description;
            if (!seenStepKeys.has(dedupeKey)) {
                seenStepKeys.add(dedupeKey);
                isThinking = true;
                thinkingSteps.push({
                    title: title,
                    description: description || "",
                    status: stepStatus
                });
            }
        }
    } catch (e) {}

    // 3. Fallback: query general thinking containers across other providers
    const thinkingSelectors = [
        ".ds-markdown--thought",
        "div[class*='thinking-status-card-content']",
        "div[class*='thinking-content']",
        "div[class*='thought-content']",
        "div[data-testid*='thought']",
        "div[class*='reasoning']",
        "div[class*='thinking_content']",
        "div[class*='thinking-container']",
        "div[class*='thinking-process']",
        "div[class*='model-thought']",
        "details[class*='thought']",
        "details[class*='thinking']",
        "div[aria-label*='Thought' i]",
        "div[aria-label*='Thinking' i]"
    ];

    for (const sel of thinkingSelectors) {
        try {
            const els = document.querySelectorAll(sel);
            if (els && els.length > 0) {
                const target = els[els.length - 1];
                const txt = (target.innerText || target.textContent || "").trim();
                if (txt) {
                    thinkingText = txt;
                    isThinking = true;
                    break;
                }
            }
        } catch (e) {}
    }

    if (!thinkingText && thinkingSteps.length > 0) {
        const fullDesc = thinkingSteps.map(s => {
            return s.description ? `${s.title}:\\n${s.description}` : s.title;
        }).join("\\n\\n");
        if (fullDesc) {
            thinkingText = fullDesc;
        }
    }

    if (!thinkingText && !isThinking) {
        try {
            const allBlocks = document.querySelectorAll("details, blockquote, div[role='region'], div[class*='thought']");
            for (const el of allBlocks) {
                const txt = (el.innerText || "").trim();
                if (txt && (/^(thought|thinking|reasoning|suy nghĩ)/i.test(txt) || txt.includes("Thought Process") || txt.includes("Thinking Process"))) {
                    thinkingText = txt;
                    isThinking = true;
                    break;
                }
            }
        } catch (e) {}
    }

    // 4. Citations and external source links in DOM
    const citations = [];
    const seenUrls = new Set();

    // 4.1. Qwen-specific: Extract from .sources-item, .custom-web-search-origins, .content-list
    try {
        const sourceItems = document.querySelectorAll(
            ".sources-item, " +
            ".custom-web-search-origins .content-list-item, " +
            "div[class*='sources-item']"
        );
        for (const item of sourceItems) {
            let url = "";
            const hostEl = item.querySelector(".host-name-text, [class*='host-name']");
            if (hostEl) {
                url = (hostEl.innerText || hostEl.textContent || "").trim();
            }
            if (!url) {
                const aTag = item.querySelector("a[href^='http']");
                if (aTag) {
                    url = aTag.href || aTag.getAttribute("href") || "";
                }
            }

            const titleEl = item.querySelector(".content-item-des-title, [class*='des-title']");
            const title = clean(titleEl ? (titleEl.innerText || titleEl.textContent) : "");
            const snipEl = item.querySelector(".content-item-des, [class*='snippet']");
            const snippet = clean(snipEl ? (snipEl.innerText || snipEl.textContent) : "");

            if (url && url.startsWith("http") && !seenUrls.has(url)) {
                seenUrls.add(url);
                citations.push({
                    url: url,
                    title: title || url,
                    snippet: snippet
                });
            }
        }
    } catch (e) {}

    // 4.2. General link selectors for citations across providers
    const linkSelectors = [
        "a[data-testid='citation']",
        "a.citation",
        "a[data-citation]",
        "a.qwen-markdown-link",
        "div.response-message-content a[href^='http']",
        ".custom-qwen-markdown a[href^='http']",
        ".qwen-markdown a[href^='http']",
        ".markdown-body a[href^='http']",
        ".prose a[href^='http']",
        "article a[href^='http']",
        "div[class*='source'] a[href^='http']",
        "div[class*='citation'] a[href^='http']",
        "ul[class*='source'] a[href^='http']",
        "ol[class*='source'] a[href^='http']",
        "div[class*='references'] a[href^='http']",
        "sup a[href^='http']",
        "div[class*='status-card'] a[href^='http']"
    ];

    for (const sel of linkSelectors) {
        try {
            const links = document.querySelectorAll(sel);
            for (const a of links) {
                const href = a.href || a.getAttribute("href");
                if (href && href.startsWith("http") && !seenUrls.has(href)) {
                    if (!href.includes("login") && !href.includes("auth") && !href.includes("accounts.google")) {
                        seenUrls.add(href);
                        let title = (a.innerText || a.textContent || a.getAttribute("title") || "").trim();
                        citations.push({
                            url: href,
                            title: title || null,
                            snippet: ""
                        });
                    }
                }
            }
        } catch (e) {}
    }

    return {
        is_thinking: isThinking,
        thinking_text: thinkingText ? thinkingText.slice(-4000) : "",
        thinking_steps: thinkingSteps,
        citations: citations
    };
}
"""


async def wait_for_completion(
    page: Any,
    *,
    provider: str = "",
    provider_cfg: dict[str, Any],
    blocking: dict[str, Any],
    completion_cfg: dict[str, Any],
    timeout_s: float,
    on_poll: Any | None = None,
    thinking_interval_s: float | None = None,
    clock: Any = time.monotonic,
    sleep: Any = asyncio.sleep,
) -> CompletionResult:
    """Poll until the chatbot finishes generating, blocked, or timeout_s elapses."""
    stable_s = float(completion_cfg.get("stable_seconds", 5))
    poll_s = float(completion_cfg.get("poll_interval_s", 2))
    min_poll = float(completion_cfg.get("min_poll_s", poll_s))
    max_poll = float(completion_cfg.get("max_poll_s", poll_s))
    # Optional per-provider delay after done_marker appears (e.g., Mistral renders
    # copy button before answer text is populated)
    done_marker_delay_s = float(completion_cfg.get("done_marker_delay_s", 0))

    question_input = provider_cfg.get("question_input", [])
    generating_chain = provider_cfg.get("generating_indicator")
    done_chain = provider_cfg.get("done_indicator")
    answer_chain = provider_cfg.get("answer_container", [])

    tracker = StabilityTracker(stable_s, clock=clock)
    start_time = clock()
    deadline = start_time + timeout_s
    last_text = ""
    poll_count = 0

    while clock() < deadline:
        try:
            state = await detect_blocking_state(page, blocking)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise
        if state is not None:
            return CompletionResult(done=False, reason="blocked", text=last_text, blocking_detail=state.detail)

        try:
            generating = await _indicator_visible(page, generating_chain)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        try:
            editable = await _input_editable(page, question_input)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        try:
            last_text = await _answer_text(page, answer_chain)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        try:
            done_marker = await _indicator_visible(page, done_chain)
        except RuntimeError as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            raise

        text_stable = tracker.update(last_text)

        done, reason = evaluate_completion(
            input_editable=editable,
            text_stable=text_stable,
            done_marker_visible=done_marker,
            generating=generating,
        )

        poll_count += 1
        elapsed = clock() - start_time
        if generating:
            state_desc = "thinking / generating"
        elif done_marker:
            state_desc = "done marker visible (copy button)"
        elif text_stable:
            state_desc = "text stable (generation finished)"
        elif last_text:
            state_desc = f"streaming text ({len(last_text)} chars)"
        else:
            state_desc = "waiting for response"

        # Check thinking & citations in DOM with provider-specific logic
        scan_data: dict[str, Any] = {"is_thinking": False, "thinking_text": "", "thinking_steps": [], "citations": []}
        try:
            raw_scan = await page.evaluate(DOM_SCAN_THINKING_AND_CITATIONS, provider)
            if isinstance(raw_scan, dict):
                scan_data = raw_scan
        except Exception as exc:
            if is_target_closed_error(exc):
                return CompletionResult(done=False, reason="page_closed", text=last_text, blocking_detail=str(exc))
            logger.debug("dom_scan_eval_failed", error=str(exc))

        is_thinking = bool(scan_data.get("is_thinking") or generating)
        thinking_text = str(scan_data.get("thinking_text") or "")
        thinking_steps = list(scan_data.get("thinking_steps") or [])
        citations = scan_data.get("citations", [])

        if on_poll is not None:
            try:
                await on_poll(
                    state=state_desc,
                    generating=generating,
                    is_thinking=is_thinking,
                    thinking_text=thinking_text,
                    thinking_steps=thinking_steps,
                    citations=citations,
                    last_text=last_text,
                    poll_count=poll_count,
                    elapsed_s=round(elapsed, 1),
                )
            except Exception as exc:
                logger.debug("on_poll_callback_failed", error=str(exc))

        logger.info(
            "wait_for_completion_poll",
            poll=poll_count,
            elapsed_s=round(elapsed, 1),
            state=state_desc,
            generating=generating,
            is_thinking=is_thinking,
            citations_count=len(citations),
            done_marker=done_marker,
            text_len=len(last_text),
            text_stable=text_stable,
        )

        if done:
            if reason == "done_marker" and done_marker_delay_s > 0:
                # Mistral renders the copy button skeleton before populating the
                # answer text — give the UI time to catch up, then re-read.
                logger.info("done_marker_delay", delay_s=done_marker_delay_s, provider=provider_cfg.get("name", ""))
                await sleep(done_marker_delay_s)
                last_text = await _answer_text(page, answer_chain)
            return CompletionResult(done=True, reason=reason, text=last_text)

        # In thinking/generating mode, use thinking_interval_s (default 1.0s from THINKING_INTERVAL_CHECK=1s)
        effective_interval = thinking_interval_s if thinking_interval_s is not None else 1.0
        if generating or is_thinking:
            await sleep(effective_interval)
        else:
            await sleep(random.uniform(min_poll, max_poll))

    return CompletionResult(done=False, reason="timeout", text=last_text)
