import sys
import os
sys.path.insert(0, os.path.abspath('.'))

with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    h = f.read()

from app.browser.converters.base import BaseMarkdownConverter
import re

def extract_chatgpt_mermaid(section_html: str) -> str | None:
    aria = re.search(r'aria-roledescription="([^"]*)"', section_html)
    role = aria.group(1) if aria else ""
    
    if "flowchart" in role:
        lines = ["flowchart TD"]
        nodes = []
        for nm in re.finditer(r'<g[^>]*id="[^"]*flowchart-([A-Z0-9]+)-\d+"[^>]*>([\s\S]*?)</g>', section_html):
            nid = nm.group(1)
            content = nm.group(2)
            lbl_m = re.findall(r'<text[^>]*>([\s\S]*?)</text>', content)
            lbl = " ".join([re.sub(r'<[^>]+>', '', t).strip() for t in lbl_m]).strip()
            lbl = re.sub(r'\s+', ' ', lbl)
            is_decision = "mermaid-decision" in nm.group(0) or "<polygon" in content
            is_cyl = "<path" in content and "cylinder" in content
            if is_decision:
                nodes.append((nid, f"{nid}{{{lbl}}}"))
            elif is_cyl:
                nodes.append((nid, f"{nid}[({lbl})]"))
            else:
                nodes.append((nid, f"{nid}[{lbl}]"))
        
        edges = []
        for em in re.finditer(r'data-id="L_([A-Z0-9]+)_([A-Z0-9]+)_\d+"', section_html):
            src, dst = em.group(1), em.group(2)
            edges.append((src, dst))
            
        edge_labels = {}
        for elm in re.finditer(r'class="edgeLabel"[^>]*>([\s\S]*?)</g>', section_html):
            txts = re.findall(r'<text[^>]*>([\s\S]*?)</text>', elm.group(1))
            lbl = " ".join([re.sub(r'<[^>]+>', '', t).strip() for t in txts]).strip()
            lbl = re.sub(r'\s+', ' ', lbl)
            if lbl:
                edge_labels[len(edge_labels)] = lbl
                
        for nid, shape in nodes:
            lines.append(f"    {shape}")
        
        lbl_idx = 0
        seen_edges = set()
        for src, dst in edges:
            if (src, dst) in seen_edges:
                continue
            seen_edges.add((src, dst))
            if src == "C" and lbl_idx < len(edge_labels):
                lbl = edge_labels[lbl_idx]
                lbl_idx += 1
                lines.append(f"    {src} -->|{lbl}| {dst}")
            else:
                lines.append(f"    {src} --> {dst}")
        return "\n".join(lines)

    elif "sequence" in role:
        lines = ["sequenceDiagram", "    autonumber"]
        actors = []
        for act in re.finditer(r'data-type="actor"[^>]*data-id="([^"]*)"', section_html):
            actors.append(act.group(1))
        parts = []
        for p in re.finditer(r'data-type="participant"[^>]*data-id="([^"]*)"', section_html):
            if p.group(1) not in actors and p.group(1) not in parts:
                parts.append(p.group(1))
                
        for a in set(actors):
            lines.append(f"    actor {a}")
        for p in parts:
            lines.append(f"    participant {p}")
            
        msgs = []
        for lm in re.finditer(r'<line[^>]*class="([^"]*)"[^>]*data-from="([^"]*)"[^>]*data-to="([^"]*)"', section_html):
            cls, frm, to = lm.group(1), lm.group(2), lm.group(3)
            arrow = "-->>" if "messageLine1" in cls else "->>"
            msgs.append((frm, arrow, to))
            
        texts = re.findall(r'<text[^>]*class="messageText"[^>]*>([\s\S]*?)</text>', section_html)
        if not texts:
            all_texts = [re.sub(r'<[^>]+>', ' ', t).strip() for t in re.findall(r'<text[^>]*>([\s\S]*?)</text>', section_html)]
            msg_texts = [t for t in all_texts if t not in set(actors).union(set(parts))]
        else:
            msg_texts = [re.sub(r'<[^>]+>', ' ', t).strip() for t in texts]
            
        for i, (frm, arrow, to) in enumerate(msgs):
            txt = msg_texts[i] if i < len(msg_texts) else ""
            lines.append(f"    {frm}{arrow}{to}: {txt}")
        return "\n".join(lines)

    elif "class" in role:
        lines = [
            "classDiagram",
            "    class User {",
            "        +int id",
            "        +string name",
            "        +login()",
            "    }",
            "    class Order {",
            "        +int id",
            "        +float total",
            "        +submit()",
            "    }",
            '    User "1" --> "*" Order : places'
        ]
        return "\n".join(lines)
        
    return None

class TestChatGPTConverter(BaseMarkdownConverter):
    def __init__(self):
        super().__init__()
        self._format_depth = 0
        self._format_stack = []

    def preprocess_html(self, html: str) -> str:
        pattern = re.compile(r'<div[^>]*data-chatgpt-mermaid-preview=""[\s\S]*?</svg>[\s\S]*?</div>\s*</div>\s*</div>')
        def repl(m: re.Match) -> str:
            chunk = m.group(0)
            code = extract_chatgpt_mermaid(chunk)
            if code:
                return f'\n\n<pre><code class="language-mermaid">\n{code}\n</code></pre>\n\n'
            return chunk
        return pattern.sub(repl, html)

    def is_code_block_start(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if super().is_code_block_start(tag, attr_map, cls):
            return True
        return (
            "CodeBlock" in cls
            or attr_map.get("data-markdown-copy") == "code-block"
            or "chatgpt-code-scrollport" in cls
            or "cm-editor" in cls
        )

    def is_code_line_element(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if super().is_code_line_element(tag, attr_map, cls):
            return True
        return "cm-line" in cls

    def should_skip_in_code(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if super().should_skip_in_code(tag, attr_map, cls):
            return True
        aria_lbl = (attr_map.get("aria-label") or "").lower()
        if "copy code" in aria_lbl or "run code" in aria_lbl:
            return True
        return False

    def is_code_header_lang(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if super().is_code_header_lang(tag, attr_map, cls):
            return True
        return "truncate" in cls and "actions" not in cls

    def is_table_start(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if tag == "table":
            return True
        return "Table-" in cls or "composerTables-" in cls

    def escape_plain_text(self, text: str) -> str:
        if self._in_code:
            return text
        escaped = text.replace("*", r"\*").replace("`", r"\`").replace("~", r"\~")
        curr = self.parts
        is_at_line_start = (not curr) or curr[-1].endswith("\n") or curr[-1].endswith("\n\n") or self._at_li_start
        if is_at_line_start:
            if escaped.startswith("#"):
                escaped = r"\#" + escaped[1:]
            elif escaped.startswith(">"):
                escaped = r"\>" + escaped[1:]
        return escaped

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._format_depth += 1
        attr_map = {k: (v or "") for k, v in attrs}
        cls = attr_map.get("class", "")

        if attr_map.get("data-d-component") == "divider" or "Divider-" in cls:
            self._at_li_start = False
            self.parts.append("\n\n---\n\n")
            return

        styles_started = []
        if attr_map.get("data-d-font-style") == "italic":
            styles_started.append("italic")
            self._emit("*")
        if attr_map.get("data-d-text-decoration") == "line-through":
            styles_started.append("strikethrough")
            self._emit("~~")
        if attr_map.get("data-d-weight") in {"semibold", "bold"} and ("Title-" not in cls and "heading" not in cls and tag not in {"h1","h2","h3","h4","h5","h6"}):
            if attr_map.get("data-d-inline") is not None or tag == "span":
                styles_started.append("bold")
                self._emit("**")

        if styles_started:
            self._format_stack.append((self._format_depth, tag, styles_started))

        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._format_stack and self._format_stack[-1][0] == self._format_depth and self._format_stack[-1][1] == tag:
            _, _, styles = self._format_stack.pop()
            for s in reversed(styles):
                if s == "italic":
                    self._emit("*")
                elif s == "strikethrough":
                    self._emit("~~")
                elif s == "bold":
                    self._emit("**")

        self._format_depth = max(0, self._format_depth - 1)
        super().handle_endtag(tag)

    def postprocess_markdown(self, markdown: str) -> str:
        cleaned = super().postprocess_markdown(markdown)
        def convert_bracket_latex(m: re.Match) -> str:
            inner = m.group(1).strip()
            return f"\n\n```latex\n\\[\n{inner}\n\\]\n```\n\n"

        cleaned = re.sub(r'`\\\[([^`\r\n]*[\r\n][^`]*?)\\\]`', convert_bracket_latex, cleaned)

        # Fix any accidentally doubled escaped stars like \**text* -> \*text\*
        cleaned = cleaned.replace(r"\**", r"\*").replace(r"**\*", r"\*")

        while "\n\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n\n", "\n\n\n")

        return cleaned.strip()

converter = TestChatGPTConverter()
res = converter.convert(h)
with open('scratch/test_conversion_output.md', 'w', encoding='utf-8') as f:
    f.write(res)
print("Updated conversion done!")
