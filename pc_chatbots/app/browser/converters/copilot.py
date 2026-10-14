from __future__ import annotations

import re
from typing import Any
from app.browser.converters.base import BaseMarkdownConverter


class CopilotMarkdownConverter(BaseMarkdownConverter):
    """Custom Markdown converter tailored for Microsoft 365 Copilot DOM outputs.
    
    Handles:
    - Inline citations from `fai-BebopCitation` buttons with `data-grouped-citations`.
    - Virtualized and standard `scriptor` code blocks (`scriptor-component-code-block`).
    - Fluent UI table structures and Adaptive Card elements.
    - Stripping response buttons (Copy Response, feedback buttons).
    - Post-processing citation deduplication and formatting normalization.
    """

    def is_skip_tag(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Skip Copilot action buttons (like Copy button, feedback, retry) and standard skip tags."""
        btn_id = attr_map.get("id", "")
        test_id = attr_map.get("data-testid", "")
        aria = attr_map.get("aria-label", "").lower()
        if (
            btn_id in {"copy-button", "CopyButtonTestId", "moreButton"}
            or test_id in {"CopyButtonTestId", "copy-button"}
            or "copy code" in aria
            or aria in {"copy response", "copy"}
            or "feedback" in cls.lower()
        ):
            return True
        return super().is_skip_tag(tag, attr_map, cls)

    def is_code_block_start(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Identify Copilot's scriptor code block containers."""
        if (
            "scriptor-component-code-block" in cls
            or "scriptor-codeblock-virtualized" in cls
            or "scriptor-codeblock" in cls
        ):
            return True
        return super().is_code_block_start(tag, attr_map, cls)

    def extract_code_lang(self, tag: str, attr_map: dict[str, str], cls: str) -> str | None:
        """Extract language identifier from Copilot scriptor identity elements."""
        lang = attr_map.get("data-language") or attr_map.get("data-mode-id")
        if lang:
            return self._normalize_lang(lang)
        return super().extract_code_lang(tag, attr_map, cls)

    def is_code_header_lang(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Detect Copilot's codeblock header containing the language name."""
        if (
            attr_map.get("data-testid") == "one-copilot-code-identity"
            or "code-identity" in cls
            or "scriptor-codeblock-header" in cls
        ):
            return True
        return super().is_code_header_lang(tag, attr_map, cls)

    def is_line_number_element(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Detect and ignore line number elements in Copilot scriptor blocks."""
        if "data-line-number" in attr_map:
            return True
        return super().is_line_number_element(tag, attr_map, cls)

    def is_code_line_element(self, tag: str, attr_map: dict[str, str], cls: str) -> bool:
        """Detect code line rows in Copilot scriptor blocks."""
        if "data-line-index" in attr_map:
            return True
        return super().is_code_line_element(tag, attr_map, cls)

    def postprocess_markdown(self, markdown: str) -> str:
        """Refine Markdown output from Copilot."""
        cleaned = super().postprocess_markdown(markdown)

        # Remove duplicate adjacent citations (e.g. [foo](url) [foo](url))
        cleaned = re.sub(r'(\[[^\]]+\]\([^\)]+\))\s+\1', r'\1', cleaned)

        # Clean LaTeX if multiline brackets were escaped
        def convert_bracket_latex(m: re.Match) -> str:
            inner = m.group(1).strip()
            return f"\n\n```latex\n\\[\n{inner}\n\\]\n```\n\n"

        cleaned = re.sub(r'\\?`\\\[([^\r\n]*[\r\n][^`]*?)\\\]\\?`', convert_bracket_latex, cleaned)

        while "\n\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n\n", "\n\n\n")

        return cleaned.strip()
