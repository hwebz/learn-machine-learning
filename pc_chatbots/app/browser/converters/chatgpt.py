from __future__ import annotations

import re
from typing import Any
from app.browser.converters.base import BaseMarkdownConverter


class ChatGPTMarkdownConverter(BaseMarkdownConverter):
    """Specialized Markdown converter for ChatGPT's React & CodeMirror DOM components."""

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
        # Note: We do NOT skip the entire [data-markdown-copy="exclude"] container
        # because ChatGPT places the language name (.truncate) inside it.
        # Instead, buttons, svgs, and copy actions are filtered.
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

    def postprocess_markdown(self, markdown: str) -> str:
        cleaned = super().postprocess_markdown(markdown)

        # Convert standalone multiline `\[ ... \]` code blocks to ```latex
        # Only match if there are no intermediate backticks AND it contains multiline formula content
        def convert_bracket_latex(m: re.Match) -> str:
            inner = m.group(1).strip()
            return f"\n\n```latex\n\\[\n{inner}\n\\]\n```\n\n"

        cleaned = re.sub(r'`\\\[([^`\r\n]*[\r\n][^`]*?)\\\]`', convert_bracket_latex, cleaned)

        while "\n\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n\n", "\n\n\n")

        return cleaned.strip()
