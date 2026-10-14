from __future__ import annotations

from html.parser import HTMLParser
from typing import Any, Iterable

from app.adapters.base import Source
from app.browser.converters import (
    BaseMarkdownConverter,
    ChatGPTMarkdownConverter,
    clean_markdown_text,
    get_converter,
    html_to_markdown,
)
from app.browser.converters.base import _SKIP_TAGS, extract_citation_urls

# Alias for backward compatibility with internal scripts/tests
_MarkdownRenderer = BaseMarkdownConverter
_extract_citation_urls = extract_citation_urls


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
                items = extract_citation_urls(attr_map)
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


def normalize_sources(pairs: Iterable[tuple[str, str | None] | tuple[str, str | None, str | None] | Any]) -> list[Source]:
    """Dedupe by URL, keep first title and snippet seen, drop non-http(s) URLs."""
    seen: set[str] = set()
    sources: list[Source] = []
    for item in pairs:
        if isinstance(item, (tuple, list)):
            if len(item) < 1:
                continue
            url = item[0]
            title = item[1] if len(item) > 1 else None
            snippet = item[2] if len(item) > 2 else None
        else:
            continue
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url.startswith(("https://", "http://")) or url in seen:
            continue
        seen.add(url)
        sources.append(
            Source(
                url=url,
                title=(title.strip() if isinstance(title, str) and title else None) or None,
                snippet=(snippet.strip() if isinstance(snippet, str) and snippet else None) or None,
            )
        )
    return sources
