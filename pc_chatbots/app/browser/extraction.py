from __future__ import annotations

from html.parser import HTMLParser
from typing import Any, Iterable

from app.adapters.base import Source

_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "tr"}
_SKIP_TAGS = {"script", "style", "noscript", "svg"}
_HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
_LIST_MARK = {"ul": "- ", "ol": "1. "}


class _MarkdownRenderer(HTMLParser):
    """Minimal HTML→Markdown converter (stdlib only, no extra dependencies)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._list_stack: list[str] = []
        self._in_pre = False
        self._in_code = False
        self._href_stack: list[str | None] = []
        self._link_text: list[str] | None = None
        self._skip_depth = 0

    def _emit(self, text: str) -> None:
        if self._link_text is not None:
            self._link_text.append(text)
        else:
            self.parts.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attr_map = {k: (v or "") for k, v in attrs}
        if tag in _HEADING:
            self.parts.append("\n\n" + _HEADING[tag] + " ")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "hr":
            self.parts.append("\n\n---\n\n")
        elif tag in _LIST_MARK:
            self._list_stack.append(tag)
            self.parts.append("\n" + _LIST_MARK[tag])
        elif tag in {"li"}:
            if self._list_stack:
                self.parts.append("\n" + _LIST_MARK[self._list_stack[-1]])
            else:
                self.parts.append("\n- ")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "blockquote":
            self.parts.append("\n\n> ")
        elif tag == "pre":
            self._in_pre = True
            self.parts.append("\n\n```\n")
        elif tag in {"code", "tt"}:
            if not self._in_pre:
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
        if tag in _HEADING:
            self.parts.append("\n\n")
        elif tag in _LIST_MARK:
            if self._list_stack:
                self._list_stack.pop()
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "blockquote":
            self.parts.append("\n\n")
        elif tag == "pre":
            self._in_pre = False
            self.parts.append("\n```\n\n")
        elif tag in {"code", "tt"}:
            if not self._in_pre and self._in_code:
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
        if self._in_pre:
            self.parts.append(data)
        else:
            self._emit(data)

    def markdown(self) -> str:
        raw = "".join(self.parts)
        lines = [line.rstrip() for line in raw.splitlines()]
        text = "\n".join(lines)
        while "\n\n\n\n" in text:
            text = text.replace("\n\n\n\n", "\n\n\n")
        return text.strip()


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
        if tag == "a" and not self._skip_depth:
            attr_map = {k: (v or "") for k, v in attrs}
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
