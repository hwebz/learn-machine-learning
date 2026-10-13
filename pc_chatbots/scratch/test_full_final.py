import sys
sys.stdout.reconfigure(encoding='utf-8')
import re
from html.parser import HTMLParser
from app.adapters.base import Source

_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer"}
_SKIP_TAGS = {"script", "style", "noscript", "svg"}
_HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
_LIST_MARK = {"ul": "- ", "ol": "1. "}

class NewMarkdownRenderer(HTMLParser):
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
        self._code_stack: list[dict] = []
        self._math_stack: list[dict] = []
        self._table_stack: list[dict] = []
        self._skip_depth = 0

    @property
    def parts(self) -> list[str]:
        return self._buffers[-1]

    def _emit(self, text: str) -> None:
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
        if "line-numbers" in cls or "margin" in cls or "glyph-margin" in cls or "gutter" in cls:
            return True
        if "data-line-number" in attr_map:
            return True
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

    def _emit_code_block(self, top: dict) -> None:
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

    def _emit_math_block(self, top: dict) -> None:
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

    def _emit_table(self, info: dict) -> None:
        rows_with_meta = info["rows"]
        if not rows_with_meta:
            return
        max_cols = max(len(r[0]) for r in rows_with_meta)
        if max_cols == 0:
            return
        table_md_lines = []
        first_row, first_is_header = rows_with_meta[0]
        first_row_padded = first_row + [""] * (max_cols - len(first_row))
        table_md_lines.append("| " + " | ".join(first_row_padded) + " |")
        table_md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attr_map = {k: (v or "") for k, v in attrs}
        cls = attr_map.get("class", "")

        # Table handling
        if tag == "table":
            self._table_stack.append({
                "rows": [],
                "curr_row": [],
                "curr_cell": None,
                "in_cell": False,
                "in_header": False,
                "header_count": 0,
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
                return

        # Math handling
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

        # Code block handling (pre, Qwen/Monaco, Copilot scriptor, ChatGPT CodeBlock)
        is_qwen_block = "qwen-markdown-code" in cls and "qwen-markdown-codespan" not in cls
        is_chatgpt_block = (
            "CodeBlock" in cls
            or attr_map.get("data-markdown-copy") == "code-block"
            or "chatgpt-code-scrollport" in cls
            or "cm-editor" in cls
        )
        is_code_block = (
            tag == "pre"
            or "scriptor-component-code-block" in cls
            or "scriptor-codeblock-virtualized" in cls
            or is_qwen_block
            or is_chatgpt_block
            or "monaco-editor" in cls
        )

        if is_code_block and not self._code_stack and not self._table_stack:
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
                or "truncate" in cls
                or (("code-header" in cls or tag == "figcaption") and "actions" not in cls)
            )
            if is_lang_header and not top["lang"]:
                top["in_lang"] = True
                top["lang_depth"] = 1
            elif top["in_lang"]:
                top["lang_depth"] += 1

            is_line_elem = "view-line" in cls or "cm-line" in cls or "data-line-index" in attr_map
            if is_line_elem:
                top["in_line"] = True
                top["line_depth"] = 1
                top["curr_line"] = []
            elif top["in_line"]:
                top["line_depth"] += 1
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
        elif tag == "li":
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
            if not self._at_li_start:
                self.parts.append("\n\n")
        elif tag in {"code", "tt"}:
            self._in_code = True
            self._emit("`")
        elif tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("*")

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

        if self._table_stack:
            top = self._table_stack[-1]
            if tag in {"th", "td"} and top["in_cell"]:
                cell_text = "".join(top["curr_cell"]).strip()
                cell_text = cell_text.replace("\n", " ").replace("|", "\\|")
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
                    line_str = "" if raw_line == "\xa0" else raw_line.replace("\xa0", " ")
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
        elif tag in {"code", "tt"}:
            if self._in_code:
                self._emit("`")
                self._in_code = False
        elif tag in {"strong", "b"}:
            self._emit("**")
        elif tag in {"em", "i"}:
            self._emit("*")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._math_stack:
            top = self._math_stack[-1]
            if top["formula"] or top["skip_depth"] > 0:
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
        while self._table_stack:
            table_info = self._table_stack.pop()
            self._emit_table(table_info)

        raw = "".join(self._buffers[0])
        # Post-clean:
        # Also check if any inline code contains \[ ... \] or \begin{...} ... \end{...}
        # and convert it to a fenced ```latex block if it does not start and end with $$
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

        # Convert any remaining `\[ ... \]` inline or standalone blocks to ```latex
        # e.g. `\[\n...\n\]` -> ```latex\n\[\n...\n\]\n```
        def convert_bracket_latex(m):
            inner = m.group(1).strip()
            return f"\n\n```latex\n\\[\n{inner}\n\\]\n```\n\n"

        text = re.sub(r'`\\\[([\s\S]*?)\\\]`', convert_bracket_latex, text)

        while "\n\n\n\n" in text:
            text = text.replace("\n\n\n\n", "\n\n\n")
        return text.strip()

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find('data-markdown-text-style="assistant-message"')
msg_html = html[idx:idx+150000]

renderer = NewMarkdownRenderer()
renderer.feed(msg_html)
renderer.close()
res = renderer.markdown()

print("=== FINAL EXTRACTED TEXT (SAMPLE 1500 chars) ===")
print(res[:1500])

print("\n=== FINAL EXTRACTED TABLES ===")
for line in res.splitlines():
    if line.startswith("|"):
        print(line)
