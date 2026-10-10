"use client";

import React, { useEffect, useRef, useMemo } from "react";
import { marked } from "marked";
import hljs from "highlight.js";

interface MarkdownContentProps {
  content: string;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Configure marked renderer
  const htmlContent = useMemo(() => {
    const renderer = new marked.Renderer();

    // Custom code block renderer with language header & copy button
    renderer.code = function ({ text, lang }) {
      const language = (lang || "").trim().toLowerCase();
      let highlightedCode = text;
      let validLang = language;

      if (language && hljs.getLanguage(language)) {
        try {
          highlightedCode = hljs.highlight(text, { language }).value;
        } catch {
          highlightedCode = hljs.highlightAuto(text).value;
        }
      } else if (text) {
        try {
          const autoResult = hljs.highlightAuto(text);
          highlightedCode = autoResult.value;
          validLang = autoResult.language || "text";
        } catch {
          highlightedCode = text;
        }
      }

      const displayLang = (validLang || "code").toUpperCase();

      return `
        <div class="code-block-container">
          <div class="code-block-header">
            <span class="code-block-lang">${displayLang}</span>
            <button class="code-copy-btn" type="button" aria-label="Copy code to clipboard">
              <span class="copy-icon">📋</span>
              <span class="copy-text">Copy code</span>
            </button>
          </div>
          <pre><code class="hljs language-${validLang}">${highlightedCode}</code></pre>
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
    renderer.blockquote = function ({ text }) {
      return `<blockquote class="markdown-blockquote">${text}</blockquote>`;
    };

    marked.setOptions({
      renderer,
      gfm: true,
      breaks: true,
    });

    let rawHtml = "";
    try {
      rawHtml = marked.parse(content) as string;
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
