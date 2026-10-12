from __future__ import annotations

from html.parser import HTMLParser
from typing import Any, Iterable

from app.adapters.base import Source

import json
import re

_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "tr"}
_SKIP_TAGS = {"script", "style", "noscript", "svg"}
_HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
_LIST_MARK = {"ul": "- ", "ol": "1. "}


def _extract_citation_urls(attr_map: dict[str, str]) -> list[tuple[str, str | None, str | None]]:
    """Extract list of (url, name, title) from citation attributes."""
    results: list[tuple[str, str | None, str | None]] = []
    aria_label = attr_map.get("aria-label") or ""
    aria_title = None
    if aria_label:
        lbl = aria_label.strip()
        if lbl.lower().startswith("citation:"):
            lbl = lbl[9:].strip()
        if " — " in lbl:
            aria_title = lbl.split(" — ", 1)[1].strip()
        elif " - " in lbl:
            aria_title = lbl.split(" - ", 1)[1].strip()
        elif lbl:
            aria_title = lbl

    raw_grouped = attr_map.get("data-grouped-citations")
    if raw_grouped:
        try:
            cleaned = raw_grouped.replace("&quot;", '"')
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                is_multi = len(parsed) > 1
                for item in parsed:
                    if isinstance(item, dict) and item.get("url"):
                        u = item["url"]
                        name = (item.get("name") or "").strip() or None
                        # For multi-citations, aria_title refers to the first source plus "plus X more",
                        # so each source's specific identity is item.name.
                        item_title = name if is_multi else (aria_title or name)
                        results.append((u, name, item_title))
        except Exception:
            urls = re.findall(r'"url"\s*:\s*"([^"]+)"', raw_grouped)
            names = re.findall(r'"name"\s*:\s*"([^"]+)"', raw_grouped)
            for i, u in enumerate(urls):
                n = names[i] if i < len(names) else None
                results.append((u, n, aria_title))

    if not results:
        direct = attr_map.get("data-citation-url") or attr_map.get("data-url") or attr_map.get("href")
        if direct and direct.startswith(("http://", "https://")):
            name = (attr_map.get("data-citation-name") or attr_map.get("data-name") or "").strip() or None
            results.append((direct, name, aria_title))

    return results


class _MarkdownRenderer(HTMLParser):
    """Minimal HTML→Markdown converter (stdlib only, no extra dependencies)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._buffers: list[list[str]] = [[]]
        self._list_stack: list[str] = []
        self._list_counters: list[int] = []
        self._at_li_start = False
        self._in_pre = False
        self._in_code = False
        self._href_stack: list[str | None] = []
        self._link_text: list[str] | None = None
        self._citation_stack: list[tuple[str, list[tuple[str, str | None, str | None]]]] = []
        self._citation_text_stack: list[list[str]] = []
        self._code_stack: list[dict[str, Any]] = []
        self._math_stack: list[dict[str, Any]] = []
        self._skip_depth = 0

    @property
    def parts(self) -> list[str]:
        return self._buffers[-1]

    def _emit(self, text: str) -> None:
        if self._at_li_start and text.strip():
            self._at_li_start = False
        if self._citation_text_stack:
            self._citation_text_stack[-1].append(text)
        elif self._link_text is not None:
            self._link_text.append(text)
        else:
            self.parts.append(text)

    def _normalize_lang(self, raw_lang: str) -> str:
        lang = (raw_lang or "").strip().lower()
        if not lang or lang in {"plain text", "plaintext", "text", "none", "plain", "txt"}:
            return ""
        tokens = lang.split()
        if tokens and tokens[0] in {"plain text", "plaintext", "text", "none", "plain", "txt"}:
            return ""
        first = tokens[0] if tokens else lang
        if first.startswith("language-"):
            first = first[9:]
        elif first.startswith("lang-"):
            first = first[5:]
        return first.replace(" ", "")

    def _is_skip_in_code(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if tag in {"button", "svg", "textarea", "canvas"}:
            return True
        if "copy-button" in attr_map.get("id", "") or "copy" in cls:
            return True
        if "anticon" in cls or "fui-Button" in cls or "header-actions" in cls or "header-action" in cls:
            return True
        # Monaco / Ace / Copilot line numbers & gutter
        if "line-numbers" in cls or "margin" in cls or "glyph-margin" in cls or "gutter" in cls:
            return True
        if "data-line-number" in attr_map:
            return True
        # Editor overlays / minimaps / scrollbars
        if "cursors-layer" in cls or "scrollbar" in cls or "minimap" in cls or "decorations" in cls or "view-overlays" in cls:
            return True
        return False

    @staticmethod
    def _trim_code_block(lines: list[str]) -> str:
        if not lines:
            return ""

        raw_lines = [l.rstrip() for l in lines]
        while raw_lines and (not raw_lines[0].strip() or raw_lines[0].strip() in {"`", "``", "```"}):
            raw_lines.pop(0)
        while raw_lines and (not raw_lines[-1].strip() or raw_lines[-1].strip() in {"`", "``", "```"}):
            raw_lines.pop()

        if raw_lines and raw_lines[-1].rstrip().endswith("``") and not raw_lines[-1].rstrip().endswith("```"):
            raw_lines[-1] = raw_lines[-1].rstrip()[:-2].rstrip()

        if not raw_lines:
            return ""

        # Check for alternating empty lines (e.g. from HTML block div dumping)
        non_empty_indices = [i for i, l in enumerate(raw_lines) if l.strip()]
        if len(non_empty_indices) >= 2:
            gaps = [non_empty_indices[i + 1] - non_empty_indices[i] for i in range(len(non_empty_indices) - 1)]
            if all(g >= 2 for g in gaps):
                raw_lines = [raw_lines[i] for i in non_empty_indices]

        # Collapse excessive consecutive blank lines to at most 1 blank line
        cleaned: list[str] = []
        blank_count = 0
        for l in raw_lines:
            if not l.strip():
                blank_count += 1
                if blank_count <= 1:
                    cleaned.append("")
            else:
                blank_count = 0
                cleaned.append(l)

        while cleaned and (not cleaned[0].strip() or cleaned[0].strip() in {"`", "``", "```"}):
            cleaned.pop(0)
        while cleaned and (not cleaned[-1].strip() or cleaned[-1].strip() in {"`", "``", "```"}):
            cleaned.pop()

        if cleaned and cleaned[-1].rstrip().endswith("``") and not cleaned[-1].rstrip().endswith("```"):
            cleaned[-1] = cleaned[-1].rstrip()[:-2].rstrip()

        return "\n".join(cleaned)

    def _emit_code_block(self, top: dict[str, Any]) -> None:
        lines = top["view_lines"]
        if not lines and top["general_text"]:
            raw_text = "".join(top["general_text"])
            if raw_text:
                lines = raw_text.splitlines()

        lang = top["lang"]
        if not lang:
            raw_lang = "".join(top["lang_text"]).strip()
            if raw_lang:
                lang = self._normalize_lang(raw_lang)
        lang = lang or ""

        code_text = self._trim_code_block(lines)
        fenced = f"```{lang}\n{code_text}\n```"

        curr = self.parts
        if curr and not curr[-1].endswith("\n\n"):
            if curr[-1].endswith("\n"):
                curr.append("\n")
            else:
                curr.append("\n\n")
        curr.append(fenced)
        curr.append("\n\n")

    def _emit_math_block(self, top: dict[str, Any]) -> None:
        formula = (top.get("formula") or "").strip()
        if not formula and top.get("annotation_text"):
            formula = "".join(top["annotation_text"]).strip()
        if not formula and top.get("math_text"):
            formula = "".join(top["math_text"]).strip()
        if not formula and top.get("raw_text"):
            formula = "".join(top["raw_text"]).strip()

        if not formula:
            return

        formula = formula.strip()
        if formula.startswith("$$") and formula.endswith("$$") and len(formula) >= 4:
            formula = formula[2:-2].strip()
        elif formula.startswith("$") and formula.endswith("$") and len(formula) >= 2:
            formula = formula[1:-1].strip()
        elif formula.startswith(r"\[") and formula.endswith(r"\]") and len(formula) >= 4:
            formula = formula[2:-2].strip()
        elif formula.startswith(r"\(") and formula.endswith(r"\)") and len(formula) >= 4:
            formula = formula[2:-2].strip()

        if not formula:
            return

        if top.get("display"):
            curr = self.parts
            if curr and not curr[-1].endswith("\n\n"):
                if curr[-1].endswith("\n"):
                    curr.append("\n")
                else:
                    curr.append("\n\n")
            curr.append(f"$$\n{formula}\n$$")
            curr.append("\n\n")
        else:
            curr = self.parts
            if curr and curr[-1] and not curr[-1].endswith((" ", "\n", "(", "[", "{", ">", "*", "`")):
                curr.append(" ")
            curr.append(f"${formula}$")

    def _emit_blockquote(self, inner_raw: str) -> None:
        inner_text = inner_raw.strip()
        if not inner_text:
            return
        while "\n\n\n" in inner_text:
            inner_text = inner_text.replace("\n\n\n", "\n\n")
        lines = inner_text.splitlines()
        prefixed = [f"> {line}" if line.strip() else ">" for line in lines]
        bq_content = "\n".join(prefixed)
        curr = self._buffers[-1]
        if curr and not curr[-1].endswith("\n\n"):
            if curr[-1].endswith("\n"):
                curr.append("\n")
            else:
                curr.append("\n\n")
        curr.append(bq_content)
        curr.append("\n\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attr_map = {k: (v or "") for k, v in attrs}
        cls = attr_map.get("class", "")

        # Check for LaTeX / Math elements (Gemini math-block, KaTeX katex-display / katex, MathJax, MathML)
        has_math_attr = bool(attr_map.get("data-math") or attr_map.get("data-latex") or attr_map.get("data-tex"))
        is_math_block_cls = "math-block" in cls or "math-display" in cls or "katex-display" in cls
        is_math_inline_cls = "math-inline" in cls or ("katex" in cls and "katex-html" not in cls and "katex-mathml" not in cls)
        is_math_element = has_math_attr or is_math_block_cls or is_math_inline_cls

        if is_math_element and not self._math_stack and not self._code_stack:
            self._at_li_start = False
            is_display = (
                is_math_block_cls
                or tag in {"div", "p"}
                or attr_map.get("display") == "block"
                or "display" in cls
            )
            formula = (
                attr_map.get("data-math")
                or attr_map.get("data-latex")
                or attr_map.get("data-tex")
                or ""
            )
            self._math_stack.append({
                "tag": tag,
                "depth": 1,
                "display": is_display,
                "formula": formula,
                "annotation_text": [],
                "in_annotation": False,
                "math_text": [],
                "in_math": False,
                "raw_text": [],
                "skip_depth": 0,
            })
            return

        if self._math_stack:
            top = self._math_stack[-1]
            if tag == top["tag"]:
                top["depth"] += 1
            if tag in {"annotation", "script"}:
                if tag == "annotation" or "math/tex" in attr_map.get("type", ""):
                    top["in_annotation"] = True
            if tag == "math":
                top["in_math"] = True
            if "katex-html" in cls or attr_map.get("aria-hidden") == "true":
                top["skip_depth"] += 1
            elif top["skip_depth"] > 0:
                top["skip_depth"] += 1
            return

        # Check for code blocks (pre, Qwen/Monaco editor, Copilot scriptor-component-code-block / scriptor-codeblock-virtualized)
        is_qwen_block = "qwen-markdown-code" in cls and "qwen-markdown-codespan" not in cls
        is_code_block = (
            tag == "pre"
            or "scriptor-component-code-block" in cls
            or "scriptor-codeblock-virtualized" in cls
            or is_qwen_block
            or "monaco-editor" in cls
        )

        if is_code_block and not self._code_stack:
            self._at_li_start = False
            lang = (
                attr_map.get("data-mode-id")
                or attr_map.get("data-language")
                or attr_map.get("data-lang")
            )
            if not lang and "language-" in cls:
                m = re.search(r'language-([a-zA-Z0-9_\-+]+)', cls)
                if m: lang = m.group(1)
            elif not lang and "lang-" in cls:
                m = re.search(r'lang-([a-zA-Z0-9_\-+]+)', cls)
                if m: lang = m.group(1)

            self._code_stack.append({
                "tag": tag,
                "depth": 1,
                "lang": self._normalize_lang(lang) if lang else None,
                "lang_text": [],
                "in_lang": False,
                "lang_depth": 0,
                "view_lines": [],
                "curr_line": [],
                "in_line": False,
                "line_depth": 0,
                "general_text": [],
                "skip_depth": 0,
            })
            return

        if self._code_stack:
            top = self._code_stack[-1]
            if tag == top["tag"]:
                top["depth"] += 1

            if top["skip_depth"] > 0:
                top["skip_depth"] += 1
            elif self._is_skip_in_code(tag, attr_map, cls):
                top["skip_depth"] = 1

            if tag == "br":
                if top["in_line"]:
                    top["curr_line"].append("\n")
                else:
                    top["general_text"].append("\n")
                return

            if tag in _BLOCK_TAGS and not top["in_line"]:
                if top["general_text"] and not top["general_text"][-1].endswith("\n"):
                    top["general_text"].append("\n")

            if not top["lang"]:
                inner_lang = (
                    attr_map.get("data-mode-id")
                    or attr_map.get("data-language")
                    or attr_map.get("data-lang")
                )
                if not inner_lang and "language-" in cls:
                    m = re.search(r'language-([a-zA-Z0-9_\-+]+)', cls)
                    if m: inner_lang = m.group(1)
                elif not inner_lang and "lang-" in cls:
                    m = re.search(r'lang-([a-zA-Z0-9_\-+]+)', cls)
                    if m: inner_lang = m.group(1)
                if inner_lang:
                    top["lang"] = self._normalize_lang(inner_lang)

            is_lang_header = (
                attr_map.get("data-testid") == "one-copilot-code-identity"
                or "code-identity" in cls
                or "qwen-markdown-code-header" in cls
                or (("code-header" in cls or tag == "figcaption") and "actions" not in cls)
            )
            if is_lang_header:
                top["in_lang"] = True
                top["lang_depth"] = 1
            elif top["in_lang"]:
                top["lang_depth"] += 1

            is_line_elem = "view-line" in cls or "data-line-index" in attr_map
            if is_line_elem:
                top["in_line"] = True
                top["line_depth"] = 1
                top["curr_line"] = []
            elif top["in_line"]:
                top["line_depth"] += 1
            return

        # Check for citation elements (e.g. Copilot fai-BebopCitation button or tags with data-grouped-citations)
        is_citation_elem = (
            "fai-BebopCitation" in attr_map.get("class", "")
            or bool(attr_map.get("data-grouped-citations"))
            or bool(attr_map.get("data-citation-url"))
        )
        if is_citation_elem:
            citation_items = _extract_citation_urls(attr_map)
            if citation_items:
                self._citation_stack.append((tag, citation_items))
                self._citation_text_stack.append([])
                return

        if tag in _HEADING:
            self._at_li_start = False
            self.parts.append("\n\n" + _HEADING[tag] + " ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "hr":
            self._at_li_start = False
            self.parts.append("\n\n---\n\n")
        elif tag in _LIST_MARK:
            self._list_stack.append(tag)
            if tag == "ol":
                self._list_counters.append(1)
            else:
                self._list_counters.append(0)
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")
        elif tag in {"li"}:
            depth = max(0, len(self._list_stack) - 1)
            indent = "  " * depth
            if self._list_stack and self._list_stack[-1] == "ol" and self._list_counters:
                idx = self._list_counters[-1]
                marker = f"{idx}. "
                self._list_counters[-1] += 1
            else:
                marker = "- "
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")
            self.parts.append(indent + marker)
            self._at_li_start = True
        elif tag in _BLOCK_TAGS:
            if self._at_li_start:
                # First block inside a list item should be on the same line as the marker
                pass
            else:
                self.parts.append("\n\n")
        elif tag == "blockquote":
            self._at_li_start = False
            self._buffers.append([])
        elif tag in {"code", "tt"}:
            self._in_code = True
            self.parts.append("`")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "a":
            self._href_stack.append(attr_map.get("href"))
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return

        if self._math_stack:
            top = self._math_stack[-1]
            if top["skip_depth"] > 0:
                top["skip_depth"] -= 1
            if tag in {"annotation", "script"}:
                top["in_annotation"] = False
            if tag == "math":
                top["in_math"] = False
            if tag == top["tag"]:
                top["depth"] -= 1
                if top["depth"] <= 0:
                    self._math_stack.pop()
                    self._emit_math_block(top)
            return

        if self._code_stack:
            top = self._code_stack[-1]
            if top["skip_depth"] > 0:
                top["skip_depth"] -= 1

            if top["in_lang"]:
                top["lang_depth"] -= 1
                if top["lang_depth"] <= 0:
                    top["in_lang"] = False

            if top["in_line"]:
                top["line_depth"] -= 1
                if top["line_depth"] <= 0:
                    top["in_line"] = False
                    raw_line = "".join(top["curr_line"])
                    if raw_line == "\xa0":
                        line_str = ""
                    else:
                        line_str = raw_line.replace("\xa0", " ")
                    top["view_lines"].append(line_str)
                    top["curr_line"] = []

            if tag in _BLOCK_TAGS and not top["in_line"]:
                if top["general_text"] and not top["general_text"][-1].endswith("\n"):
                    top["general_text"].append("\n")

            if tag == top["tag"]:
                top["depth"] -= 1
                if top["depth"] <= 0:
                    self._code_stack.pop()
                    self._emit_code_block(top)
            return

        if self._citation_stack and self._citation_stack[-1][0] == tag:
            _, items = self._citation_stack.pop()
            text_parts = self._citation_text_stack.pop() if self._citation_text_stack else []
            raw_text = "".join(text_parts).strip()
            if raw_text.startswith("[") and raw_text.endswith("]") and len(raw_text) > 2:
                raw_text = raw_text[1:-1].strip()

            for u, name, title in items:
                display_label = name or (raw_text if len(items) == 1 else None) or title or "citation"
                md_link = f"[{display_label}]({u})"
                if self.parts and not self.parts[-1].endswith((" ", "\n", ">", "(")):
                    self.parts.append(" ")
                self.parts.append(md_link)
            return

        if tag in _HEADING:
            self.parts.append("\n\n")
        elif tag in _LIST_MARK:
            if self._list_stack:
                self._list_stack.pop()
            if self._list_counters:
                self._list_counters.pop()
            self._at_li_start = False
            self.parts.append("\n")
        elif tag == "li":
            self._at_li_start = False
            self.parts.append("\n")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "blockquote":
            if len(self._buffers) > 1:
                inner = self._buffers.pop()
                self._emit_blockquote("".join(inner))
        elif tag in {"code", "tt"}:
            if self._in_code:
                self.parts.append("`")
                self._in_code = False
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "a":
            text = "".join(self._link_text or []).strip()
            href = self._href_stack.pop() if self._href_stack else None
            self._link_text = None
            if href and text:
                self.parts.append(f"[{text}]({href})")
            elif text:
                self.parts.append(text)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._math_stack:
            top = self._math_stack[-1]
            if top["formula"]:
                return
            if top["skip_depth"] > 0:
                return
            if top["in_annotation"]:
                top["annotation_text"].append(data)
                return
            if top["in_math"]:
                top["math_text"].append(data)
                return
            top["raw_text"].append(data)
            return
        if self._code_stack:
            top = self._code_stack[-1]
            if top["skip_depth"] > 0:
                return
            if top["in_line"]:
                top["curr_line"].append(data)
            elif top["in_lang"]:
                top["lang_text"].append(data)
            else:
                top["general_text"].append(data)
            return
        self._emit(data)

    def markdown(self) -> str:
        while self._code_stack:
            top = self._code_stack.pop()
            self._emit_code_block(top)
        while self._math_stack:
            top = self._math_stack.pop()
            self._emit_math_block(top)
        while self._citation_stack:
            _, items = self._citation_stack.pop()
            text_parts = self._citation_text_stack.pop() if self._citation_text_stack else []
            raw_text = "".join(text_parts).strip()
            if raw_text.startswith("[") and raw_text.endswith("]") and len(raw_text) > 2:
                raw_text = raw_text[1:-1].strip()
            for u, name, title in items:
                display_label = name or (raw_text if len(items) == 1 else None) or title or "citation"
                md_link = f"[{display_label}]({u})"
                if self.parts and not self.parts[-1].endswith((" ", "\n", ">", "(")):
                    self.parts.append(" ")
                self.parts.append(md_link)
        while len(self._buffers) > 1:
            inner = self._buffers.pop()
            self._emit_blockquote("".join(inner))
        raw = "".join(self._buffers[0])
        lines = [line.rstrip() for line in raw.splitlines()]
        # Filter out empty list items (lines containing only a list marker without text), preserving and trimming code fences
        marker_pattern = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+\.)\s*$")
        cleaned_lines: list[str] = []
        in_fence = False
        fence_lang = ""
        fence_lines: list[str] = []
        for line in lines:
            if line.strip().startswith("```"):
                if not in_fence:
                    in_fence = True
                    fence_lang = line.strip()[3:]
                    fence_lines = []
                else:
                    in_fence = False
                    trimmed_code = self._trim_code_block(fence_lines)
                    cleaned_lines.append(f"```{fence_lang}")
                    if trimmed_code:
                        cleaned_lines.extend(trimmed_code.splitlines())
                    cleaned_lines.append("```")
            elif in_fence:
                fence_lines.append(line)
            elif not marker_pattern.match(line):
                cleaned_lines.append(line)
        if in_fence:
            trimmed_code = self._trim_code_block(fence_lines)
            cleaned_lines.append(f"```{fence_lang}")
            if trimmed_code:
                cleaned_lines.extend(trimmed_code.splitlines())
            cleaned_lines.append("```")
        text = "\n".join(cleaned_lines)
        while "\n\n\n\n" in text:
            text = text.replace("\n\n\n\n", "\n\n\n")
        return text.strip()


def clean_markdown_text(text: str) -> str:
    """Filter out empty list items and trim unnecessary lines inside code blocks."""
    if not text:
        return ""
    lines = [line.rstrip() for line in text.splitlines()]
    marker_pattern = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+\.)\s*$")
    cleaned_lines: list[str] = []
    in_fence = False
    fence_lang = ""
    fence_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("```"):
            if not in_fence:
                in_fence = True
                fence_lang = line.strip()[3:]
                fence_lines = []
            else:
                in_fence = False
                trimmed_code = _MarkdownRenderer._trim_code_block(fence_lines)
                cleaned_lines.append(f"```{fence_lang}")
                if trimmed_code:
                    cleaned_lines.extend(trimmed_code.splitlines())
                cleaned_lines.append("```")
        elif in_fence:
            fence_lines.append(line)
        elif not marker_pattern.match(line):
            cleaned_lines.append(line)
    if in_fence:
        trimmed_code = _MarkdownRenderer._trim_code_block(fence_lines)
        cleaned_lines.append(f"```{fence_lang}")
        if trimmed_code:
            cleaned_lines.extend(trimmed_code.splitlines())
        cleaned_lines.append("```")
    result = "\n".join(cleaned_lines)
    while "\n\n\n\n" in result:
        result = result.replace("\n\n\n\n", "\n\n\n")
    return result.strip()


def html_to_markdown(html: str) -> str:
    """Convert an HTML fragment to readable Markdown. Never raises on bad input."""
    if not html or not html.strip():
        return ""
    renderer = _MarkdownRenderer()
    try:
        renderer.feed(html)
        renderer.close()
    except Exception:  # noqa: BLE001 — malformed HTML should degrade, not crash
        return html.strip()
    return renderer.markdown()


def extract_source_links(html: str) -> list[tuple[str, str | None]]:
    """Pull (url, title) pairs from anchor tags in an HTML fragment."""
    if not html:
        return []
    parser = _LinkExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001
        return []
    return parser.links


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str | None]] = []
        self._href: str | None = None
        self._text: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if not self._skip_depth:
            attr_map = {k: (v or "") for k, v in attrs}
            is_citation_elem = (
                "fai-BebopCitation" in attr_map.get("class", "")
                or bool(attr_map.get("data-grouped-citations"))
                or bool(attr_map.get("data-citation-url"))
            )
            if is_citation_elem:
                items = _extract_citation_urls(attr_map)
                for u, name, t in items:
                    self.links.append((u, t or name))
            elif tag == "a":
                href = attr_map.get("href", "")
                if href.startswith(("http://", "https://")):
                    self._href = href
                    self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "a" and self._href is not None:
            title = "".join(self._text).strip() or None
            self.links.append((self._href, title))
            self._href = None
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None and not self._skip_depth:
            self._text.append(data)


def normalize_sources(pairs: Iterable[tuple[str, str | None]]) -> list[Source]:
    """Dedupe by URL, keep first title seen, drop non-http(s) URLs."""
    seen: set[str] = set()
    sources: list[Source] = []
    for url, title in pairs:
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url.startswith(("https://", "http://")) or url in seen:
            continue
        seen.add(url)
        sources.append(Source(url=url, title=(title.strip() if title else None) or None))
    return sources
