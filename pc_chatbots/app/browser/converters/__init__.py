from __future__ import annotations

from app.browser.converters.base import BaseMarkdownConverter
from app.browser.converters.chatgpt import ChatGPTMarkdownConverter
from app.browser.converters.copilot import CopilotMarkdownConverter
from app.browser.converters.registry import get_converter, register_converter


def html_to_markdown(html: str, provider: str | None = None) -> str:
    """Convert an HTML fragment to readable Markdown for a specific provider.
    
    Never raises on bad input. Falls back gracefully to raw text.
    """
    if not html or not html.strip():
        return ""
    converter = get_converter(provider)
    return converter.convert(html)


def clean_markdown_text(text: str) -> str:
    """Filter out empty list items and trim unnecessary lines inside code blocks."""
    if not text:
        return ""
    converter = BaseMarkdownConverter()
    return converter.default_cleanup(text)


__all__ = [
    "BaseMarkdownConverter",
    "ChatGPTMarkdownConverter",
    "CopilotMarkdownConverter",
    "clean_markdown_text",
    "get_converter",
    "html_to_markdown",
    "register_converter",
]
