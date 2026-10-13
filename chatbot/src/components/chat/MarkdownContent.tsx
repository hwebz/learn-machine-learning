"use client";

import React, { useEffect, useRef, useMemo } from "react";
import { marked } from "marked";
import hljs from "highlight.js";
import katex from "katex";

interface MarkdownContentProps {
  content: string;
}

export function trimCodeBlock(codeText: string): string {
  if (!codeText) return "";
  let rawLines = codeText.split("\n").map((l) => l.trimEnd());

  // Trim leading empty lines or stray backtick markers
  while (
    rawLines.length > 0 &&
    (rawLines[0].trim() === "" || /^`{1,3}$/.test(rawLines[0].trim()))
  ) {
    rawLines.shift();
  }
  // Trim trailing empty lines or stray backtick markers (e.g. "``" or "```")
  while (
    rawLines.length > 0 &&
    (rawLines[rawLines.length - 1].trim() === "" ||
      /^`{1,3}$/.test(rawLines[rawLines.length - 1].trim()))
  ) {
    rawLines.pop();
  }
  if (rawLines.length === 0) return "";

  // If the last line ends with stray trailing backticks like "``"
  if (rawLines.length > 0) {
    const last = rawLines[rawLines.length - 1].trimEnd();
    if (last.endsWith("``") && !last.endsWith("```")) {
      rawLines[rawLines.length - 1] = last.slice(0, -2).trimEnd();
    }
  }

  // Check for alternating empty lines (double-spaced code artifact from HTML/div conversions)
  const nonEmptyIndices: number[] = [];
  rawLines.forEach((l, idx) => {
    if (l.trim() !== "") nonEmptyIndices.push(idx);
  });

  let lines = rawLines;
  if (nonEmptyIndices.length >= 2) {
    let allGapsAtLeastTwo = true;
    for (let i = 0; i < nonEmptyIndices.length - 1; i++) {
      if (nonEmptyIndices[i + 1] - nonEmptyIndices[i] < 2) {
        allGapsAtLeastTwo = false;
        break;
      }
    }
    if (allGapsAtLeastTwo) {
      lines = nonEmptyIndices.map((idx) => rawLines[idx]);
    }
  }

  // Collapse consecutive blank lines to at most 1 blank line
  const cleaned: string[] = [];
  let blankCount = 0;
  for (const l of lines) {
    if (l.trim() === "") {
      blankCount++;
      if (blankCount <= 1) {
        cleaned.push("");
      }
    } else {
      blankCount = 0;
      cleaned.push(l);
    }
  }

  while (
    cleaned.length > 0 &&
    (cleaned[0].trim() === "" || /^`{1,3}$/.test(cleaned[0].trim()))
  ) {
    cleaned.shift();
  }
  while (
    cleaned.length > 0 &&
    (cleaned[cleaned.length - 1].trim() === "" ||
      /^`{1,3}$/.test(cleaned[cleaned.length - 1].trim()))
  ) {
    cleaned.pop();
  }

  if (cleaned.length > 0) {
    const last = cleaned[cleaned.length - 1].trimEnd();
    if (last.endsWith("``") && !last.endsWith("```")) {
      cleaned[cleaned.length - 1] = last.slice(0, -2).trimEnd();
    }
  }

  return cleaned.join("\n");
}

export function cleanMarkdownCodeBlocks(text: string): string {
  if (!text) return "";
  return text.replace(
    /(```[^\n]*\n)([\s\S]*?)(```)/g,
    (_, openFence, code, closeFence) => {
      const trimmed = trimCodeBlock(code);
      return `${openFence}${trimmed}\n${closeFence}`;
    }
  );
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Configure marked renderer
  const htmlContent = useMemo(() => {
    const renderer = new marked.Renderer();

    // Custom code block renderer with language header & copy button
    renderer.code = function ({ text, lang }) {
      let codeText = text || "";
      let language = (lang || "").trim().toLowerCase();

      // Clean up leaked language header & gutter line numbers (e.g. from Monaco/Qwen or legacy conversions)
      const lines = codeText.split("\n");
      let idx = 0;
      let detectedLang = "";

      const firstLine = lines[0]?.trim() || "";
      if (lines.length > 2 && /^[a-zA-Z0-9_#+-]+$/.test(firstLine)) {
        const candidateLang = firstLine.toLowerCase();
        let lookAhead = 1;
        while (lookAhead < lines.length && lines[lookAhead].trim() === "") {
          lookAhead++;
        }
        if (lookAhead < lines.length && lines[lookAhead].trim() === "1") {
          detectedLang = candidateLang;
          idx = lookAhead;
        }
      }

      let expectedNum = 1;
      let hasLineNumbers = false;
      let scanIdx = idx;
      while (scanIdx < lines.length) {
        const trimmed = lines[scanIdx].trim();
        if (trimmed === "") {
          scanIdx++;
          continue;
        }
        if (trimmed === String(expectedNum)) {
          hasLineNumbers = true;
          expectedNum++;
          scanIdx++;
        } else {
          break;
        }
      }

      if (hasLineNumbers && expectedNum >= 2 && scanIdx < lines.length) {
        if (!language && detectedLang) {
          language = detectedLang;
        }
        while (scanIdx < lines.length && lines[scanIdx].trim() === "") {
          scanIdx++;
        }
        const remainingLines = lines.slice(scanIdx);
        codeText = remainingLines.join("\n");
      }

      // Always trim unnecessary lines (leading/trailing blanks, excessive blank lines, alternating double-spaced lines)
      codeText = trimCodeBlock(codeText);

      // If no specific language was given (or given as plain text variants), treat as Plain Text
      if (
        !language ||
        ["plaintext", "text", "plain", "none"].includes(language)
      ) {
        language = "";
      }

      if (language === "mermaid") {
        return `
          <div class="code-block-container mermaid-block-container">
            <div class="code-block-header">
              <span class="code-block-lang">MERMAID</span>
              <button class="code-copy-btn" type="button" aria-label="Copy Mermaid code to clipboard">
                <span class="copy-icon">📋</span>
                <span class="copy-text">Copy code</span>
              </button>
            </div>
            <div class="mermaid-diagram-body" data-mermaid-code="${encodeURIComponent(codeText)}">
              <div class="mermaid-loading">Rendering diagram...</div>
            </div>
            <code class="mermaid-raw-code" style="display: none;">${codeText}</code>
          </div>
        `;
      }

      let highlightedCode = codeText;
      let validLang = "plaintext";
      let displayLang = "Plain Text";

      if (language) {
        validLang = language;
        displayLang = language.toUpperCase();
        if (hljs.getLanguage(language)) {
          try {
            highlightedCode = hljs.highlight(codeText, { language }).value;
          } catch {
            highlightedCode = hljs.highlight(codeText, { language: "plaintext" }).value;
          }
        } else {
          highlightedCode = hljs.highlight(codeText, { language: "plaintext" }).value;
        }
      } else {
        highlightedCode = hljs.highlight(codeText, { language: "plaintext" }).value;
      }

      // Generate line numbers gutter
      const lineCount = codeText.split("\n").length;
      const gutterHtml = Array.from(
        { length: lineCount },
        (_, i) => `<span>${i + 1}</span>`
      ).join("");

      return `
        <div class="code-block-container">
          <div class="code-block-header">
            <span class="code-block-lang">${displayLang}</span>
            <button class="code-copy-btn" type="button" aria-label="Copy code to clipboard">
              <span class="copy-icon">📋</span>
              <span class="copy-text">Copy code</span>
            </button>
          </div>
          <div class="code-block-body">
            <div class="code-gutter" aria-hidden="true">${gutterHtml}</div>
            <pre><code class="hljs language-${validLang}">${highlightedCode}</code></pre>
          </div>
        </div>
      `;
    };

    // Custom task list item and general list item renderer
    renderer.listitem = function (token: any) {
      if (token.task) {
        const checked = token.checked ? ' checked="checked"' : "";
        const body =
          token.tokens && this.parser
            ? this.parser.parse(token.tokens)
            : token.text || "";
        return `
          <li class="task-list-item">
            <label class="task-list-label">
              <input type="checkbox" class="task-list-checkbox"${checked} />
              <span class="task-list-box" aria-hidden="true">
                <svg class="task-list-check-icon" viewBox="0 0 14 14" fill="none">
                  <path d="M3 7.5L5.5 10L11 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="task-list-text">${body}</span>
            </label>
          </li>
        `;
      }
      const body =
        token.tokens && this.parser
          ? this.parser.parse(token.tokens)
          : token.text || "";
      return `<li>${body}</li>`;
    };

    // Custom inline code renderer
    renderer.codespan = function ({ text }) {
      return `<code class="inline-code">${text}</code>`;
    };

    // Custom link renderer (always open in new tab securely)
    renderer.link = function ({ href, title, text }) {
      const titleAttr = title ? ` title="${title}"` : "";
      return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="markdown-link"${titleAttr}>${text}</a>`;
    };

    // Custom table renderer with responsive wrapper
    renderer.table = function (token: any) {
      let headerCells = "";
      for (const cell of token.header || []) {
        headerCells += this.tablecell(cell);
      }
      const headerRow = this.tablerow({ text: headerCells });

      let bodyRows = "";
      for (const row of token.rows || []) {
        let rowCells = "";
        for (const cell of row) {
          rowCells += this.tablecell(cell);
        }
        bodyRows += this.tablerow({ text: rowCells });
      }
      const tbody = bodyRows ? `<tbody>\n${bodyRows}</tbody>` : "";

      return `
        <div class="markdown-table-wrapper">
          <table class="markdown-table">
            <thead>
              ${headerRow}
            </thead>
            ${tbody}
          </table>
        </div>
      `;
    };

    // Custom blockquote
    renderer.blockquote = function (token: any) {
      const body =
        token && token.tokens && this.parser
          ? this.parser.parse(token.tokens)
          : typeof token === "string"
            ? token
            : token?.text || "";
      return `<blockquote class="markdown-blockquote">${body}</blockquote>`;
    };


    marked.setOptions({
      renderer,
      gfm: true,
      breaks: true,
    });

    // 1. Strip ID prefix in source markdown lists like:
    // "- [4705a475-e12d-434c-8d0b-ff25bb9ed5c1:S1] [Title](url)" -> "- [Title](url)"
    let sanitizedContent = (content || "").replace(
      /^(\s*[-*]\s*)\[[a-zA-Z0-9_\-:]+\]\s*(\[[^\]]+\]\([^\)]+\))/gm,
      "$1$2"
    );

    // 2. Strip stray empty list markers like lone "1." or "-" with no content
    sanitizedContent = sanitizedContent
      .split("\n")
      .filter((line) => !/^\s*(?:>\s*)*(?:[-*+]|\d+\.)\s*$/.test(line))
      .join("\n");

    // 2b. Transform Section 18 "Markdown test results: 0/27 passed" into interactive checklist widget
    sanitizedContent = sanitizedContent.replace(
      /(?:##+\s+Markdown test results\s*\n+)?0\/27 passed/gi,
      `
<div class="checklist-widget-card" data-checklist-group="compatibility">
  <div class="checklist-widget-header">
    <div class="checklist-widget-title">
      <span class="checklist-icon">📋</span>
      <span>Markdown test results</span>
    </div>
    <div class="checklist-counter-badge">
      <span class="checklist-counter-text">0/27 passed</span>
    </div>
  </div>
  <div class="checklist-progress-track">
    <div class="checklist-progress-fill" style="width: 0%"></div>
  </div>
</div>
`
    );

    // 3. Convert virtualized scriptor code blocks (Copilot), Monaco / Qwen code blocks,
    // and raw HTML math blocks (Gemini math-block, KaTeX katex-display/katex)
    const hasScriptor =
      sanitizedContent.includes("scriptor-component-code-block") ||
      sanitizedContent.includes("scriptor-codeblock-virtualized");
    const hasMonaco =
      sanitizedContent.includes("qwen-markdown-code") ||
      sanitizedContent.includes("monaco-editor");
    const hasMath =
      sanitizedContent.includes("math-block") ||
      sanitizedContent.includes("math-inline") ||
      sanitizedContent.includes("katex-display") ||
      sanitizedContent.includes("data-math") ||
      sanitizedContent.includes('class="katex"') ||
      sanitizedContent.includes("class='katex'");

    if (hasScriptor || hasMonaco || hasMath) {
      if (typeof window !== "undefined" && typeof DOMParser !== "undefined") {
        try {
          const parser = new DOMParser();
          const doc = parser.parseFromString(sanitizedContent, "text/html");

          // Handle Gemini math-block & KaTeX display/inline elements in raw HTML
          if (hasMath) {
            // 1. Display math blocks (.math-block, [data-math], .katex-display)
            const displayEls = doc.querySelectorAll(
              ".math-block, [class*='math-block'], .katex-display, [class*='katex-display']"
            );
            displayEls.forEach((el) => {
              const formula =
                el.getAttribute("data-math") ||
                el.getAttribute("data-latex") ||
                el.getAttribute("data-tex") ||
                el.querySelector("annotation")?.textContent ||
                el.querySelector("script[type*='math']")?.textContent ||
                "";
              if (formula.trim()) {
                const mdBlock = doc.createTextNode(`\n\n$$\n${formula.trim()}\n$$\n\n`);
                el.parentNode?.replaceChild(mdBlock, el);
              }
            });

            // 2. Inline math elements (.math-inline, .katex, [data-math])
            const inlineEls = doc.querySelectorAll(
              ".math-inline, [class*='math-inline'], .katex, [data-math], [data-latex]"
            );
            inlineEls.forEach((el) => {
              if (!el.parentNode) return;
              if (el.closest(".katex-html") || el.closest(".katex-mathml")) return;
              const formula =
                el.getAttribute("data-math") ||
                el.getAttribute("data-latex") ||
                el.getAttribute("data-tex") ||
                el.querySelector("annotation")?.textContent ||
                "";
              if (formula.trim()) {
                const mdInline = doc.createTextNode(` $${formula.trim()}$ `);
                el.parentNode?.replaceChild(mdInline, el);
              }
            });
          }

          // Handle Copilot scriptor code blocks
          if (hasScriptor) {
            const scriptorEls = doc.querySelectorAll(
              ".scriptor-component-code-block, .scriptor-codeblock-virtualized, [class*='scriptor-component-code-block'], [class*='scriptor-codeblock-virtualized']"
            );
            scriptorEls.forEach((el) => {
              let lang = "";
              const langEl = el.querySelector(
                "[data-testid='one-copilot-code-identity'] span, [class*='code-identity'] span"
              );
              if (langEl) {
                lang = (langEl.textContent || "").trim();
              }
              if (lang.toLowerCase() === "plain text") lang = "";
              else lang = lang.toLowerCase().replace(/\s+/g, "");

              const lines: string[] = [];
              const lineEls = el.querySelectorAll("[data-line-index]");
              if (lineEls.length > 0) {
                lineEls.forEach((l) =>
                  lines.push((l.textContent || "").replace(/\u00a0/g, " "))
                );
              } else {
                const editorEl = el.querySelector(
                  "[role='textbox'], [aria-label='Code editor']"
                );
                if (editorEl) {
                  lines.push((editorEl.textContent || "").replace(/\u00a0/g, " "));
                }
              }
              const codeText = trimCodeBlock(lines.join("\n"));
              const mdCodeBlock = doc.createTextNode(
                `\n\n\`\`\`${lang}\n${codeText}\n\`\`\`\n\n`
              );
              el.parentNode?.replaceChild(mdCodeBlock, el);
            });
          }

          // Handle Monaco / Qwen code blocks
          if (hasMonaco) {
            const monacoEls = doc.querySelectorAll(
              ".qwen-markdown-code, .monaco-editor, [class*='qwen-markdown-code']"
            );
            monacoEls.forEach((el) => {
              let lang =
                el.getAttribute("data-mode-id") ||
                el.getAttribute("data-language") ||
                el.getAttribute("data-lang") ||
                "";
              if (!lang) {
                const headerEl = el.querySelector(
                  ".qwen-markdown-code-header, [class*='code-header']"
                );
                if (headerEl) {
                  const firstChild = headerEl.firstElementChild;
                  if (
                    firstChild &&
                    !firstChild.classList.contains("qwen-markdown-code-header-actions")
                  ) {
                    lang = firstChild.textContent?.trim() || "";
                  } else {
                    lang = (headerEl.textContent || "").split(/\s+/)[0] || "";
                  }
                }
              }
              if (lang.toLowerCase() === "plain text") lang = "";
              else lang = lang.toLowerCase().replace(/\s+/g, "");

              const lines: string[] = [];
              const lineEls = el.querySelectorAll(".view-line");
              if (lineEls.length > 0) {
                lineEls.forEach((l) => {
                  lines.push((l.textContent || "").replace(/\u00a0/g, " "));
                });
              } else {
                const clone = el.cloneNode(true) as HTMLElement;
                clone
                  .querySelectorAll(
                    ".line-numbers, .margin, .glyph-margin, [class*='header']"
                  )
                  .forEach((n) => n.remove());
                lines.push((clone.textContent || "").replace(/\u00a0/g, " "));
              }
              const codeText = trimCodeBlock(lines.join("\n"));
              const mdCodeBlock = doc.createTextNode(
                `\n\n\`\`\`${lang}\n${codeText}\n\`\`\`\n\n`
              );
              el.parentNode?.replaceChild(mdCodeBlock, el);
            });
          }

          sanitizedContent = doc.body.innerHTML;
        } catch (e) {
          console.warn("Failed to preprocess virtualized code blocks via DOMParser:", e);
        }
      } else {
        // Universal fallback for SSR
        if (hasMath) {
          sanitizedContent = sanitizedContent
            .replace(
              /<(?:div|span)[^>]*class="[^"]*(?:math-block|katex-display)[^"]*"[^>]*data-math="([^"]+)"[\s\S]*?<\/(?:div|span)>/g,
              "\n\n$$\n$1\n$$\n\n"
            )
            .replace(
              /<(?:div|span)[^>]*data-math="([^"]+)"[\s\S]*?<\/(?:div|span)>/g,
              "\n\n$$\n$1\n$$\n\n"
            )
            .replace(
              /<(?:div|span)[^>]*class="[^"]*katex-display[^"]*"[\s\S]*?<annotation[^>]*>([\s\S]*?)<\/annotation>[\s\S]*?<\/(?:div|span)>/g,
              "\n\n$$\n$1\n$$\n\n"
            )
            .replace(
              /<span[^>]*class="[^"]*(?:math-inline|katex)[^"]*"[\s\S]*?<annotation[^>]*>([\s\S]*?)<\/annotation>[\s\S]*?<\/span>/g,
              " $$1 "
            );
        }
        if (hasScriptor) {
          sanitizedContent = sanitizedContent.replace(
            /<[a-zA-Z0-9]+[^>]*class="[^"]*(?:scriptor-component-code-block|scriptor-codeblock-virtualized)[^"]*"[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/g,
            (block) => {
              const langMatch = block.match(
                /data-testid="one-copilot-code-identity"[^>]*>[\s\S]*?<span>(.*?)<\/span>/
              );
              let lang = langMatch ? langMatch[1].trim() : "";
              if (lang.toLowerCase() === "plain text") lang = "";
              else lang = lang.toLowerCase().replace(/\s+/g, "");

              const lineMatches = [
                ...block.matchAll(
                  /<div[^>]*data-line-index="\d+"[^>]*>([\s\S]*?)<\/div>/g
                ),
              ];
              const lines = lineMatches.map((m) =>
                m[1]
                  .replace(/<[^>]+>/g, "")
                  .replace(/&nbsp;/g, " ")
                  .replace(/\u00a0/g, " ")
              );
              const code = trimCodeBlock(lines.join("\n"));
              return `\n\n\`\`\`${lang}\n${code}\n\`\`\`\n\n`;
            }
          );
        }
        if (hasMonaco) {
          sanitizedContent = sanitizedContent.replace(
            /<pre[^>]*class="[^"]*qwen-markdown-code[^"]*"[\s\S]*?<\/pre>/g,
            (block) => {
              const headerMatch = block.match(
                /<div class="qwen-markdown-code-header"[^>]*><div>(.*?)<\/div>/
              );
              let lang = headerMatch ? headerMatch[1].trim() : "";
              if (lang.toLowerCase() === "plain text") lang = "";
              else lang = lang.toLowerCase().replace(/\s+/g, "");

              const lineMatches = [
                ...block.matchAll(
                  /<div[^>]*class="view-line"[^>]*>([\s\S]*?)<\/div>/g
                ),
              ];
              const lines = lineMatches.map((m) =>
                m[1]
                  .replace(/<[^>]+>/g, "")
                  .replace(/&nbsp;/g, " ")
                  .replace(/\u00a0/g, " ")
              );
              const code = trimCodeBlock(lines.join("\n"));
              return `\n\n\`\`\`${lang}\n${code}\n\`\`\`\n\n`;
            }
          );
        }
      }
    }


    // Ensure all code block fences have clean inner code without leaked trailing ``
    sanitizedContent = cleanMarkdownCodeBlocks(sanitizedContent);

    // Extract and protect LaTeX math expressions before marked.parse to prevent markdown escaping
    const mathPlaceholders = new Map<string, string>();
    let placeholderCounter = 0;

    const storeMath = (tex: string, displayMode: boolean) => {
      const key = `@@KATEX_MATH_${placeholderCounter++}@@`;
      try {
        const cleanTex = tex.trim();
        const rendered = katex.renderToString(cleanTex, {
          displayMode,
          throwOnError: false,
        });

        const wrapper = displayMode
          ? `<div class="katex-display-block">${rendered}</div>`
          : `<span class="katex-inline-block">${rendered}</span>`;
        mathPlaceholders.set(key, wrapper);
      } catch (err) {
        mathPlaceholders.set(key, `<span class="katex-error">${tex}</span>`);
      }
      return key;
    };

    let processedContent = sanitizedContent;

    // 1. Temporarily protect code blocks and inline code so we don't alter math inside code
    const codePlaceholders = new Map<string, string>();
    let codeCounter = 0;
    processedContent = processedContent.replace(
      /(```[\s\S]*?```|`[^`\n]+`)/g,
      (match) => {
        const key = `@@CODE_CHUNK_${codeCounter++}@@`;
        codePlaceholders.set(key, match);
        return key;
      }
    );

    // 2. Block math: $$ ... $$
    processedContent = processedContent.replace(
      /(?<!\\)\$\$([\s\S]+?)\$\$/g,
      (_, math) => `\n\n${storeMath(math, true)}\n\n`
    );

    // 2b. Block math: \begin{equation|align|gather|matrix|bmatrix|pmatrix|cases|aligned} ... \end{...}
    processedContent = processedContent.replace(
      /(?<!\\)\\begin\{(equation\*?|align\*?|gather\*?|matrix|bmatrix|pmatrix|cases|aligned)\}([\s\S]+?)\\end\{\1\}/g,
      (match) => `\n\n${storeMath(match, true)}\n\n`
    );

    // 3. Inline math: \( ... \)
    processedContent = processedContent.replace(
      /(?<!\\)\\\(([\s\S]+?)\\\)/g,
      (_, math) => storeMath(math, false)
    );

    // 4. Inline math: $ ... $ (excluding currency like $100 or $50 to $100)
    processedContent = processedContent.replace(
      /(?<![\\\$])\$([^\s\$](?:[^\$]*?[^\s\$])?)\$(?!\d)/g,
      (match, math) => {
        if (/^\d+(?:[.,]\d+)?$/.test(math.trim())) {
          return match;
        }
        return storeMath(math, false);
      }
    );

    // 5. Restore code blocks
    for (const [key, code] of codePlaceholders.entries()) {
      processedContent = processedContent.replace(key, () => code);
    }

    let rawHtml = "";
    try {
      rawHtml = marked.parse(processedContent) as string;
    } catch (err) {
      console.warn("Markdown parse error, falling back to raw text:", err);
      rawHtml = `<p>${content}</p>`;
    }

    // Restore rendered KaTeX math placeholders
    for (const [key, mathHtml] of mathPlaceholders.entries()) {
      rawHtml = rawHtml.replace(key, () => mathHtml);
    }

    // Enhance citations like [1], [2], [S1], [S2]
    const withCitations = rawHtml.replace(
      /\[(\d+|S\d+)\]/g,
      '<span class="citation-sup">$1</span>'
    );

    return withCitations;
  }, [content]);

  // Click handler delegation for copy code buttons, mermaid diagrams, and interactive checklists
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Dynamic Mermaid rendering
    import("mermaid").then((m) => {
      const mermaidInstance = m.default || m;
      mermaidInstance.initialize({
        startOnLoad: false,
        theme: "default",
        securityLevel: "loose",
        fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
      });

      const diagramBodies = container.querySelectorAll<HTMLElement>(
        ".mermaid-diagram-body:not([data-rendered='true'])"
      );
      diagramBodies.forEach((bodyEl, idx) => {
        const rawCode = decodeURIComponent(bodyEl.getAttribute("data-mermaid-code") || "");
        if (!rawCode) return;
        const svgId = `mermaid-svg-${Date.now()}-${idx}`;
        mermaidInstance
          .render(svgId, rawCode)
          .then(({ svg }: { svg: string }) => {
            bodyEl.innerHTML = svg;
            bodyEl.setAttribute("data-rendered", "true");
          })
          .catch((err: any) => {
            console.warn("Failed to render Mermaid diagram:", err);
            bodyEl.innerHTML = `<div class="mermaid-error"><p>Could not render diagram</p><pre><code>${rawCode}</code></pre></div>`;
            bodyEl.setAttribute("data-rendered", "true");
          });
      });
    });

    // 2. Interactive checklist checkboxes handler
    const handleCheckboxChange = (e: Event) => {
      const target = e.target as HTMLInputElement;
      if (!target.classList.contains("task-list-checkbox")) return;

      const widgetCard = container.querySelector(".checklist-widget-card");
      if (widgetCard) {
        const allBoxes = container.querySelectorAll(".task-list-checkbox");
        const checkedBoxes = container.querySelectorAll(".task-list-checkbox:checked");
        const total = allBoxes.length;
        const count = checkedBoxes.length;

        const counterText = widgetCard.querySelector(".checklist-counter-text");
        const progressFill = widgetCard.querySelector(".checklist-progress-fill") as HTMLElement | null;

        if (counterText) {
          counterText.textContent = `${count}/${total} passed`;
        }
        if (progressFill) {
          const pct = total > 0 ? (count / total) * 100 : 0;
          progressFill.style.width = `${pct}%`;
        }
        if (count === total && total > 0) {
          widgetCard.classList.add("all-passed");
        } else {
          widgetCard.classList.remove("all-passed");
        }
      }
    };

    // 3. Copy button handler delegation & Radio groups
    const handleContainerClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;

      // Radio group interaction delegation
      const radioBtn = target.closest<HTMLButtonElement>("button[role='radio'], .RadioItem-eqbQKh");
      const radioLabel = target.closest<HTMLLabelElement>(".RadioLabel-aEyICO, [data-d-component='radio']");
      let selectedRadio = radioBtn;
      if (!selectedRadio && radioLabel) {
        selectedRadio = radioLabel.querySelector<HTMLButtonElement>("button[role='radio'], .RadioItem-eqbQKh");
      }

      if (selectedRadio) {
        const radioGroup = selectedRadio.closest("[role='radiogroup'], [data-d-component='radio-group']");
        if (radioGroup) {
          const allRadios = radioGroup.querySelectorAll<HTMLButtonElement>("button[role='radio'], .RadioItem-eqbQKh");
          allRadios.forEach((r) => {
            r.setAttribute("aria-checked", "false");
            r.setAttribute("data-state", "unchecked");
            const indicator = r.querySelector(".RadioIndicator-QSL7RM");
            if (indicator) indicator.remove();
          });
          selectedRadio.setAttribute("aria-checked", "true");
          selectedRadio.setAttribute("data-state", "checked");
          if (!selectedRadio.querySelector(".RadioIndicator-QSL7RM")) {
            const ind = document.createElement("span");
            ind.className = "RadioIndicator-QSL7RM";
            ind.setAttribute("data-state", "checked");
            selectedRadio.appendChild(ind);
          }
        }
        return;
      }

      const copyBtn = target.closest(".code-copy-btn") as HTMLButtonElement | null;
      if (!copyBtn) return;

      const codeContainer = copyBtn.closest(".code-block-container");
      const isLatex = Boolean(copyBtn.closest(".latex-block-container"));
      const isMermaid = Boolean(copyBtn.closest(".mermaid-block-container"));
      const originalText = isLatex ? "Copy LaTeX" : isMermaid ? "Copy code" : "Copy code";
      const codeElement =
        codeContainer?.querySelector("code.latex-raw-code") ||
        codeContainer?.querySelector("code.mermaid-raw-code") ||
        codeContainer?.querySelector("code");
      if (!codeElement) return;

      const codeText = codeElement.textContent || "";
      navigator.clipboard.writeText(codeText).then(() => {
        const copyTextSpan = copyBtn.querySelector(".copy-text");
        const copyIconSpan = copyBtn.querySelector(".copy-icon");

        if (copyTextSpan) copyTextSpan.textContent = "Copied!";
        if (copyIconSpan) copyIconSpan.textContent = "✓";
        copyBtn.classList.add("copied");

        setTimeout(() => {
          if (copyTextSpan) copyTextSpan.textContent = originalText;
          if (copyIconSpan) copyIconSpan.textContent = "📋";
          copyBtn.classList.remove("copied");
        }, 2000);
      });
    };

    // 4. Interactive Slider pointer/drag delegation
    const handleSliderPointerDown = (e: PointerEvent) => {
      const target = e.target as HTMLElement;
      const sliderContainer = target.closest<HTMLElement>(
        ".SliderContainer-csaRc8, .Slider-veC4c6, [data-d-component='slider']"
      );
      if (!sliderContainer) return;

      const track = sliderContainer.querySelector<HTMLElement>(".Track-J8JrvV") || sliderContainer;
      const range = sliderContainer.querySelector<HTMLElement>(".Range-OINGKj");
      const thumb = sliderContainer.querySelector<HTMLElement>(".Thumb-ZDGlbm, [role='slider']");
      const thumbWrapper = thumb?.parentElement;
      if (!thumb || !thumbWrapper) return;

      const updateSliderValue = (clientX: number) => {
        const rect = track.getBoundingClientRect();
        if (rect.width <= 0) return;
        const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
        const min = parseFloat(thumb.getAttribute("aria-valuemin") || "0");
        const max = parseFloat(thumb.getAttribute("aria-valuemax") || "100");
        const val = Math.round(min + ratio * (max - min));

        thumb.setAttribute("aria-valuenow", String(val));
        thumbWrapper.style.left = `calc(${ratio * 100}% - 3px)`;
        if (range) {
          range.style.right = `${(1 - ratio) * 100}%`;
        }

        const parentBox = sliderContainer.closest(
          "[data-d-component='box'], [data-d-component='grid-item'], div[class*='Box-']"
        );
        if (parentBox) {
          const valueTitle = parentBox.querySelector<HTMLElement>(
            "[data-d-component='title'] span, .Title-HRvkwB span, [data-d-component='title']"
          );
          if (valueTitle) {
            valueTitle.textContent = `${val}%`;
          }
        }
      };

      updateSliderValue(e.clientX);

      const onPointerMove = (moveEvt: PointerEvent) => {
        updateSliderValue(moveEvt.clientX);
      };
      const onPointerUp = () => {
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
      };
      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
    };

    container.addEventListener("change", handleCheckboxChange);
    container.addEventListener("click", handleContainerClick);
    container.addEventListener("pointerdown", handleSliderPointerDown);
    return () => {
      container.removeEventListener("change", handleCheckboxChange);
      container.removeEventListener("click", handleContainerClick);
      container.removeEventListener("pointerdown", handleSliderPointerDown);
    };
  }, [htmlContent]);

  return (
    <div
      ref={containerRef}
      className="markdown-rendered-content"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}
