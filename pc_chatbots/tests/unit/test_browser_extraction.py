from __future__ import annotations

import pytest

from app.browser.extraction import extract_source_links, html_to_markdown, normalize_sources


def test_html_to_markdown_basic() -> None:
    html = "<p>Hello <strong>world</strong>.</p>"
    md = html_to_markdown(html)
    assert "Hello **world**." in md


def test_html_to_markdown_headings_and_lists() -> None:
    html = "<h1>Title</h1><ul><li>One</li><li>Two</li></ul>"
    md = html_to_markdown(html)
    assert "# Title" in md
    assert "- One" in md
    assert "- Two" in md


def test_html_to_markdown_code_and_blockquote() -> None:
    html = "<pre><code>print('hi')</code></pre><blockquote>Quote</blockquote>"
    md = html_to_markdown(html)
    assert "```" in md
    assert "print('hi')" in md
    assert "> Quote" in md


def test_html_to_markdown_empty_and_malformed() -> None:
    assert html_to_markdown("") == ""
    assert html_to_markdown("plain text") == "plain text"
    assert html_to_markdown("<div><span>unclosed")  # should not raise


def test_extract_source_links_dedupes_by_url() -> None:
    html = (
        '<a href="https://example.com/a">Title A</a>'
        '<a href="https://example.com/b">Title B</a>'
        '<a href="https://example.com/a">Title A Again</a>'
        '<a href="not-http">ignored</a>'
    )
    pairs = extract_source_links(html)
    sources = normalize_sources(pairs)
    assert len(sources) == 2
    urls = {str(s.url) for s in sources}
    assert "https://example.com/a" in urls
    assert "https://example.com/b" in urls


def test_normalize_sources_drops_non_http() -> None:
    pairs = [
        ("https://a.com", "A"),
        ("http://b.com", "B"),
        ("ftp://c.com", "C"),
        ("javascript:void(0)", "D"),
    ]
    sources = normalize_sources(pairs)
    urls = {str(s.url).rstrip("/") for s in sources}
    assert urls == {"https://a.com", "http://b.com"}


@pytest.mark.asyncio
async def test_normalize_sources_keeps_first_title() -> None:
    pairs = [("https://dup.com", "First"), ("https://dup.com", "Second")]
    sources = normalize_sources(pairs)
    assert len(sources) == 1
    assert sources[0].title == "First"