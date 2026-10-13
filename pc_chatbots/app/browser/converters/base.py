from __future__ import annotations

from html.parser import HTMLParser
from typing import Any, Iterable
import html
import json
import re

_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer"}
_SKIP_TAGS = {"script", "style", "noscript", "svg"}
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
_LIST_MARK = {"ul": "- ", "ol": "1. "}


def extract_citation_urls(attr_map: dict[str, str]) -> list[tuple[str, str | None, str | None]]:
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


class BaseMarkdownConverter(HTMLParser):
    """General HTML5 to Markdown converter with template hooks for provider customization."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._buffers: list[list[str]] = [[]]
        self._list_stack: list[str] = []
        self._list_counters: list[int] = []
        self._at_li_start = False
        self._in_pre = False
        self._in_code = False
        self._inline_code_buffer: list[list[str]] = []
        self._href_stack: list[str | None] = []
        self._link_text: list[str] | None = None
        self._citation_stack: list[tuple[str, list[tuple[str, str | None, str | None]]]] = []
        self._citation_text_stack: list[list[str]] = []
        self._code_stack: list[dict[str, Any]] = []
        self._math_stack: list[dict[str, Any]] = []
        self._table_stack: list[dict[str, Any]] = []
        self._raw_html_stack: list[dict[str, Any]] = []
        self._skip_depth = 0
        self._li_depth = 0

    @property
    def parts(self) -> list[str]:
        return self._buffers[-1]

    # -------------------------------------------------------------------------
    # Lifecycle & Extension Hooks (Subclasses can override)
    # -------------------------------------------------------------------------

    def preprocess_html(self, html: str) -> str:
        """Hook to sanitize or prepare raw HTML before parsing."""
        return html

    def postprocess_markdown(self, markdown: str) -> str:
        """Hook to clean up or transform markdown after parsing."""
        return self.default_cleanup(markdown)

    def escape_plain_text(self, text: str) -> str:
        """Hook to escape literal markdown syntax characters in plain text."""
        return text

    def is_skip_tag(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Return True if element should be completely ignored (including children)."""
        return tag in _SKIP_TAGS

    def is_raw_html_block_start(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Hook to declare standalone HTML components that should be preserved as raw HTML."""
        return False

    def is_table_start(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Return True if element starts a table."""
        return tag == "table"

    def is_math_block_start(self, tag: str, attr_map: dict[str, str], cls: str) -> tuple[bool, bool, str]:
        """Return (is_math, is_display, formula_if_known)."""
        has_math_attr = bool(attr_map.get("data-math") or attr_map.get("data-latex") or attr_map.get("data-tex"))
        is_math_block_cls = "math-block" in cls or "math-display" in cls or "katex-display" in cls
        is_math_inline_cls = "math-inline" in cls or ("katex" in cls and "katex-html" not in cls and "katex-mathml" not in cls)
        is_math = has_math_attr or is_math_block_cls or is_math_inline_cls

        if not is_math:
            return (False, False, "")

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
        return (True, is_display, formula)

    def is_code_block_start(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Return True if element starts a preformatted code block."""
        is_qwen_block = "qwen-markdown-code" in cls and "qwen-markdown-codespan" not in cls
        return (
            tag == "pre"
            or "scriptor-component-code-block" in cls
            or "scriptor-codeblock-virtualized" in cls
            or is_qwen_block
            or "monaco-editor" in cls
        )

    def extract_code_lang(self, tag: str, attr_map: dict[str, str], cls: str) -> str | None:
        """Extract programming language identifier from tag attributes or class."""
        lang = (
            attr_map.get("data-mode-id")
            or attr_map.get("data-language")
            or attr_map.get("data-lang")
        )
        if not lang and "language-" in cls:
            m = re.search(r'language-([a-zA-Z0-9_\-+]+)', cls)
            if m:
                lang = m.group(1)
        elif not lang and "lang-" in cls:
            m = re.search(r'lang-([a-zA-Z0-9_\-+]+)', cls)
            if m:
                lang = m.group(1)
        return self._normalize_lang(lang) if lang else None

    def is_code_header_lang(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Return True if element is a header displaying the language name."""
        return (
            attr_map.get("data-testid") == "one-copilot-code-identity"
            or "code-identity" in cls
            or "qwen-markdown-code-header" in cls
            or (("code-header" in cls or tag == "figcaption") and "actions" not in cls)
        )

    def is_code_line_element(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Return True if element represents a single virtualized line in a code editor."""
        return "view-line" in cls or "data-line-index" in attr_map

    def should_skip_in_code(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Return True if element inside a code block should be omitted (buttons, gutters)."""
        if tag in {"button", "svg", "textarea", "canvas"}:
            return True
        if "copy-button" in attr_map.get("id", "") or "copy" in cls:
            return True
        if "anticon" in cls or "fui-Button" in cls or "header-actions" in cls or "header-action" in cls:
            return True
        if "line-numbers" in cls or "margin" in cls or "glyph-margin" in cls or "gutter" in cls:
            return True
        if "data-line-number" in attr_map:
            return True
        if "cursors-layer" in cls or "scrollbar" in cls or "minimap" in cls or "decorations" in cls or "view-overlays" in cls:
            return True
        return False

    def is_citation_element(self, tag: str, attr_map: dict[str, str], cls: str) -> tuple[bool, list[tuple[str, str | None, str | None]]]:
        """Return (is_citation, [(url, name, title)])."""
        is_cit = (
            "fai-BebopCitation" in cls
            or bool(attr_map.get("data-grouped-citations"))
            or bool(attr_map.get("data-citation-url"))
        )
        if is_cit:
            items = extract_citation_urls(attr_map)
            if items:
                return (True, items)
        return (False, [])

    # -------------------------------------------------------------------------
    # Core Formatting Helpers
    # -------------------------------------------------------------------------

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

    @staticmethod
    def format_inline_code(code_text: str) -> str:
        if not code_text:
            return ""
        runs = re.findall(r"`+", code_text)
        max_run = max((len(r) for r in runs), default=0)
        fence_len = max_run + 1 if max_run > 0 else 1
        fence = "`" * fence_len
        needs_space_padding = (
            code_text.startswith("`")
            or code_text.endswith("`")
            or (code_text.startswith(" ") and code_text.endswith(" ") and bool(code_text.strip()))
        )
        if needs_space_padding:
            return f"{fence} {code_text} {fence}"
        return f"{fence}{code_text}{fence}"

    def _emit(self, text: str) -> None:
        if self._inline_code_buffer:
            self._inline_code_buffer[-1].append(text)
            return
        if self._table_stack and self._table_stack[-1]["in_cell"]:
            self._table_stack[-1]["curr_cell"].append(text)
            return
        if self._at_li_start and text.strip():
            self._at_li_start = False
        if self._citation_text_stack:
            self._citation_text_stack[-1].append(text)
        elif self._link_text is not None:
            self._link_text.append(text)
        else:
            self.parts.append(text)

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

        non_empty_indices = [i for i, l in enumerate(raw_lines) if l.strip()]
        if len(non_empty_indices) >= 2:
            gaps = [non_empty_indices[i + 1] - non_empty_indices[i] for i in range(len(non_empty_indices) - 1)]
            if all(g >= 2 for g in gaps):
                raw_lines = [raw_lines[i] for i in non_empty_indices]

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

    def _emit_raw_html_block(self, html_block: str) -> None:
        if not html_block:
            return
        curr = self.parts
        if curr and not curr[-1].endswith("\n\n"):
            if curr[-1].endswith("\n"):
                curr.append("\n")
            else:
                curr.append("\n\n")
        curr.append(html_block)
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

        if self._table_stack and self._table_stack[-1]["in_cell"]:
            self._table_stack[-1]["curr_cell"].append(f"${formula}$")
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

    def _emit_table(self, info: dict[str, Any]) -> None:
        rows_with_meta = info["rows"]
        if not rows_with_meta:
            return
        max_cols = max(len(r[0]) for r in rows_with_meta)
        if max_cols == 0:
            return
        alignments = info.get("col_alignments", [])
        sep_cells: list[str] = []
        for c in range(max_cols):
            align = alignments[c] if c < len(alignments) else ""
            if align == "center":
                sep_cells.append(":---:")
            elif align == "right":
                sep_cells.append("---:")
            elif align == "left":
                sep_cells.append(":---")
            else:
                sep_cells.append("---")

        table_md_lines: list[str] = []
        first_row, _ = rows_with_meta[0]
        first_row_padded = first_row + [""] * (max_cols - len(first_row))
        table_md_lines.append("| " + " | ".join(first_row_padded) + " |")
        table_md_lines.append("| " + " | ".join(sep_cells) + " |")
        for row, _ in rows_with_meta[1:]:
            padded = row + [""] * (max_cols - len(row))
            table_md_lines.append("| " + " | ".join(padded) + " |")
        curr = self.parts
        if curr and not curr[-1].endswith("\n\n"):
            if curr[-1].endswith("\n"):
                curr.append("\n")
            else:
                curr.append("\n\n")
        curr.append("\n".join(table_md_lines))
        curr.append("\n\n")

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

    # -------------------------------------------------------------------------
    # HTMLParser Callback Implementations
    # -------------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        cls = attr_map.get("class", "")

        if self.is_skip_tag(tag, attr_map, cls):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        # Raw HTML standalone component block
        if not self._raw_html_stack and not self._table_stack and not self._code_stack and not self._math_stack:
            if self.is_raw_html_block_start(tag, attr_map, cls):
                self._at_li_start = False
                raw_start = self.get_starttag_text() or f"<{tag}>"
                self._raw_html_stack.append({
                    "tag": tag,
                    "depth": 1,
                    "parts": [raw_start],
                })
                return

        if self._raw_html_stack:
            top = self._raw_html_stack[-1]
            if tag == top["tag"]:
                top["depth"] += 1
            raw_start = self.get_starttag_text() or f"<{tag}>"
            top["parts"].append(raw_start)
            return

        # Table handling
        if self.is_table_start(tag, attr_map, cls):
            self._table_stack.append({
                "rows": [],
                "curr_row": [],
                "curr_cell": None,
                "in_cell": False,
                "in_header": False,
                "header_count": 0,
                "col_alignments": [],
            })
            return

        if self._table_stack and not self._math_stack:
            top = self._table_stack[-1]
            if tag == "thead":
                top["in_header"] = True
                return
            if tag == "tr":
                top["curr_row"] = []
                top["header_count"] = 0
                return
            if tag in {"th", "td"}:
                top["in_cell"] = True
                top["curr_cell"] = []
                if tag == "th" or top["in_header"]:
                    top["header_count"] += 1
                col_idx = len(top["curr_row"])
                raw_align = (attr_map.get("data-d-align") or attr_map.get("align") or "").lower()
                align = ""
                if raw_align in {"start", "left"}:
                    align = "left"
                elif raw_align in {"center", "middle"}:
                    align = "center"
                elif raw_align in {"end", "right"}:
                    align = "right"
                while len(top["col_alignments"]) <= col_idx:
                    top["col_alignments"].append("")
                if align and not top["col_alignments"][col_idx]:
                    top["col_alignments"][col_idx] = align
                return

        # Math / LaTeX elements
        is_math, is_display, formula = self.is_math_block_start(tag, attr_map, cls)
        if is_math and not self._math_stack and not self._code_stack:
            self._at_li_start = False
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

        # Code block handling
        if self.is_code_block_start(tag, attr_map, cls) and not self._code_stack and not self._table_stack:
            self._at_li_start = False
            lang = self.extract_code_lang(tag, attr_map, cls)

            self._code_stack.append({
                "tag": tag,
                "depth": 1,
                "lang": lang,
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
            elif self.should_skip_in_code(tag, attr_map, cls):
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
                inner_lang = self.extract_code_lang(tag, attr_map, cls)
                if inner_lang:
                    top["lang"] = inner_lang

            if self.is_code_header_lang(tag, attr_map, cls) and not top["lang"]:
                top["in_lang"] = True
                top["lang_depth"] = 1
            elif top["in_lang"]:
                top["lang_depth"] += 1

            if self.is_code_line_element(tag, attr_map, cls):
                top["in_line"] = True
                top["line_depth"] = 1
                top["curr_line"] = []
            elif top["in_line"]:
                top["line_depth"] += 1
            return

        # Citation handling
        is_cit, citation_items = self.is_citation_element(tag, attr_map, cls)
        if is_cit and citation_items:
            self._citation_stack.append((tag, citation_items))
            self._citation_text_stack.append([])
            return

        # Checkboxes (task lists)
        is_checkbox = (
            attr_map.get("role") == "checkbox"
            or attr_map.get("data-d-component") == "checkbox"
            or attr_map.get("type") == "checkbox"
            or "Checkbox-" in cls
        )
        if is_checkbox:
            is_checked = (
                attr_map.get("aria-checked") == "true"
                or attr_map.get("data-state") == "checked"
                or attr_map.get("checked") in {"", "true", "checked"}
            )
            box_mark = "[x] " if is_checked else "[ ] "
            if self._at_li_start:
                self.parts.append(box_mark)
                self._at_li_start = False
            else:
                if self.parts and not self.parts[-1].endswith("\n"):
                    self.parts.append("\n")
                indent = "    " * max(0, len(self._list_stack))
                self.parts.append(f"{indent}- {box_mark}")
            return

        # Standard HTML5 text elements
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
        elif tag == "li":
            self._li_depth += 1
            depth = max(0, len(self._list_stack) - 1)
            indent = "    " * depth
            if self._list_stack and self._list_stack[-1] == "ol" and self._list_counters:
                idx = self._list_counters[-1]
                marker = f"{idx}. "
                self._list_counters[-1] += 1
            else:
                marker = "- "
            if self.parts:
                while len(self.parts) > 1 and self.parts[-1] == "\n" and self.parts[-2].endswith("\n"):
                    self.parts.pop()
                if self.parts and self.parts[-1].endswith("\n\n"):
                    self.parts[-1] = self.parts[-1][:-1]
                elif self.parts and not self.parts[-1].endswith("\n"):
                    self.parts.append("\n")
            self.parts.append(indent + marker)
            self._at_li_start = True
        elif tag in _BLOCK_TAGS:
            if not self._at_li_start and self._li_depth == 0:
                self.parts.append("\n\n")
        elif tag == "blockquote":
            self._at_li_start = False
            self._buffers.append([])
        elif tag in {"code", "tt"}:
            self._in_code = True
            self._inline_code_buffer.append([])
        elif tag in {"strong", "b"}:
            if not self._in_code:
                self._emit("**")
        elif tag in {"em", "i"}:
            if not self._in_code:
                self._emit("*")
        elif tag in {"u", "ins"}:
            if not self._in_code:
                self._emit("<u>")
        elif tag == "a":
            self._href_stack.append(attr_map.get("href"))
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return

        if self._raw_html_stack:
            top = self._raw_html_stack[-1]
            if tag not in _VOID_TAGS:
                top["parts"].append(f"</{tag}>")
            if tag == top["tag"]:
                top["depth"] -= 1
                if top["depth"] <= 0:
                    self._raw_html_stack.pop()
                    html_block = "".join(top["parts"]).strip()
                    self._emit_raw_html_block(html_block)
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

        if self._table_stack and not self._math_stack:
            top = self._table_stack[-1]
            if tag in {"th", "td"} and top["in_cell"]:
                cell_text = "".join(top["curr_cell"]).strip()
                cell_text = cell_text.replace("\n", " ")
                cell_text = re.sub(r'(?<!\\)\|', r'\|', cell_text)
                top["curr_row"].append(cell_text)
                top["in_cell"] = False
                top["curr_cell"] = None
                return
            if tag == "tr":
                if top["curr_row"]:
                    top["rows"].append((top["curr_row"], top["header_count"] > 0))
                top["curr_row"] = []
                return
            if tag == "thead":
                top["in_header"] = False
                return
            if tag == "table":
                table_info = self._table_stack.pop()
                self._emit_table(table_info)
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
            self._li_depth = max(0, self._li_depth - 1)
            self._at_li_start = False
            if self.parts and not self.parts[-1].endswith("\n"):
                self.parts.append("\n")
        elif tag in _BLOCK_TAGS:
            if self._li_depth == 0:
                self.parts.append("\n\n")
        elif tag == "blockquote":
            if len(self._buffers) > 1:
                inner = self._buffers.pop()
                self._emit_blockquote("".join(inner))
        elif tag in {"code", "tt"}:
            if self._inline_code_buffer:
                buf = self._inline_code_buffer.pop()
                if not self._inline_code_buffer:
                    self._in_code = False
                code_text = "".join(buf)
                formatted_code = self.format_inline_code(code_text)
                self._emit(formatted_code)
            elif self._in_code:
                self._in_code = False
                self._emit("`")
        elif tag in {"strong", "b"}:
            if not self._in_code:
                self._emit("**")
        elif tag in {"em", "i"}:
            if not self._in_code:
                self._emit("*")
        elif tag in {"u", "ins"}:
            if not self._in_code:
                self._emit("</u>")
        elif tag == "a":
            text = "".join(self._link_text or []).strip()
            href = self._href_stack.pop() if self._href_stack else None
            self._link_text = None
            if href and text:
                self._emit(f"[{text}]({href})")
            elif text:
                self._emit(text)

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._raw_html_stack:
            self._raw_html_stack[-1]["parts"].append(html.escape(data, quote=False))
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
        if self._inline_code_buffer:
            self._inline_code_buffer[-1].append(data)
            return
        if self._table_stack and not self._math_stack:
            top = self._table_stack[-1]
            if top["in_cell"] and top["curr_cell"] is not None:
                top["curr_cell"].append(data)
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
        escaped_data = self.escape_plain_text(data)
        self._emit(escaped_data)

    def default_cleanup(self, raw: str) -> str:
        """Standard Markdown normalization: trims empty list items and code blocks."""
        lines = [line.rstrip() for line in raw.splitlines()]
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

    def convert(self, html: str) -> str:
        """Complete pipeline: preprocess -> parse -> postprocess."""
        if not html or not html.strip():
            return ""

        prepared_html = self.preprocess_html(html)
        try:
            self.feed(prepared_html)
            self.close()
        except Exception:  # noqa: BLE001
            return html.strip()

        # Flush any remaining unclosed stacks
        while self._code_stack:
            top = self._code_stack.pop()
            self._emit_code_block(top)
        while self._math_stack:
            top = self._math_stack.pop()
            self._emit_math_block(top)
        while self._table_stack:
            table_info = self._table_stack.pop()
            self._emit_table(table_info)
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

        raw_md = "".join(self._buffers[0])
        return self.postprocess_markdown(raw_md)
