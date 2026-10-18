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

    // 1.2. Copilot-specific: Open ChainOfThought thinking steps & Sources button if closed
    if (provider === "copilot" || !provider) {
        try {
            // A. Expand ChainOfThought cards/details by clicking scc-ChainOfThought toggles
            const cotToggles = document.querySelectorAll(
                "[class*='scc-ChainOfThought']:not([class*='scc-ChainOfThought__card']):not([class*='scc-ChainOfThought__description']):not([class*='scc-ChainOfThought__body']):not([class*='scc-ChainOfThought__detail']), " +
                "button[class*='scc-ChainOfThought'], " +
                "[class*='scc-ChainOfThought__header'], " +
                "[class*='scc-ChainOfThought__toggle'], " +
                "[class*='scc-ChainOfThought__title']"
            );
            for (const toggle of cotToggles) {
                const isExpanded = toggle.getAttribute("aria-expanded");
                if (isExpanded === "false" || isExpanded === null) {
                    const attempts = parseInt(toggle.dataset.expandAttempts || "0", 10);
                    if (attempts < 5) {
                        toggle.dataset.expandAttempts = (attempts + 1).toString();
                        triggerClick(toggle);
                    }
                }
            }

            // B. Click Sources button to reveal detailed sources/citations
            const sourcesBtn = document.querySelector(
                "button[data-testid='sources-button-testid'], " +
                "button[aria-label='Sources'], " +
                "[data-testid='sources-button-testid']"
            );
            if (sourcesBtn) {
                const isExpanded = sourcesBtn.getAttribute("aria-expanded");
                if (isExpanded === "false" || isExpanded === null) {
                    const attempts = parseInt(sourcesBtn.dataset.expandAttempts || "0", 10);
                    if (attempts < 5) {
                        sourcesBtn.dataset.expandAttempts = (attempts + 1).toString();
                        triggerClick(sourcesBtn);
                    }
                }
            }
        } catch (e) {}
    }

    // 1.3. Gemini-specific: Open thoughts/thinking accordion if closed
    if (provider === "gemini" || !provider) {
        try {
            const thoughtToggles = document.querySelectorAll(
                ".thoughts-container button, " +
                ".thoughts-wrapper button, " +
                "button.thoughts-header, " +
                "button.thoughts-toggle, " +
                "button[aria-label*='suy nghĩ' i], " +
                "button[aria-label*='thought' i], " +
                "button[aria-label*='thinking' i], " +
                "expandable-section[data-test-id*='thought'] [data-test-id='expandable-section-toggle'], " +
                "[data-test-id*='thought-toggle']"
            );
            for (const toggle of thoughtToggles) {
                const isExpanded = toggle.getAttribute("aria-expanded");
                if (isExpanded === "false") {
                    const attempts = parseInt(toggle.dataset.expandAttempts || "0", 10);
                    if (attempts < 5) {
                        toggle.dataset.expandAttempts = (attempts + 1).toString();
                        triggerClick(toggle);
                    }
                }
            }
        } catch (e) {}
    }

    // 1.4. ChatGPT-specific: Open thought/reasoning accordion if present and closed
    if (provider === "chatgpt" || !provider) {
        try {
            const thoughtToggles = document.querySelectorAll(
                "button[aria-label*='Thought' i], " +
                "button[aria-label*='Thinking' i], " +
                "button[aria-label*='Worked' i], " +
                "button[data-testid*='thought'], " +
                "[class*='thought'] button"
            );
            for (const toggle of thoughtToggles) {
                const isExpanded = toggle.getAttribute("aria-expanded");
                if (isExpanded === "false") {
                    const attempts = parseInt(toggle.dataset.expandAttempts || "0", 10);
                    if (attempts < 5) {
                        toggle.dataset.expandAttempts = (attempts + 1).toString();
                        triggerClick(toggle);
                    }
                }
            }

            // Also check buttons matching "Worked for ..." or "Thought for ..."
            const candidateButtons = document.querySelectorAll("button, [role='button'], summary");
            for (const btn of candidateButtons) {
                const txt = clean(btn.innerText || btn.textContent || "");
                if (/(?:worked|thought)\\s+for\\s+\\d+/i.test(txt)) {
                    const isExpanded = btn.getAttribute("aria-expanded");
                    if (isExpanded === "false") {
                        const attempts = parseInt(btn.dataset.expandAttempts || "0", 10);
                        if (attempts < 5) {
                            btn.dataset.expandAttempts = (attempts + 1).toString();
                            triggerClick(btn);
                        }
                    }
                }
            }
        } catch (e) {}
    }

    // 1.5. Mistral-specific: Open Thinking / harness-steps accordion and Expand button if truncated
    if (provider === "mistral" || !provider) {
        try {
            // A. Expand Thinking collapsible triggers if closed
            const mistralTriggers = document.querySelectorAll(
                "button[id^='collapsible-trigger-'][data-state='closed'], " +
                "button[aria-controls^='collapsible-content-'][aria-expanded='false'], " +
                "div[data-testid='harness-steps-summary'] button, " +
                "div[data-testid='harness-steps-summary']"
            );
            for (const trg of mistralTriggers) {
                const btn = trg.tagName === "BUTTON" ? trg : (trg.closest("button") || trg.querySelector("button"));
                if (btn && btn.getAttribute("aria-expanded") === "false") {
                    const attempts = parseInt(btn.dataset.expandAttempts || "0", 10);
                    if (attempts < 5) {
                        btn.dataset.expandAttempts = (attempts + 1).toString();
                        triggerClick(btn);
                    }
                }
            }

            // B. If 'Content truncated' paragraph is found, click Expand button at footer
            const textNodes = document.querySelectorAll("p, div, span");
            for (const el of textNodes) {
                if (/content\s+truncated/i.test(el.innerText || el.textContent || "")) {
                    const container = el.closest("div") || el.parentElement;
                    if (container) {
                        const expandBtn = container.querySelector("button, [role='button']") ||
                                          document.querySelector("button[aria-label*='Expand' i]");
                        if (expandBtn) {
                            const attempts = parseInt(expandBtn.dataset.expandAttempts || "0", 10);
                            if (attempts < 5) {
                                expandBtn.dataset.expandAttempts = (attempts + 1).toString();
                                triggerClick(expandBtn);
                            }
                        }
                    }
                }
            }
        } catch (e) {}
    }

    // 1.6. Zhipu-specific: Open thought process accordion / summary inside .chat-assistant if closed
    if (provider === "zhipu" || !provider) {
        try {
            const zhipuAssts = document.querySelectorAll(".chat-assistant, [class*='chat-assistant']");
            const targetAsst = zhipuAssts.length > 0 ? zhipuAssts[zhipuAssts.length - 1] : null;
            if (targetAsst) {
                const detailsEls = targetAsst.querySelectorAll("details:not([open])");
                for (const d of detailsEls) {
                    const sum = d.querySelector("summary");
                    if (sum) {
                        const attempts = parseInt(sum.dataset.expandAttempts || "0", 10);
                        if (attempts < 5) {
                            sum.dataset.expandAttempts = (attempts + 1).toString();
                            triggerClick(sum);
                        }
                    }
                }
                const thoughtButtons = targetAsst.querySelectorAll(
                    "button[class*='thought'], " +
                    "button:has-text('Thought Process'), " +
                    "button:has-text('Thinking'), " +
                    "button[aria-label*='Thought' i], " +
                    "button[aria-label*='Thinking' i], " +
                    "[class*='thought-process'] button"
                );
                for (const btn of thoughtButtons) {
                    if (btn.getAttribute("aria-expanded") === "false") {
                        const attempts = parseInt(btn.dataset.expandAttempts || "0", 10);
                        if (attempts < 5) {
                            btn.dataset.expandAttempts = (attempts + 1).toString();
                            triggerClick(btn);
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

        // Sequential thinking: all steps prior to the latest active card are completed
        for (let sIdx = 0; sIdx < thinkingSteps.length - 1; sIdx++) {
            thinkingSteps[sIdx].status = "completed";
        }
    } catch (e) {}

    // 2.2. Copilot-specific: Extract from scc-ChainOfThought* and scc-BebopChainOfThought*
    if (provider === "copilot" || !provider) {
        try {
            // Find all ChainOfThought root containers
            const cotContainers = document.querySelectorAll(
                "[class*='scc-ChainOfThought'], " +
                "[class*='scc-BebopChainOfThought'], " +
                "[class*='ChainOfThought']"
            );

            for (const cotRoot of cotContainers) {
                // If this is a nested element inside another ChainOfThought container, avoid duplicate root processing
                if (cotRoot.parentElement && cotRoot.parentElement.closest("[class*='scc-ChainOfThought'], [class*='scc-BebopChainOfThought']")) {
                    continue;
                }

                // Check overall expand button / header text (e.g. "Reasoning completed in 7 steps" or "Thinking...")
                const mainHeaderEl = cotRoot.querySelector(
                    "[class*='ChainOfThought__headerText'], [class*='ChainOfThought__expandButton'], button[id*='expand-button'], button[title*='Reasoning']"
                );
                const overallHeader = clean(mainHeaderEl ? (mainHeaderEl.innerText || mainHeaderEl.textContent || mainHeaderEl.getAttribute("title") || "") : "");

                // Query all item elements within the ChainOfThought container
                const stepItems = cotRoot.querySelectorAll(
                    "div[role='listitem'][class*='ChainOfThoughtItem'], " +
                    "div[role='listitem'][class*='scc-'], " +
                    "div[role='listitem'], " +
                    "[class*='scc-BebopChainOfThoughtItem']:not([class*='__']), " +
                    "[class*='scc-ChainOfThoughtItem']:not([class*='__']), " +
                    "[class*='ChainOfThoughtItem']:not([class*='__']), " +
                    "[class*='scc-ChainOfThought__step'], " +
                    "[class*='scc-ChainOfThought__item']"
                );

                // Filter out sub-elements that are inside already selected listitems
                const validItems = [];
                for (const it of stepItems) {
                    const isSubHeaderOrContent = it.className.includes("__header") ||
                                                 it.className.includes("__content") ||
                                                 it.className.includes("__statusIndicator") ||
                                                 it.className.includes("__contentText");
                    if (isSubHeaderOrContent) {
                        continue;
                    }
                    // Avoid nested duplicate listitems
                    if (it.parentElement && it.parentElement.closest("div[role='listitem']")) {
                        continue;
                    }
                    validItems.push(it);
                }

                if (validItems.length > 0) {
                    for (let idx = 0; idx < validItems.length; idx++) {
                        const item = validItems[idx];

                        // Extract title from header or h3/h4/h5
                        let title = "";
                        const titleEl = item.querySelector(
                            "[class*='headerText'], [class*='header'], h3, h4, h5, [role='heading'], strong"
                        ) || item;
                        if (titleEl) {
                            const cloneH = titleEl.cloneNode(true);
                            cloneH.querySelectorAll("svg, button, [class*='icon'], [class*='statusIndicator']").forEach(i => i.remove());
                            title = clean(cloneH.innerText || cloneH.textContent);
                        }

                        // Extract description
                        let description = "";
                        const contentEl = item.querySelector(
                            "[class*='contentText'], [class*='content'], [class*='description'], [class*='pills'], [class*='interstitialPillsContainer']"
                        );

                        if (contentEl) {
                            // Check for search pills (e.g. .r1fgiwrn or interstitial pills)
                            let pillEls = contentEl.querySelectorAll(".r1fgiwrn");
                            if (pillEls.length === 0) {
                                pillEls = contentEl.querySelectorAll("[class*='Pill'], [class*='pill'], [class*='pillsContainer'] > span");
                            }
                            const pillTexts = [];
                            for (const pEl of pillEls) {
                                const pt = clean(pEl.innerText || pEl.textContent || pEl.getAttribute("aria-label") || "");
                                if (pt && !pillTexts.includes(pt) && pt !== "true") pillTexts.push(pt);
                            }

                            // Check for paragraphs
                            const pEls = contentEl.querySelectorAll("p, li");
                            const pTexts = [];
                            for (const p of pEls) {
                                const pt = clean(p.innerText || p.textContent || "");
                                if (pt && !pTexts.includes(pt)) pTexts.push(pt);
                            }

                            if (pTexts.length > 0) {
                                description = pTexts.join("\\n\\n");
                            } else if (pillTexts.length > 0) {
                                description = pillTexts.join("\\n");
                            } else {
                                const cloneC = contentEl.cloneNode(true);
                                cloneC.querySelectorAll("svg, button").forEach(i => i.remove());
                                description = clean(cloneC.innerText || cloneC.textContent || "");
                            }
                        } else {
                            const cloneAll = item.cloneNode(true);
                            cloneAll.querySelectorAll("svg, button, h3, h4, h5, [class*='header']").forEach(i => i.remove());
                            description = clean(cloneAll.innerText || cloneAll.textContent || "");
                        }

                        if (!title && description) {
                            const lines = description.split("\\n").map(l => clean(l)).filter(Boolean);
                            if (lines.length > 1) {
                                title = lines[0];
                                description = lines.slice(1).join("\\n\\n");
                            } else {
                                title = description;
                                description = "";
                            }
                        }

                        if (title) {
                            // Determine step status
                            const statusIndicator = item.querySelector("[class*='statusIndicator']");
                            const isCompleted = item.className.includes("completed") ||
                                                (statusIndicator && statusIndicator.querySelector("svg path[d*='M10 2a8']") !== null) ||
                                                item.querySelector("[class*='Checkmark'], [class*='check'], [class*='success'], [data-icon-name*='Checkmark']") !== null;
                            const isRunning = item.className.includes("running") ||
                                              item.className.includes("loading") ||
                                              item.querySelector("[class*='spinner'], [class*='loading'], [class*='ProgressRing'], svg[class*='spin'], [data-icon-name*='Sync']") !== null;
                            const stepStatus = isCompleted ? "completed" : (isRunning ? "running" : (description ? "completed" : "running"));

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
                    }
                } else if (overallHeader) {
                    // Fallback to overallHeader if listitems are not yet expanded or rendered
                    isThinking = true;
                    if (!seenStepKeys.has(overallHeader)) {
                        seenStepKeys.add(overallHeader);
                        thinkingSteps.push({
                            title: overallHeader,
                            description: "",
                            status: "running"
                        });
                    }
                }
            }

            // Sequential thinking: all steps prior to the latest active card are completed
            for (let sIdx = 0; sIdx < thinkingSteps.length - 1; sIdx++) {
                thinkingSteps[sIdx].status = "completed";
            }
        } catch (e) {}
    }

    // 2.3. Gemini-specific: Extract structured thinking steps
    if (provider === "gemini" || !provider) {
        try {
            // Check for live processing indicator in Gemini
            const processingEl = document.querySelector(
                ".response-container-header-processing-state, " +
                "thinking-overlay, " +
                ".thinking-dots-animation, " +
                "[data-test-id*='thinking-state'], " +
                ".pending-status"
            );
            if (processingEl) {
                isThinking = true;
                const procText = clean(processingEl.innerText || processingEl.textContent);
                if (procText && !seenStepKeys.has(procText)) {
                    seenStepKeys.add(procText);
                    thinkingSteps.push({
                        title: procText,
                        description: "",
                        status: "in_progress"
                    });
                }
            }

            // Check for thoughts containers and structured step elements
            const thoughtsContainers = document.querySelectorAll(
                ".thoughts-container, " +
                ".thoughts-wrapper, " +
                ".thoughts-content, " +
                "spark-thinking-steps, " +
                ".is-embedded-thought"
            );
            for (const container of thoughtsContainers) {
                // If container has structured steps or list items
                const stepItems = container.querySelectorAll("spark-thinking-steps .step, li, .step-item, div[class*='step']");
                if (stepItems && stepItems.length > 0) {
                    for (const item of stepItems) {
                        const titleEl = item.querySelector(".step-title, strong, h4, h5") || item;
                        const title = clean(titleEl.innerText || titleEl.textContent);
                        let description = "";
                        const descEl = item.querySelector(".step-description, .step-desc, p");
                        if (descEl && descEl !== titleEl) {
                            description = clean(descEl.innerText || descEl.textContent);
                        }
                        if (title && !seenStepKeys.has(title)) {
                            seenStepKeys.add(title);
                            isThinking = true;
                            thinkingSteps.push({
                                title: title,
                                description: description,
                                status: "completed"
                            });
                        }
                    }
                } else {
                    // Fallback: entire thoughts content text
                    const fullText = clean(container.innerText || container.textContent);
                    if (fullText && fullText.length > 3 && !seenStepKeys.has(fullText)) {
                        seenStepKeys.add(fullText);
                        isThinking = true;
                        thinkingSteps.push({
                            title: fullText.length > 60 ? fullText.slice(0, 57) + "..." : fullText,
                            description: fullText.length > 60 ? fullText : "",
                            status: "completed"
                        });
                    }
                }
            }
        } catch (e) {}
    }

    // 2.4. ChatGPT-specific: Extract thinking steps and status
    if (provider === "chatgpt" || !provider) {
        try {
            const WORKED_FOR_REGEX = /(?:worked|thought)\\s+for\\s+(?:(?:\\d+\\s*m(?:in(?:ute)?s?)?\\s*)?\\d+\\s*s(?:ec(?:ond)?s?)?|\\d+\\s*m(?:in(?:ute)?s?)?)|(?:đã\\s+)?suy\\s+nghĩ\\s+trong\\s+\\d+/i;

            const asstMessages = document.querySelectorAll(
                "div[data-message-author-role='assistant'], article[data-testid*='conversation-turn'], main"
            );
            const asstRoot = asstMessages.length > 0 ? asstMessages[asstMessages.length - 1] : document.body;

            // Strategy 1: Look for active Skip button
            // In ChatGPT, during reasoning: Header has "Thinking" label with "Skip" button on the right hand side
            let skipButton = null;
            const buttons = asstRoot.querySelectorAll("button");
            for (const btn of buttons) {
                const txt = clean(btn.innerText || btn.textContent || "").toLowerCase();
                const aria = (btn.getAttribute("aria-label") || "").toLowerCase();
                if (txt === "skip" || aria === "skip" || aria.includes("skip thinking")) {
                    skipButton = btn;
                    break;
                }
            }
            if (!skipButton) {
                const allButtons = document.querySelectorAll("button");
                for (let i = allButtons.length - 1; i >= 0; i--) {
                    const btn = allButtons[i];
                    const txt = clean(btn.innerText || btn.textContent || "").toLowerCase();
                    const aria = (btn.getAttribute("aria-label") || "").toLowerCase();
                    if (txt === "skip" || aria === "skip" || aria.includes("skip thinking")) {
                        skipButton = btn;
                        break;
                    }
                }
            }

            if (skipButton) {
                isThinking = true;
                let headerRow = skipButton.parentElement;
                while (
                    headerRow &&
                    headerRow !== asstRoot &&
                    headerRow !== document.body &&
                    !/thinking|suy nghĩ/i.test(headerRow.innerText || "") &&
                    headerRow.parentElement
                ) {
                    headerRow = headerRow.parentElement;
                }

                let title = "Thinking";
                if (headerRow) {
                    const clone = headerRow.cloneNode(true);
                    clone.querySelectorAll("button, svg, [class*='icon']").forEach(i => i.remove());
                    const t = clean(clone.innerText || clone.textContent || "");
                    if (t) title = t;
                }

                // Extract thinking content below headerRow
                let description = "";
                if (headerRow && headerRow.parentElement) {
                    const container = headerRow.parentElement;
                    const contentEl = container.querySelector(
                        "[data-markdown-text-tone='tertiary'], [class*='thought'], [class*='reasoning'], .prose, .markdown"
                    );
                    if (contentEl && !headerRow.contains(contentEl)) {
                        const pTags = contentEl.querySelectorAll("p, li, div[class*='paragraph']");
                        if (pTags && pTags.length > 0) {
                            const lines = [];
                            for (const p of pTags) {
                                const pt = clean(p.innerText || p.textContent || "");
                                if (pt && !lines.includes(pt)) lines.push(pt);
                            }
                            if (lines.length > 0) description = lines.join("\\n\\n");
                        }
                        if (!description) {
                            description = clean(contentEl.innerText || contentEl.textContent || "");
                        }
                    } else {
                        const siblings = [];
                        let sib = headerRow.nextElementSibling;
                        while (sib) {
                            const isFinalAnswer = sib.getAttribute("data-message-author-role") === "assistant" ||
                                (sib.getAttribute("data-markdown-text-style") === "assistant-message" &&
                                 sib.getAttribute("data-markdown-text-tone") !== "tertiary");
                            if (isFinalAnswer) break;

                            const sTxt = clean(sib.innerText || sib.textContent || "");
                            if (sTxt) siblings.push(sTxt);
                            sib = sib.nextElementSibling;
                        }
                        if (siblings.length > 0) {
                            description = siblings.join("\\n\\n");
                        } else {
                            const cloneCont = container.cloneNode(true);
                            const cloneH = cloneCont.querySelector("button")?.closest(headerRow.tagName.toLowerCase());
                            if (cloneH) cloneH.remove();
                            description = clean(cloneCont.innerText || cloneCont.textContent || "");
                        }
                    }
                }

                if (description.toLowerCase().startsWith(title.toLowerCase())) {
                    description = description.slice(title.length).trim();
                }

                const dedupeKey = title + "::" + description;
                if (!seenStepKeys.has(dedupeKey)) {
                    seenStepKeys.add(dedupeKey);
                    thinkingSteps.push({
                        title: title,
                        description: description,
                        status: "running"
                    });
                }
                if (description) {
                    thinkingText = description;
                }
            } else {
                // Strategy 2: Look for completed reasoning header "Worked for {x}m {xx}s" / "Thought for {x}s"
                const candidateEls = asstRoot.querySelectorAll(
                    "button, summary, div[role='button'], [data-testid*='thought'], div[class*='thought'], div[class*='reasoning'], span, h4, h5, div"
                );
                let completedEl = null;
                let completedTitle = "";

                for (let i = candidateEls.length - 1; i >= 0; i--) {
                    const el = candidateEls[i];
                    if ((el.innerText || "").length > 200) continue;
                    const txt = clean(el.innerText || el.textContent || "");
                    const m = txt.match(WORKED_FOR_REGEX);
                    if (m) {
                        completedEl = el;
                        completedTitle = m[0];
                        break;
                    }
                }

                if (completedEl) {
                    isThinking = true;
                    if (completedEl.getAttribute("aria-expanded") === "false") {
                        const attempts = parseInt(completedEl.dataset.expandAttempts || "0", 10);
                        if (attempts < 5) {
                            completedEl.dataset.expandAttempts = (attempts + 1).toString();
                            triggerClick(completedEl);
                        }
                    }

                    let description = "";
                    const container = completedEl.closest("div[class*='thought'], div[class*='reasoning'], [data-testid*='thought']") || completedEl.parentElement;

                    if (container) {
                        const contentEl = container.querySelector(
                            "[data-markdown-text-tone='tertiary'], [class*='thought'], [class*='reasoning'], .prose, .markdown"
                        );
                        if (contentEl && !completedEl.contains(contentEl)) {
                            const pTags = contentEl.querySelectorAll("p, li, div[class*='paragraph']");
                            if (pTags && pTags.length > 0) {
                                const lines = [];
                                for (const p of pTags) {
                                    const pt = clean(p.innerText || p.textContent || "");
                                    if (pt && !lines.includes(pt)) lines.push(pt);
                                }
                                if (lines.length > 0) description = lines.join("\\n\\n");
                            }
                            if (!description) {
                                description = clean(contentEl.innerText || contentEl.textContent || "");
                            }
                        } else {
                            const siblings = [];
                            let sib = completedEl.nextElementSibling;
                            while (sib) {
                                const isFinalAnswer = sib.getAttribute("data-message-author-role") === "assistant" ||
                                    (sib.getAttribute("data-markdown-text-style") === "assistant-message" &&
                                     sib.getAttribute("data-markdown-text-tone") !== "tertiary");
                                if (isFinalAnswer) break;

                                const sTxt = clean(sib.innerText || sib.textContent || "");
                                if (sTxt) siblings.push(sTxt);
                                sib = sib.nextElementSibling;
                            }
                            if (siblings.length > 0) {
                                description = siblings.join("\\n\\n");
                            } else {
                                const cloneCont = container.cloneNode(true);
                                cloneCont.querySelectorAll("button, summary, svg, [class*='icon']").forEach(i => i.remove());
                                description = clean(cloneCont.innerText || cloneCont.textContent || "");
                            }
                        }
                    }

                    if (description.startsWith(completedTitle)) {
                        description = description.slice(completedTitle.length).trim();
                    }

                    const dedupeKey = completedTitle + "::" + description;
                    if (!seenStepKeys.has(dedupeKey)) {
                        seenStepKeys.add(dedupeKey);
                        thinkingSteps.push({
                            title: completedTitle,
                            description: description,
                            status: "completed"
                        });
                    }
                    if (description) {
                        thinkingText = description;
                    }
                } else {
                    // Strategy 3: Check for "Thinking" label (without Skip button yet, e.g. early streaming)
                    const thinkingEls = asstRoot.querySelectorAll(
                        "button, summary, div[role='button'], [data-testid*='thought'], div[class*='thought'], div[class*='reasoning'], span, div"
                    );
                    for (let i = thinkingEls.length - 1; i >= 0; i--) {
                        const el = thinkingEls[i];
                        if ((el.innerText || "").length > 100) continue;
                        const txt = clean(el.innerText || el.textContent || "");
                        if (/^thinking(?:\\.\\.\\.)?$/i.test(txt) || /^đang suy nghĩ(?:\\.\\.\\.)?$/i.test(txt)) {
                            isThinking = true;
                            let description = "";
                            const container = el.parentElement;
                            if (container) {
                                const clone = container.cloneNode(true);
                                clone.querySelectorAll("svg, button").forEach(i => i.remove());
                                description = clean(clone.innerText || clone.textContent || "");
                                if (description.toLowerCase().startsWith("thinking")) {
                                    description = description.slice(8).trim();
                                }
                            }
                            const dedupeKey = "Thinking::" + description;
                            if (!seenStepKeys.has(dedupeKey)) {
                                seenStepKeys.add(dedupeKey);
                                thinkingSteps.push({
                                    title: "Thinking",
                                    description: description,
                                    status: "running"
                                });
                            }
                            if (description) {
                                thinkingText = description;
                            }
                            break;
                        }
                    }
                }
            }
        } catch (e) {}
    }

    // 2.5. Mistral-specific: Extract structured thinking and research steps
    if (provider === "mistral" || !provider) {
        try {
            // Check Stop generation button or active spinners
            const mistralStopBtn = document.querySelector(
                "button[aria-label='Stop generation'], " +
                "button[aria-label*='Stop' i]"
            );
            const isMistralGenerating = mistralStopBtn && (mistralStopBtn.offsetParent !== null || mistralStopBtn.getAttribute("aria-disabled") !== "true");
            if (isMistralGenerating) {
                isThinking = true;
            }

            // Find reasoning parts
            const reasoningEls = document.querySelectorAll("div[data-message-part-type='reasoning']");
            if (isMistralGenerating && reasoningEls.length > 0) {
                isThinking = true;
            }
            for (const rEl of reasoningEls) {
                const stepItem = rEl.closest("div[id^='collapsible-content-']") || rEl.closest(".flex.flex-col") || rEl.parentElement;
                let stepTitle = "";
                let stepStatus = "completed";

                const triggerId = stepItem ? stepItem.getAttribute("aria-labelledby") : null;
                let triggerBtn = triggerId ? document.getElementById(triggerId) : null;
                if (!triggerBtn && stepItem && stepItem.parentElement) {
                    triggerBtn = stepItem.parentElement.querySelector("button[id^='collapsible-trigger-']");
                }
                if (triggerBtn) {
                    stepTitle = clean(triggerBtn.innerText || triggerBtn.textContent || "");
                }
                if (!stepTitle) {
                    const summaryEl = document.querySelector("div[data-testid='harness-steps-summary']");
                    if (summaryEl) {
                        stepTitle = clean(summaryEl.innerText || summaryEl.textContent || "");
                    }
                }
                if (!stepTitle) {
                    stepTitle = "Thinking";
                }

                const spinEl = stepItem ? stepItem.parentElement.querySelector("[data-step-state='running'], .animate-spin") : null;
                if (spinEl || (isMistralGenerating && reasoningEls.length === 1)) {
                    stepStatus = "running";
                }

                const paragraphs = Array.from(rEl.querySelectorAll("p")).map(p => clean(p.innerText || p.textContent)).filter(Boolean);
                const fullDesc = paragraphs.join("\\n\\n") || clean(rEl.innerText || rEl.textContent || "");
                if (fullDesc) {
                    thinkingText = (thinkingText ? thinkingText + "\\n\\n" : "") + fullDesc;
                }

                const dedupeKey = stepTitle + "::" + fullDesc;
                if (!seenStepKeys.has(dedupeKey)) {
                    seenStepKeys.add(dedupeKey);
                    thinkingSteps.push({
                        title: stepTitle,
                        description: fullDesc,
                        status: stepStatus
                    });
                }
            }

            // Fallback for Mistral harness steps summary if reasoning blocks are not yet present
            if (thinkingSteps.length === 0) {
                const summaryEl = document.querySelector("div[data-testid='harness-steps-summary']");
                if (summaryEl) {
                    const sTitle = clean(summaryEl.innerText || summaryEl.textContent || "Thinking");
                    isThinking = true;
                    const dedupeKey = sTitle + "::summary";
                    if (!seenStepKeys.has(dedupeKey)) {
                        seenStepKeys.add(dedupeKey);
                        thinkingSteps.push({
                            title: sTitle,
                            description: "Đang suy luận...",
                            status: isMistralGenerating ? "running" : "completed"
                        });
                    }
                }
            }

            // Sequential: all steps prior to the latest active are completed
            for (let sIdx = 0; sIdx < thinkingSteps.length - 1; sIdx++) {
                thinkingSteps[sIdx].status = "completed";
            }
        } catch (e) {}
    }

    // 2.6. Zhipu-specific: Extract structured thinking steps and thinking text from .chat-assistant
    if (provider === "zhipu" || !provider) {
        try {
            const zhipuStopBtn = document.querySelector(
                "button:has-text('Stop'), " +
                "button:has-text('停止'), " +
                "button[aria-label*='Stop' i], " +
                "button[aria-label*='停止'], " +
                "button[class*='stop' i], " +
                "button[data-testid*='stop']"
            );
            const isZhipuGenerating = zhipuStopBtn && (zhipuStopBtn.offsetParent !== null || zhipuStopBtn.getAttribute("aria-disabled") !== "true");

            const hasConfirmPreferences = Array.from(document.querySelectorAll("div, form, [role='dialog']")).some(el => {
                if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                    const t = (el.innerText || el.textContent || "").toLowerCase();
                    return t.includes("confirm preferences") || t.includes("confirm preference") || t.includes("确认偏好") || t.includes("偏好确认");
                }
                return false;
            });

            if (hasConfirmPreferences) {
                isThinking = true;
                const prefTitle = "Confirm Preferences";
                const prefDesc = "Đang chờ cấu hình mặc định hoặc tự động tiếp tục...";
                const dedupeKey = prefTitle + "::" + prefDesc;
                if (!seenStepKeys.has(dedupeKey)) {
                    seenStepKeys.add(dedupeKey);
                    thinkingSteps.push({
                        title: prefTitle,
                        description: prefDesc,
                        status: "running"
                    });
                }
            }

            const asstEls = document.querySelectorAll(".chat-assistant, [class*='chat-assistant']");
            if (asstEls.length > 0) {
                const lastAsst = asstEls[asstEls.length - 1];
                const isTyping = lastAsst.querySelector(".cursor, [class*='cursor'], [class*='typing'], [class*='loading'], svg.animate-spin") !== null;
                if (isZhipuGenerating || isTyping) {
                    isThinking = true;
                }

                const thoughtEls = lastAsst.querySelectorAll(
                    "[class*='thought'], [class*='reasoning'], details, [class*='thinking'], [aria-label*='thought' i], [aria-label*='thinking' i]"
                );

                for (const tEl of thoughtEls) {
                    let stepTitle = "";
                    const summaryEl = tEl.querySelector("summary, button, [class*='title'], [class*='header']");
                    if (summaryEl) {
                        stepTitle = clean(summaryEl.innerText || summaryEl.textContent || "");
                    }
                    if (!stepTitle) {
                        stepTitle = "Thought Process";
                    }

                    let thoughtDesc = "";
                    const descEl = tEl.querySelector(".markdown, .markdown-body, [class*='content'], p") || tEl;
                    if (descEl) {
                        const clone = descEl.cloneNode(true);
                        clone.querySelectorAll("summary, button, svg").forEach(i => i.remove());
                        thoughtDesc = clean(clone.innerText || clone.textContent || "");
                    }

                    if (thoughtDesc) {
                        thinkingText = (thinkingText ? thinkingText + "\\n\\n" : "") + thoughtDesc;
                        isThinking = true;
                        const dedupeKey = stepTitle + "::" + thoughtDesc;
                        if (!seenStepKeys.has(dedupeKey)) {
                            seenStepKeys.add(dedupeKey);
                            thinkingSteps.push({
                                title: stepTitle,
                                description: thoughtDesc,
                                status: isZhipuGenerating ? "running" : "completed"
                            });
                        }
                    }
                }

                if ((isZhipuGenerating || isTyping) && thinkingSteps.length === 0) {
                    const fallbackKey = "Thinking::Zhipu";
                    if (!seenStepKeys.has(fallbackKey)) {
                        seenStepKeys.add(fallbackKey);
                        thinkingSteps.push({
                            title: "Thinking Process",
                            description: "Đang suy luận...",
                            status: "running"
                        });
                    }
                }
            }
        } catch (e) {}
    }

    // 2.7. Minimax-specific: Extract structured thinking steps and thinking text from [data-testid="chat-main-conversation"]
    if (provider === "minimax" || !provider) {
        try {
            const root = document.querySelector("[data-testid='chat-main-conversation']");
            if (root) {
                // Check if stop button is present inside chat-main-conversation or document
                const stopBtn = root.querySelector("[data-testid='stop-button'], button[aria-label*='Stop' i], div[aria-label*='Stop' i]") ||
                                document.querySelector("[data-testid='stop-button'], button[aria-label*='Stop' i], div[aria-label*='Stop' i]");
                const isMinimaxGenerating = stopBtn && (stopBtn.offsetParent !== null || stopBtn.getAttribute("aria-disabled") !== "true");
                if (isMinimaxGenerating) {
                    isThinking = true;
                }

                // Look for assistant messages inside chat-main-conversation
                const asstEls = root.querySelectorAll("[data-message-role='assistant'], [data-role='assistant'], div.mb-4.mavis-assistant-reading-row");
                if (asstEls.length > 0) {
                    const lastAsst = asstEls[asstEls.length - 1];

                    // Look for thinking detail / disclosure inside lastAsst (or root)
                    const detailEl = lastAsst.querySelector("[data-testid='turn-process-detail']") ||
                                     root.querySelector("[data-testid='turn-process-detail']");
                    const disclosure = lastAsst.querySelector("[data-testid='turn-process-disclosure'], section.mavis-turn-process-disclosure") ||
                                       root.querySelector("[data-testid='turn-process-disclosure'], section.mavis-turn-process-disclosure");

                    const container = detailEl || disclosure;

                    if (container) {
                        isThinking = true;

                        // Summary header (e.g. "Processing 1m 28s" or "Processed 25s")
                        let overallSummary = "";
                        const summaryEl = (disclosure || root).querySelector("[data-testid='turn-process-summary']");
                        if (summaryEl) {
                            overallSummary = clean(summaryEl.innerText || summaryEl.textContent || "");
                        }

                        // Loader label if streaming
                        let loaderLabel = "";
                        const loaderEl = (disclosure || container).querySelector("[data-testid='streaming-rose-loader-label'], .streaming-rose-loader-label");
                        if (loaderEl) {
                            loaderLabel = clean(loaderEl.innerText || loaderEl.textContent || "");
                        }

                        // Activity groups inside turn-process-detail / disclosure
                        const activityGroups = container.querySelectorAll("[data-testid='activity-group']");

                        for (let agIdx = 0; agIdx < activityGroups.length; agIdx++) {
                            const ag = activityGroups[agIdx];

                            let stepTitle = "";
                            const summaryHeader = ag.querySelector("[data-testid='activity-group-header-summary']");
                            if (summaryHeader) {
                                stepTitle = clean(summaryHeader.getAttribute("title") || summaryHeader.innerText || summaryHeader.textContent || "");
                            }
                            if (!stepTitle) {
                                const headerBtn = ag.querySelector("[data-testid='activity-group-header']");
                                if (headerBtn) {
                                    stepTitle = clean(headerBtn.getAttribute("aria-label") || headerBtn.innerText || headerBtn.textContent || "");
                                }
                            }
                            if (!stepTitle) {
                                const shimmer = ag.querySelector(".shimmer-text__label-text");
                                if (shimmer) {
                                    stepTitle = clean(shimmer.innerText || shimmer.textContent || "");
                                }
                            }
                            if (!stepTitle) {
                                stepTitle = overallSummary || loaderLabel || "Thinking Step";
                            }

                            // Extract description from inner markdown or following siblings
                            let stepDesc = "";
                            const innerMd = ag.querySelector(".matrix-markdown, .mavis-markdown-blocks, p");
                            if (innerMd) {
                                stepDesc = clean(innerMd.innerText || innerMd.textContent || "");
                            }
                            if (!stepDesc) {
                                let sib = ag.nextElementSibling;
                                while (sib && sib.getAttribute("data-testid") !== "activity-group") {
                                    if (sib.matches && (sib.matches(".matrix-markdown, [data-selection-anchor='text'], [class*='markdown']") || sib.querySelector(".matrix-markdown, p"))) {
                                        const pTags = Array.from(sib.querySelectorAll("p")).map(p => clean(p.innerText || p.textContent)).filter(Boolean);
                                        const txt = pTags.join("\\n\\n") || clean(sib.innerText || sib.textContent || "");
                                        if (txt) {
                                            stepDesc = (stepDesc ? stepDesc + "\\n\\n" : "") + txt;
                                        }
                                    }
                                    sib = sib.nextElementSibling;
                                }
                            }

                            const isLastGroup = agIdx === activityGroups.length - 1;
                            const stepStatus = (isMinimaxGenerating && isLastGroup) ? "running" : "completed";

                            const dedupeKey = stepTitle + "::" + stepDesc;
                            if (!seenStepKeys.has(dedupeKey)) {
                                seenStepKeys.add(dedupeKey);
                                thinkingSteps.push({
                                    title: stepTitle,
                                    description: stepDesc,
                                    status: stepStatus
                                });
                            }
                            if (stepDesc) {
                                thinkingText = (thinkingText ? thinkingText + "\\n\\n" : "") + stepDesc;
                            } else if (stepTitle) {
                                thinkingText = (thinkingText ? thinkingText + "\\n\\n" : "") + stepTitle;
                            }
                        }

                        // Also check active trailing blocks inside turn-process-detail during real-time streaming
                        const trailing = container.querySelector("[data-testid='assistant-active-trailing-blocks']");
                        if (trailing) {
                            const trailingTags = Array.from(trailing.querySelectorAll("p, .matrix-markdown")).map(el => clean(el.innerText || el.textContent)).filter(Boolean);
                            const trailingText = trailingTags.join("\\n\\n") || clean(trailing.innerText || trailing.textContent || "");
                            if (trailingText) {
                                if (thinkingSteps.length > 0 && isMinimaxGenerating) {
                                    const lastStep = thinkingSteps[thinkingSteps.length - 1];
                                    if (!lastStep.description || !lastStep.description.includes(trailingText)) {
                                        lastStep.description = lastStep.description ? lastStep.description + "\\n\\n" + trailingText : trailingText;
                                    }
                                } else {
                                    const title = loaderLabel || "Thinking Step";
                                    const dedupeKey = title + "::" + trailingText;
                                    if (!seenStepKeys.has(dedupeKey)) {
                                        seenStepKeys.add(dedupeKey);
                                        thinkingSteps.push({
                                            title: title,
                                            description: trailingText,
                                            status: "running"
                                        });
                                    }
                                }
                            }
                        }

                        // Fallback if detail/disclosure exists but no activity groups yet
                        if (thinkingSteps.length === 0 && (overallSummary || loaderLabel || isMinimaxGenerating)) {
                            const title = loaderLabel || overallSummary || "Thinking Process";
                            const desc = "Đang suy luận...";
                            const dedupeKey = title + "::" + desc;
                            if (!seenStepKeys.has(dedupeKey)) {
                                seenStepKeys.add(dedupeKey);
                                thinkingSteps.push({
                                    title: title,
                                    description: desc,
                                    status: isMinimaxGenerating ? "running" : "completed"
                                });
                            }
                            thinkingText = title;
                        }
                    } else if (isMinimaxGenerating) {
                        const fallbackKey = "Thinking::Minimax";
                        if (!seenStepKeys.has(fallbackKey)) {
                            seenStepKeys.add(fallbackKey);
                            thinkingSteps.push({
                                title: "Thinking Process",
                                description: "Đang suy luận...",
                                status: "running"
                            });
                        }
                    }

                    // Sequential completion: all steps prior to the latest active are completed
                    for (let sIdx = 0; sIdx < thinkingSteps.length - 1; sIdx++) {
                        thinkingSteps[sIdx].status = "completed";
                    }
                }
            }
        } catch (e) {}
    }

    // 2.8. Meta AI-specific: Extract thinking steps & sources from [data-testid="thinking-status"], right sidebar, and [data-testid="chat-main-conversation"]
    if (provider === "meta" || !provider) {
        try {
            const root = document.querySelector("[data-testid='chat-main-conversation']") || document;
            const stopBtn = document.querySelector(
                "[data-testid='chat-main-conversation'] [data-testid='stop-button'], " +
                "[data-testid='chat-main-conversation'] button[aria-label*='Stop' i], " +
                "button[aria-label*='Stop' i]"
            );
            const isMetaGenerating = stopBtn && (stopBtn.offsetParent !== null || stopBtn.getAttribute("aria-disabled") !== "true");
            if (isMetaGenerating) {
                isThinking = true;
            }

            // Check element with data-testid="thinking-status"
            const thinkingStatusEl = document.querySelector("[data-testid='thinking-status'], [data-testid*='thinking-status']");
            if (thinkingStatusEl) {
                isThinking = true;
                const statusText = clean(thinkingStatusEl.innerText || thinkingStatusEl.textContent || "");

                // Check and click to open the right sidebar showing detailed steps and Sources
                const rightSidebar = document.querySelector(
                    "[aria-label*='Thought' i], " +
                    "[aria-label*='Thinking' i], " +
                    "[data-testid*='thinking-panel'], " +
                    "[data-testid*='sidebar'], " +
                    "aside[role='complementary'], " +
                    "aside, " +
                    ".ecto-code-source-panel ~ aside"
                );
                if (!rightSidebar && thinkingStatusEl.click) {
                    try {
                        thinkingStatusEl.click();
                    } catch (err) {}
                }

                const sidebarOrRoot = document.querySelector(
                    "[aria-label*='Thought' i], " +
                    "[aria-label*='Thinking' i], " +
                    "[data-testid*='thinking-panel'], " +
                    "[data-testid*='sidebar'], " +
                    "aside"
                ) || root;

                // Extract thinking steps inside right sidebar or root
                const stepEls = sidebarOrRoot.querySelectorAll(
                    "[data-testid*='step'], " +
                    "li, " +
                    "[class*='step'], " +
                    "[class*='timeline'], " +
                    "[role='listitem']"
                );
                if (stepEls.length > 0) {
                    for (let i = 0; i < stepEls.length; i++) {
                        const sEl = stepEls[i];
                        const titleEl = sEl.querySelector("[class*='title'], [class*='header'], strong, h3, h4, [data-testid*='title']") || sEl;
                        const title = clean(titleEl.innerText || titleEl.textContent || `Step ${i + 1}`);
                        let desc = "";
                        const descEl = sEl.querySelector("[class*='desc'], [class*='body'], [class*='content'], p") || sEl;
                        if (descEl && descEl !== titleEl) {
                            desc = clean(descEl.innerText || descEl.textContent || "");
                        }
                        const isLast = i === stepEls.length - 1;
                        const stepStatus = (isMetaGenerating && isLast) ? "running" : "completed";
                        const dedupeKey = title + "::" + desc;
                        if (!seenStepKeys.has(dedupeKey)) {
                            seenStepKeys.add(dedupeKey);
                            thinkingSteps.push({
                                title: title || `Step ${i + 1}`,
                                description: desc,
                                status: stepStatus
                            });
                        }
                    }
                }

                // If no individual step elements found, use thinkingStatus text
                if (thinkingSteps.length === 0 && (statusText || isMetaGenerating)) {
                    const title = statusText || "Thinking Process";
                    const desc = isMetaGenerating ? "Đang suy luận..." : "Hoàn tất suy luận";
                    const dedupeKey = title + "::" + desc;
                    if (!seenStepKeys.has(dedupeKey)) {
                        seenStepKeys.add(dedupeKey);
                        thinkingSteps.push({
                            title: title,
                            description: desc,
                            status: isMetaGenerating ? "running" : "completed"
                        });
                    }
                    thinkingText = title;
                }

                // Also extract Sources from right sidebar / panel
                const sourceLinks = sidebarOrRoot.querySelectorAll(
                    "a[href^='http'], " +
                    "[data-testid*='source'] a[href^='http'], " +
                    "[aria-label*='source' i] a[href^='http'], " +
                    "[aria-label*='Sources' i] a[href^='http']"
                );
                for (const a of sourceLinks) {
                    const href = a.href || a.getAttribute("href");
                    if (href && href.startsWith("http") && !seenUrls.has(href)) {
                        if (
                            !href.includes("meta.ai") &&
                            !href.includes("facebook.com") &&
                            !href.includes("instagram.com") &&
                            !href.includes("login") &&
                            !href.includes("auth")
                        ) {
                            seenUrls.add(href);
                            const title = clean(a.innerText || a.textContent || a.getAttribute("title") || href);
                            citations.push({
                                url: href,
                                title: title || href,
                                snippet: ""
                            });
                        }
                    }
                }
            }
        } catch (e) {}
    }

    // 3. Fallback: query general thinking containers across other providers
    if (!thinkingText && thinkingSteps.length === 0) {
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
            const allBlocks = document.querySelectorAll("details[class*='thought'], details[class*='thinking'], div[data-testid*='thought'], div[class*='thinking-process']");
            for (const el of allBlocks) {
                const txt = (el.innerText || "").trim();
                if (txt && (txt.includes("Thought Process") || txt.includes("Thinking Process") || /^(thinking|thought|suy nghĩ)\b/i.test(txt))) {
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

    // 4.2. Copilot-specific: Extract from sources button, flyout, panel
    try {
        const copilotSourceEls = document.querySelectorAll(
            "[data-testid='sources-button-testid'] ~ * a[href^='http'], " +
            "div[class*='sources'] a[href^='http'], " +
            "div[class*='attribution'] a[href^='http'], " +
            "[data-testid*='source'] a[href^='http'], " +
            "[aria-label*='Sources' i] a[href^='http'], " +
            "[role='dialog'] a[href^='http'], " +
            "div[class*='scc-'] a[href^='http'], " +
            "a[data-testid*='attribution'][href^='http'], " +
            "a[class*='attribution'][href^='http']"
        );
        for (const a of copilotSourceEls) {
            const href = a.href || a.getAttribute("href") || "";
            if (href && href.startsWith("http") && !seenUrls.has(href)) {
                if (!href.includes("login") && !href.includes("auth") && !href.includes("microsoft.com/chat")) {
                    seenUrls.add(href);
                    let title = clean(a.innerText || a.textContent || a.getAttribute("title") || a.getAttribute("aria-label") || "");
                    const card = a.closest("div, li, [class*='card']");
                    let snippet = "";
                    if (card && card !== a) {
                        const snipEl = card.querySelector("[class*='snippet'], [class*='desc'], [class*='summary'], p");
                        if (snipEl) snippet = clean(snipEl.innerText || snipEl.textContent);
                    }
                    citations.push({
                        url: href,
                        title: title || href,
                        snippet: snippet
                    });
                }
            }
        }

        // Copilot: Extract citations from paragraph citation buttons (fai-BebopCitation)
        const bebopButtons = document.querySelectorAll(
            "button[class*='fai-BebopCitation'], [class*='fai-BebopCitation'], [data-grouped-citations]"
        );
        for (const btn of bebopButtons) {
            const rawGrouped = btn.getAttribute("data-grouped-citations");
            const ariaLabel = btn.getAttribute("aria-label") || "";
            let ariaTitle = "";
            if (ariaLabel) {
                let lbl = ariaLabel.trim();
                if (lbl.toLowerCase().startsWith("citation:")) {
                    lbl = lbl.slice(9).trim();
                }
                if (lbl.includes(" — ")) {
                    ariaTitle = lbl.split(" — ")[1].trim();
                } else if (lbl.includes(" - ")) {
                    ariaTitle = lbl.split(" - ")[1].trim();
                } else {
                    ariaTitle = lbl;
                }
            }

            if (rawGrouped) {
                try {
                    const parsed = JSON.parse(rawGrouped);
                    if (Array.isArray(parsed)) {
                        for (const item of parsed) {
                            if (item && item.url && !seenUrls.has(item.url)) {
                                if (!item.url.includes("login") && !item.url.includes("auth") && !item.url.includes("microsoft.com/chat")) {
                                    seenUrls.add(item.url);
                                    citations.push({
                                        url: item.url,
                                        title: item.name || ariaTitle || item.url,
                                        snippet: ""
                                    });
                                }
                            }
                        }
                    }
                } catch (err) {}
            }
        }
    } catch (e) {}

    // 4.3. Gemini-specific: Extract rich citations from attribution containers
    if (provider === "gemini" || !provider) {
        try {
            const geminiAttrContainers = document.querySelectorAll(
                "attribution-container, div.tool-attribution, link-block, sources-list, [data-test-id*='attribution']"
            );
            for (const container of geminiAttrContainers) {
                const link = container.querySelector("a[href^='http']");
                if (link) {
                    const href = link.href || link.getAttribute("href");
                    if (href && !seenUrls.has(href)) {
                        if (!href.includes("login") && !href.includes("auth") && !href.includes("accounts.google")) {
                            seenUrls.add(href);
                            const titleEl = container.querySelector(".tool-attribution-title-text, .title, .link-title, strong") || link;
                            const title = clean(titleEl.innerText || titleEl.textContent || link.getAttribute("title") || "");
                            const descEl = container.querySelector(".tool-attribution-label, .snippet, .description, p");
                            const snippet = descEl ? clean(descEl.innerText || descEl.textContent) : "";
                            citations.push({
                                url: href,
                                title: title || href,
                                snippet: snippet
                            });
                        }
                    }
                }
            }
        } catch (e) {}
    }

    // 4.4. General link selectors for citations across providers
    const linkSelectors = [
        "div[data-message-author-role='assistant'] a[href^='http']",
        "[data-markdown-text-style='assistant-message'] a[href^='http']",
        "[class*='MarkdownRoot'] a[href^='http']",
        "a[data-testid='citation']",
        "a.citation",
        "a[data-citation]",
        "a.qwen-markdown-link",
        "attribution-container a[href^='http']",
        "div.tool-attribution a[href^='http']",
        "link-block a[href^='http']",
        "sources-list a[href^='http']",
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
        "div[class*='status-card'] a[href^='http']",
        "[aria-label='Sources'] a[href^='http']",
        "[aria-label*='Sources' i] a[href^='http']",
        "div.chat-assistant a[href^='http']",
        ".chat-assistant a[href^='http']",
        "div[data-testid='chat-main-conversation'] div[data-message-role='assistant'] a[href^='http']",
        "div[data-testid='chat-main-conversation'] a[href^='http']"
    ];

    for (const sel of linkSelectors) {
        try {
            const links = document.querySelectorAll(sel);
            for (const a of links) {
                const href = a.href || a.getAttribute("href");
                if (href && href.startsWith("http") && !seenUrls.has(href)) {
                    if (!href.includes("login") && !href.includes("auth") && !href.includes("accounts.google") && !href.includes("chatgpt.com") && !href.includes("openai.com") && !href.includes("minimax.io") && !href.includes("meta.ai") && !href.includes("facebook.com") && !href.includes("instagram.com")) {
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