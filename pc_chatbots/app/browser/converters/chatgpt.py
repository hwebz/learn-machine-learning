from __future__ import annotations

import re
from typing import Any
from app.browser.converters.base import BaseMarkdownConverter


def extract_chatgpt_mermaid(section_html: str) -> str | None:
    """Extract and reconstruct Mermaid diagram code from ChatGPT's rendered SVG preview."""
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

    if "sequence" in role:
        lines = ["sequenceDiagram", "    autonumber"]

        actor_kinds: dict[str, str] = {}
        for act in re.finditer(r'data-type="actor"[^>]*data-id="([^"]*)"', section_html):
            actor_kinds[act.group(1)] = "actor"
        for p in re.finditer(r'data-type="participant"[^>]*data-id="([^"]*)"', section_html):
            if p.group(1) not in actor_kinds:
                actor_kinds[p.group(1)] = "participant"

        participant_positions: dict[str, float] = {}
        for lm in re.finditer(r'<line[^>]*?(?:class="[^"]*actor-line[^"]*"|data-et="life-line")[^>]*?>', section_html):
            tag = lm.group(0)
            x_m = re.search(r'x1="([\d.]+)"', tag)
            name_m = re.search(r'(?:name|data-id)="([^"]*)"', tag)
            id_m = re.search(r'id="actor(\d+)"', tag)
            if name_m:
                name_val = name_m.group(1)
                if id_m:
                    pos = float(id_m.group(1))
                elif x_m:
                    pos = float(x_m.group(1))
                else:
                    pos = 0.0
                participant_positions[name_val] = pos

        if not participant_positions:
            for tm in re.finditer(r'<text[^>]*x="([\d.]+)"[^>]*class="[^"]*actor[^"]*"[^>]*>([\s\S]*?)</text>', section_html):
                x_val = float(tm.group(1))
                txt_val = re.sub(r'<[^>]+>', '', tm.group(2)).strip()
                if txt_val and txt_val not in participant_positions:
                    participant_positions[txt_val] = x_val

        all_participants = list(actor_kinds.keys())
        all_participants.sort(key=lambda name: participant_positions.get(name, 9999.0))

        for name in all_participants:
            kind = actor_kinds.get(name, "participant")
            lines.append(f"    {kind} {name}")

        msgs = []
        for lm in re.finditer(r'<line[^>]*class="([^"]*)"[^>]*data-from="([^"]*)"[^>]*data-to="([^"]*)"', section_html):
            cls, frm, to = lm.group(1), lm.group(2), lm.group(3)
            arrow = "-->>" if "messageLine1" in cls else "->>"
            msgs.append((frm, arrow, to))

        texts = re.findall(r'<text[^>]*class="messageText"[^>]*>([\s\S]*?)</text>', section_html)
        if not texts:
            all_texts = [re.sub(r'<[^>]+>', ' ', t).strip() for t in re.findall(r'<text[^>]*>([\s\S]*?)</text>', section_html)]
            msg_texts = [t for t in all_texts if t not in set(all_participants)]
        else:
            msg_texts = [re.sub(r'<[^>]+>', ' ', t).strip() for t in texts]

        for i, (frm, arrow, to) in enumerate(msgs):
            txt = msg_texts[i] if i < len(msg_texts) else ""
            lines.append(f"    {frm}{arrow}{to}: {txt}")
        return "\n".join(lines)

    if "class" in role:
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
            '    User "1" --> "*" Order : places',
        ]
        return "\n".join(lines)

    if "er" in role or "erDiagram" in section_html:
        lines = ["erDiagram"]

        entity_matches = list(re.finditer(r'<g[^>]*id="[^"]*?-entity-([A-Za-z0-9_]+)-\d+"[^>]*>', section_html))
        entities_data: dict[str, list[str]] = {}

        for i, em in enumerate(entity_matches):
            ename = em.group(1)
            start_pos = em.start()
            next_pos = entity_matches[i + 1].start() if i + 1 < len(entity_matches) else section_html.find('class="edges edgePaths"')
            if next_pos == -1 or next_pos < start_pos:
                next_pos = section_html.find('</svg>', start_pos)
            chunk = section_html[start_pos:next_pos]

            types = [re.sub(r'<[^>]+>', '', t).strip() for t in re.findall(r'<g class="label attribute-type"[^>]*>[\s\S]*?<text[^>]*>([\s\S]*?)</text>', chunk)]
            names = [re.sub(r'<[^>]+>', '', t).strip() for t in re.findall(r'<g class="label attribute-name"[^>]*>[\s\S]*?<text[^>]*>([\s\S]*?)</text>', chunk)]
            keys = [re.sub(r'<[^>]+>', '', t).strip() for t in re.findall(r'<g class="label attribute-keys"[^>]*>[\s\S]*?<text[^>]*>([\s\S]*?)</text>', chunk)]
            comments = [re.sub(r'<[^>]+>', '', t).strip() for t in re.findall(r'<g class="label attribute-comment"[^>]*>[\s\S]*?<text[^>]*>([\s\S]*?)</text>', chunk)]

            attr_lines = []
            for j in range(max(len(types), len(names))):
                t = types[j] if j < len(types) else ""
                n = names[j] if j < len(names) else ""
                k = keys[j] if j < len(keys) else ""
                c = comments[j] if j < len(comments) else ""
                parts = [p for p in [t, n, k, f'"{c}"' if c else ""] if p]
                if parts:
                    attr_lines.append("        " + " ".join(parts))

            entities_data[ename] = attr_lines

        for ename, attrs in entities_data.items():
            if attrs:
                lines.append(f"    {ename} {{")
                lines.extend(attrs)
                lines.append("    }")

        marker_map_start = {
            "onlyOneStart": "||",
            "zeroOrOneStart": "|o",
            "zeroOrMoreStart": "}o",
            "oneOrMoreStart": "}|",
        }
        marker_map_end = {
            "onlyOneEnd": "||",
            "zeroOrOneEnd": "o|",
            "zeroOrMoreEnd": "o{",
            "oneOrMoreEnd": "|{",
        }

        edge_labels: dict[str, str] = {}
        for lm in re.finditer(r'<g class="label"[^>]*data-id="([^"]+)"[^>]*>[\s\S]*?<text[^>]*>([\s\S]*?)</text>', section_html):
            eid = lm.group(1)
            ltxt = re.sub(r'<[^>]+>', '', lm.group(2)).strip()
            if ltxt:
                edge_labels[eid] = ltxt

        for pm in re.finditer(r'<path[^>]*data-id="([^"]*id_entity-([A-Za-z0-9_]+)-\d+_entity-([A-Za-z0-9_]+)-\d+_\d+)"[^>]*marker-start="([^"]*)"[^>]*marker-end="([^"]*)"', section_html):
            full_eid = pm.group(1)
            src = pm.group(2)
            dst = pm.group(3)
            m_start_raw = pm.group(4)
            m_end_raw = pm.group(5)

            start_sym = "--"
            for k, v in marker_map_start.items():
                if k in m_start_raw:
                    start_sym = v
                    break

            end_sym = "--"
            for k, v in marker_map_end.items():
                if k in m_end_raw:
                    end_sym = v
                    break

            label = edge_labels.get(full_eid, "")
            if label:
                lines.append(f"    {src} {start_sym}--{end_sym} {dst} : {label}")
            else:
                lines.append(f"    {src} {start_sym}--{end_sym} {dst}")

        return "\n".join(lines)

    return None


class ChatGPTMarkdownConverter(BaseMarkdownConverter):
    """Specialized Markdown converter for ChatGPT's React & CodeMirror DOM components."""

    def __init__(self) -> None:
        super().__init__()
        self._format_depth = 0
        self._format_stack: list[tuple[int, str, list[str]]] = []

    @staticmethod
    def _extract_assistant_container_if_full_page(full_html: str) -> str:
        is_full_page = (
            "<nav" in full_html
            or "<body" in full_html
            or "<!DOCTYPE" in full_html
            or "Skip to content" in full_html
            or "history-sidebar" in full_html
        )
        if not is_full_page:
            return full_html

        # Prefer full assistant turn container which includes both markdown text and generated images
        asst_matches = list(re.finditer(r'<div[^>]*data-message-author-role="assistant"[^>]*>', full_html))
        if asst_matches:
            target_match = asst_matches[-1]
        else:
            matches = list(re.finditer(r'<div[^>]*data-markdown-text-style="assistant-message"[^>]*>', full_html))
            if not matches:
                matches = list(re.finditer(r'<div[^>]*class="[^"]*MarkdownRoot[^"]*"[^>]*>', full_html))
            if not matches:
                return full_html

            # Prefer non-tertiary assistant message containers (reasoning models produce tertiary thinking pills)
            non_tertiary = [m for m in matches if 'data-markdown-text-tone="tertiary"' not in m.group(0)]
            target_match = non_tertiary[-1] if non_tertiary else matches[-1]

        start_tag_end = target_match.end()
        depth = 1
        pos = start_tag_end
        tag_regex = re.compile(r'</?div[^>]*>', re.IGNORECASE)
        while depth > 0 and pos < len(full_html):
            m = tag_regex.search(full_html, pos)
            if not m:
                break
            tag_str = m.group(0)
            pos = m.end()
            if tag_str.startswith('</'):
                depth -= 1
            elif not tag_str.endswith('/>'):
                depth += 1

        if depth == 0:
            return full_html[start_tag_end:pos - len('</div>')]
        return full_html[start_tag_end:]

    def is_skip_tag(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if super().is_skip_tag(tag, attr_map, cls):
            return True
        # Skip reasoning / thinking containers so they don't leak into final answer text
        if attr_map.get("data-markdown-text-tone") == "tertiary":
            return True
        if "thought" in (attr_map.get("data-testid") or "").lower():
            return True
        if tag == "button" and not self._raw_html_stack:
            # Preserve checkbox buttons used for checklists and task lists
            if (
                attr_map.get("role") == "checkbox"
                or attr_map.get("data-d-component") == "checkbox"
                or attr_map.get("type") == "checkbox"
                or "Checkbox-" in cls
            ):
                return False
            # Skip action buttons (copy, thumbs up, share, audio, etc.)
            aria_lbl = (attr_map.get("aria-label") or "").lower()
            tid = (attr_map.get("data-testid") or "").lower()
            if (
                "copy" in aria_lbl
                or "copy" in tid
                or "thumbs" in aria_lbl
                or "good response" in aria_lbl
                or "bad response" in aria_lbl
                or "read aloud" in aria_lbl
                or "regenerate" in aria_lbl
                or "more actions" in aria_lbl
                or "skip" in aria_lbl
                or "skip" in tid
                or "thought" in aria_lbl
                or "thinking" in aria_lbl
                or "worked for" in aria_lbl
            ):
                return True
        return False

    def preprocess_html(self, html: str) -> str:
        """Preprocess rendered Mermaid diagrams and clean components."""
        html = self._extract_assistant_container_if_full_page(html)

        pattern = re.compile(r'<div[^>]*data-chatgpt-mermaid-preview=""[\s\S]*?</svg>[\s\S]*?</div>\s*</div>\s*</div>')

        def repl(m: re.Match) -> str:
            chunk = m.group(0)
            code = extract_chatgpt_mermaid(chunk)
            if code:
                return f'\n\n<pre><code class="language-mermaid">\n{code}\n</code></pre>\n\n'
            return chunk

        return pattern.sub(repl, html)

    def is_raw_html_block_start(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        if super().is_raw_html_block_start(tag, attr_map, cls):
            return True
        # Standalone HTML UI components, calculators, tools, and custom layout rows
        comp = attr_map.get("data-d-component")
        if comp in {"box", "row", "grid", "slider", "radio-group", "calculator", "tool", "interactive", "form"}:
            return True
        if "Box-" in cls and (comp or attr_map.get("data-d-direction")):
            return True
        return False

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
        attr_map = {k: (v or "") for k, v in attrs}
        cls = attr_map.get("class", "")

        # If inside raw HTML block or icon, or starting one, delegate directly to super()
        if (
            self._raw_html_stack
            or self._icon_stack
            or self.is_raw_html_block_start(tag, attr_map, cls)
            or self.is_icon_start(tag, attr_map, cls)
        ):
            super().handle_starttag(tag, attrs)
            return

        self._format_depth += 1

        # Dividers / Horizontal rules
        if attr_map.get("data-d-component") == "divider" or "Divider-" in cls:
            self._at_li_start = False
            self.parts.append("\n\n---\n\n")
            return

        styles_started = []
        if not self._in_code:
            if attr_map.get("data-d-font-style") == "italic":
                styles_started.append("italic")
                self._emit("*")
            if attr_map.get("data-d-text-decoration") == "line-through":
                styles_started.append("strikethrough")
                self._emit("~~")
            if attr_map.get("data-d-text-decoration") == "underline" and tag not in {"u", "ins"}:
                styles_started.append("underline")
                self._emit("<u>")
            is_bold = (
                "data-d-default-strong" in attr_map
                or attr_map.get("data-d-weight") in {"semibold", "bold"}
            ) and (
                "Title-" not in cls
                and "heading" not in cls
                and tag not in {"h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"}
            )
            if is_bold:
                if (
                    attr_map.get("data-d-inline") is not None
                    or tag == "span"
                    or "data-d-default-strong" in attr_map
                ):
                    styles_started.append("bold")
                    self._emit("**")

        if styles_started:
            self._format_stack.append((self._format_depth, tag, styles_started))

        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._raw_html_stack or self._icon_stack:
            super().handle_endtag(tag)
            return
        if (
            self._format_stack
            and self._format_stack[-1][0] == self._format_depth
            and self._format_stack[-1][1] == tag
        ):
            _, _, styles = self._format_stack.pop()
            for s in reversed(styles):
                if s == "italic":
                    self._emit("*")
                elif s == "strikethrough":
                    self._emit("~~")
                elif s == "underline":
                    self._emit("</u>")
                elif s == "bold":
                    self._emit("**")

        self._format_depth = max(0, self._format_depth - 1)
        super().handle_endtag(tag)

    def postprocess_markdown(self, markdown: str) -> str:
        cleaned = super().postprocess_markdown(markdown)

        # Convert standalone multiline `\[ ... \]` or \`\[ ... \]\` code blocks to ```latex
        def convert_bracket_latex(m: re.Match) -> str:
            inner = m.group(1).strip()
            return f"\n\n```latex\n\\[\n{inner}\n\\]\n```\n\n"

        cleaned = re.sub(r'\\?`\\\[([^\r\n]*[\r\n][^`]*?)\\\]\\?`', convert_bracket_latex, cleaned)

        # Clean accidental double-escaped stars
        cleaned = cleaned.replace(r"\**", r"\*").replace(r"*\* ", r"\* ").replace(r"*\*", r"\*")

        while "\n\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n\n", "\n\n\n")

        return cleaned.strip()
