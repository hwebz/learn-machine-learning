"use client";

import React, { useEffect, useRef, useMemo } from "react";
import { marked } from "marked";
import hljs from "highlight.js";

interface MarkdownContentProps {
  content: string;
}

function trimCodeBlock(codeText: string): string {
  if (!codeText) return "";
  const rawLines = codeText.split("\n").map((l) => l.trimEnd());

  // Trim leading & trailing empty lines
  while (rawLines.length > 0 && rawLines[0].trim() === "") {
    rawLines.shift();
  }
  while (rawLines.length > 0 && rawLines[rawLines.length - 1].trim() === "") {
    rawLines.pop();
  }
  if (rawLines.length === 0) return "";

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

  while (cleaned.length > 0 && cleaned[0].trim() === "") cleaned.shift();
  while (cleaned.length > 0 && cleaned[cleaned.length - 1].trim() === "") cleaned.pop();

  return cleaned.join("\n");
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

      let highlightedCode = codeText;
      let validLang = language;

      if (language && hljs.getLanguage(language)) {
        try {
          highlightedCode = hljs.highlight(codeText, { language }).value;
        } catch {
          highlightedCode = hljs.highlightAuto(codeText).value;
        }
      } else if (codeText) {
        try {
          const autoResult = hljs.highlightAuto(codeText);
          highlightedCode = autoResult.value;
          validLang = autoResult.language || "text";
        } catch {
          highlightedCode = codeText;
        }
      }

      const displayLang = (validLang || "code").toUpperCase();

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
    renderer.table = function ({ header, rows }) {
      return `
        <div class="markdown-table-wrapper">
          <table class="markdown-table">
            <thead>${header}</thead>
            <tbody>${rows}</tbody>
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

    // 3. Convert virtualized scriptor code blocks (Copilot) and Monaco / Qwen code blocks
    // to markdown fenced code blocks so marked and highlight.js highlight them
    const hasScriptor =
      sanitizedContent.includes("scriptor-component-code-block") ||
      sanitizedContent.includes("scriptor-codeblock-virtualized");
    const hasMonaco =
      sanitizedContent.includes("qwen-markdown-code") ||
      sanitizedContent.includes("monaco-editor");

    if (hasScriptor || hasMonaco) {
      if (typeof window !== "undefined" && typeof DOMParser !== "undefined") {
        try {
          const parser = new DOMParser();
          const doc = parser.parseFromString(sanitizedContent, "text/html");

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

    let rawHtml = "";
    try {
      rawHtml = marked.parse(sanitizedContent) as string;
    } catch (err) {
      console.warn("Markdown parse error, falling back to raw text:", err);
      rawHtml = `<p>${content}</p>`;
    }

    // Enhance citations like [1], [2], [S1], [S2]
    const withCitations = rawHtml.replace(
      /\[(\d+|S\d+)\]/g,
      '<span class="citation-sup">$1</span>'
    );

    return withCitations;
  }, [content]);

  // Click handler delegation for copy code buttons
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleContainerClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const copyBtn = target.closest(".code-copy-btn") as HTMLButtonElement | null;
      if (!copyBtn) return;

      const codeContainer = copyBtn.closest(".code-block-container");
      const codeElement = codeContainer?.querySelector("code");
      if (!codeElement) return;

      const codeText = codeElement.textContent || "";
      navigator.clipboard.writeText(codeText).then(() => {
        const copyTextSpan = copyBtn.querySelector(".copy-text");
        const copyIconSpan = copyBtn.querySelector(".copy-icon");

        if (copyTextSpan) copyTextSpan.textContent = "Copied!";
        if (copyIconSpan) copyIconSpan.textContent = "✓";
        copyBtn.classList.add("copied");

        setTimeout(() => {
          if (copyTextSpan) copyTextSpan.textContent = "Copy code";
          if (copyIconSpan) copyIconSpan.textContent = "📋";
          copyBtn.classList.remove("copied");
        }, 2000);
      });
    };

    container.addEventListener("click", handleContainerClick);
    return () => {
      container.removeEventListener("click", handleContainerClick);
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
