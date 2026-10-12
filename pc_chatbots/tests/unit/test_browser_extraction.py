from __future__ import annotations

import pytest

from app.browser.extraction import (
    clean_markdown_text,
    extract_source_links,
    html_to_markdown,
    normalize_sources,
)


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
    lines = [line.strip() for line in md.splitlines()]
    # There should not be an empty "-" or "1." line
    assert "-" not in lines
    assert "1." not in lines


def test_html_to_markdown_ordered_and_nested_paragraphs() -> None:
    html = """
    <h3>Heading</h3>
    <ol>
      <li><p><strong>First point</strong></p><p>Details about point</p></li>
      <li>Second point</li>
    </ol>
    """
    md = html_to_markdown(html)
    lines = [line.strip() for line in md.splitlines() if line.strip()]
    assert "1." not in lines
    assert any(line.startswith("1. **First point**") for line in lines)
    assert any(line.startswith("2. Second point") for line in lines)


def test_html_to_markdown_code_and_blockquote() -> None:
    html = "<pre><code>print('hi')</code></pre><blockquote>Quote</blockquote>"
    md = html_to_markdown(html)
    assert "```" in md
    assert "print('hi')" in md
    assert "> Quote" in md


def test_html_to_markdown_blockquote_paragraphs_and_nested() -> None:
    # 1. Multiple paragraphs inside blockquote
    html_p = "<blockquote><p>First paragraph</p><p>Second paragraph</p></blockquote>"
    md_p = html_to_markdown(html_p)
    lines_p = [line.strip() for line in md_p.splitlines() if line.strip()]
    assert lines_p == ["> First paragraph", ">", "> Second paragraph"]

    # 2. Blockquote with line breaks and formatting
    html_br = "<blockquote>Line 1<br>Line 2<br><br><strong>Bold quote</strong></blockquote>"
    md_br = html_to_markdown(html_br)
    assert "> Line 1" in md_br
    assert "> Line 2" in md_br
    assert "> **Bold quote**" in md_br

    # 3. Nested blockquotes
    html_nested = "<blockquote><p>Outer</p><blockquote><p>Inner</p></blockquote></blockquote>"
    md_nested = html_to_markdown(html_nested)
    assert "> Outer" in md_nested
    assert "> > Inner" in md_nested


def test_html_to_markdown_copilot_fai_bebop_citation() -> None:
    html = (
        '<p>This is a paragraph with factual info.<button type="button" class="fai-BebopCitation r1blrj54" '
        'data-grouped-citations="[{&quot;url&quot;:&quot;https://example.com/source1&quot;,&quot;name&quot;:&quot;example.com&quot;}]" '
        'aria-label="Citation: example — Example Source Title">'
        '<span class="fai-BebopCitation__content"><span class="fai-BebopCitation__text">example</span></span>'
        '</button></p>'
    )
    md = html_to_markdown(html)
    assert "[example.com](https://example.com/source1)" in md
    assert "This is a paragraph with factual info. [example.com](https://example.com/source1)" in md

    # Also test extract_source_links
    links = extract_source_links(html)
    assert len(links) == 1
    assert links[0][0] == "https://example.com/source1"
    assert "Example Source Title" in (links[0][1] or "")


def test_html_to_markdown_copilot_multi_citations() -> None:
    html = (
        '<p>Here are recent AI breakthroughs.'
        '<button type="button" class="fai-BebopCitation" '
        'data-grouped-citations="[{&quot;index&quot;:&quot;5-dbdc2c&quot;,&quot;occurrence&quot;:1,&quot;url&quot;:&quot;https://www.explainx.ai/news&quot;,&quot;name&quot;:&quot;explainx.ai&quot;},'
        '{&quot;index&quot;:&quot;6-7f797a&quot;,&quot;occurrence&quot;:1,&quot;url&quot;:&quot;https://www.volanea.com/blog/ai-breakthroughs-october-2026&quot;,&quot;name&quot;:&quot;volanea.com&quot;}]" '
        'aria-label="Citation: explainx — AI News Today plus 1 more">'
        '<span class="fai-BebopCitation__content"><span class="fai-BebopCitation__text">explainx</span><span class="fai-BebopCitation__overflowCount">+1</span></span>'
        '</button></p>'
    )
    md = html_to_markdown(html)
    assert "[explainx.ai](https://www.explainx.ai/news)" in md
    assert "[volanea.com](https://www.volanea.com/blog/ai-breakthroughs-october-2026)" in md
    # Ensure raw_text ("explainx+1") was NOT duplicated across both links
    assert "explainx+1" not in md
    assert md == "Here are recent AI breakthroughs. [explainx.ai](https://www.explainx.ai/news) [volanea.com](https://www.volanea.com/blog/ai-breakthroughs-october-2026)"

    # Also test extract_source_links
    links = extract_source_links(html)
    assert len(links) == 2
    assert links[0] == ("https://www.explainx.ai/news", "explainx.ai")
    assert links[1] == ("https://www.volanea.com/blog/ai-breakthroughs-october-2026", "volanea.com")


def test_html_to_markdown_scriptor_code_block() -> None:
    html = (
        '<p>Before code</p>'
        '<div tabindex="-1" class="scriptor-component-code-block scriptor-codeblock-virtualized">'
        '<div data-testid="one-copilot-code-identity"><svg></svg><span>Python</span></div>'
        '<button type="button" id="copy-button"><span>Copy code</span></button>'
        '<div role="textbox" aria-label="Code editor">'
        '<div data-line-number="1"></div>'
        '<div data-line-index="0">def add(a, b):</div>'
        '<div data-line-number="2"></div>'
        '<div data-line-index="1">    return a + b</div>'
        '</div></div>'
        '<p>After code</p>'
    )
    md = html_to_markdown(html)
    assert "Before code" in md
    assert "After code" in md
    assert "Copy code" not in md
    assert "```python\ndef add(a, b):\n    return a + b\n```" in md


def test_html_to_markdown_scriptor_plain_text_virtualized() -> None:
    html = (
        '<div class="scriptor-codeblock-virtualized">'
        '<div class="code-identity"><span>Plain Text</span></div>'
        '<button id="copy-button">Copy</button>'
        '<div role="textbox">'
        '<div data-line-number="1"></div>'
        '<div data-line-index="0">Input Layer</div>'
        '<div data-line-number="2"></div>'
        '<div data-line-index="1">      ↓</div>'
        '<div data-line-number="3"></div>'
        '<div data-line-index="2">Output Layer</div>'
        '</div></div>'
    )
    md = html_to_markdown(html)
    assert "Copy" not in md
    assert "Plain Text" not in md
    assert "```\nInput Layer\n      ↓\nOutput Layer\n```" in md


def test_html_to_markdown_qwen_monaco_code_block() -> None:
    html = (
        '<pre class="qwen-markdown-code" dir="ltr">'
        '<div class="qwen-markdown-code-header-wrapper">'
        '<div class="qwen-markdown-code-header"><div>html</div>'
        '<div class="qwen-markdown-code-header-actions"><button type="button"><span>Copy code</span></button></div>'
        '</div></div>'
        '<div class="monaco-editor">'
        '<div class="margin"><div class="line-numbers">1</div><div class="line-numbers">2</div><div class="line-numbers">3</div></div>'
        '<div class="view-lines">'
        '<div class="view-line"><span>&lt;!DOCTYPE html&gt;</span></div>'
        '<div class="view-line"><span>&lt;html&gt;</span></div>'
        '<div class="view-line"><span>&lt;/html&gt;</span></div>'
        '</div></div></pre>'
    )
    md = html_to_markdown(html)
    # Line numbers must not be present
    lines = md.splitlines()
    assert "1" not in lines
    assert "2" not in lines
    assert "3" not in lines
    assert "Copy code" not in md
    # Header language should not appear inside code text
    expected = "```html\n<!DOCTYPE html>\n<html>\n</html>\n```"
    assert expected in md


def test_html_to_markdown_trims_extra_blank_lines() -> None:
    html = (
        '<pre><code class="language-html">\n'
        '&lt;!DOCTYPE html&gt;\n\n'
        '&lt;html lang="en"&gt;\n\n'
        '&lt;head&gt;\n\n'
        '    &lt;title&gt;Hello&lt;/title&gt;\n\n'
        '&lt;/head&gt;\n\n'
        '&lt;body&gt;\n\n'
        '    &lt;h1&gt;Hello&lt;/h1&gt;\n\n'
        '&lt;/body&gt;\n\n'
        '&lt;/html&gt;\n'
        '</code></pre>'
    )
    md = html_to_markdown(html)
    expected = (
        "```html\n"
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        "    <title>Hello</title>\n"
        "</head>\n"
        "<body>\n"
        "    <h1>Hello</h1>\n"
        "</body>\n"
        "</html>\n"
        "```"
    )
    assert expected in md


def test_html_to_markdown_preserves_intentional_blank_line() -> None:
    html = (
        '<pre><code class="language-python">\n'
        'def add(a, b):\n'
        '    return a + b\n\n'
        'def sub(a, b):\n'
        '    return a - b\n'
        '</code></pre>'
    )
    md = html_to_markdown(html)
    expected = (
        "```python\n"
        "def add(a, b):\n"
        "    return a + b\n\n"
        "def sub(a, b):\n"
        "    return a - b\n"
        "```"
    )
    assert expected in md


def test_html_to_markdown_qwen_codespan_inline_not_block() -> None:
    html = '<p>Inline code <code class="qwen-markdown-codespan">pip install package</code> here.</p>'
    md = html_to_markdown(html)
    assert "`pip install package`" in md
    assert "```" not in md


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


def test_html_to_markdown_removes_double_backticks_at_end_of_code_block() -> None:
    html = (
        '<div class="scriptor-component-code-block scriptor-codeblock-virtualized">'
        '<div data-testid="one-copilot-code-identity"><span>Python</span></div>'
        '<div role="textbox">'
        '<div data-line-number="1"></div>'
        '<div data-line-index="0">print("Hello, World!")</div>'
        '<div data-line-number="2"></div>'
        '<div data-line-index="1">``</div>'
        '</div></div>'
    )
    md = html_to_markdown(html)
    assert md == '```python\nprint("Hello, World!")\n```'


def test_clean_markdown_text_removes_double_backticks() -> None:
    raw_md = '```python\nprint("Hello, World!")\n``\n```'
    cleaned = clean_markdown_text(raw_md)
    assert cleaned == '```python\nprint("Hello, World!")\n```'


def test_html_to_markdown_gemini_math_block_and_inline() -> None:
    html = (
        '<p>Given formula:</p>'
        '<div class="math-block" data-math="\\theta_{t+1} = \\theta_t - \\alpha \\nabla J(\\theta_t)">'
        '<span class="katex-display"><span class="katex"><span class="katex-html">duplicate visual text</span></span></span>'
        '</div>'
        '<p>where <span class="math-inline" data-math="\\alpha"><span class="katex"><span class="katex-html">a</span></span></span> is learning rate.</p>'
    )
    md = html_to_markdown(html)
    assert "$$\n\\theta_{t+1} = \\theta_t - \\alpha \\nabla J(\\theta_t)\n$$" in md
    assert "$\\alpha$" in md
    assert "duplicate visual text" not in md


def test_html_to_markdown_katex_display_with_annotation() -> None:
    html = (
        '<p>Pythagorean theorem:</p>'
        '<span class="katex-display">'
        '<span class="katex">'
        '<span class="katex-mathml"><math><semantics><mrow><mi>a</mi></mrow>'
        '<annotation encoding="application/x-tex">a^2 + b^2 = c^2</annotation>'
        '</semantics></math></span>'
        '<span class="katex-html" aria-hidden="true"><span class="base">a2+b2=c2</span></span>'
        '</span></span>'
    )
    md = html_to_markdown(html)
    assert "$$\na^2 + b^2 = c^2\n$$" in md
    assert "a2+b2=c2" not in md