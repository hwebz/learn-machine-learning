import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.browser.extraction import _MarkdownRenderer

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find('data-markdown-text-style="assistant-message"')
msg_html = html[idx:idx+150000]

class TestFullRenderer(_MarkdownRenderer):
    def __init__(self):
        super().__init__()
        self._table_stack = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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

        if self._table_stack:
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

        # ChatGPT Code Block handling
        is_chatgpt_block = (
            "CodeBlock" in cls
            or attr_map.get("data-markdown-copy") == "code-block"
        )
        if is_chatgpt_block and not self._code_stack and not self._table_stack:
            self._code_stack.append({
                "tag": tag,
                "depth": 1,
                "lang": None,
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
            if "truncate" in cls and not top["lang"]:
                top["in_lang"] = True
                top["lang_depth"] = 1
            if "cm-line" in cls:
                top["in_line"] = True
                top["line_depth"] = 1
                top["curr_line"] = []

        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
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

        super().handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._table_stack:
            top = self._table_stack[-1]
            if top["in_cell"] and top["curr_cell"] is not None:
                top["curr_cell"].append(data)
                return
        super().handle_data(data)

    def _emit_table(self, info: dict) -> None:
        rows_with_meta = info["rows"]
        if not rows_with_meta:
            return
        
        # Max cols
        max_cols = max(len(r[0]) for r in rows_with_meta)
        if max_cols == 0:
            return

        table_md_lines = []
        first_row, first_is_header = rows_with_meta[0]
        # Pad first row
        first_row_padded = first_row + [""] * (max_cols - len(first_row))
        table_md_lines.append("| " + " | ".join(first_row_padded) + " |")
        table_md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

        # Data rows
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

renderer = TestFullRenderer()
renderer.feed(msg_html)
renderer.close()
res = renderer.markdown()

print("=== CHECKING TABLES IN OUTPUT ===")
for line in res.splitlines():
    if line.startswith("|"):
        print(line)
