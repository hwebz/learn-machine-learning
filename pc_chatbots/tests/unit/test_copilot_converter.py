from __future__ import annotations

import pytest

from app.browser.converters import (
    BaseMarkdownConverter,
    CopilotMarkdownConverter,
    get_converter,
    html_to_markdown,
)


def test_copilot_converter_factory() -> None:
    conv = get_converter("copilot")
    assert isinstance(conv, CopilotMarkdownConverter)

    ms = get_converter("microsoft")
    assert isinstance(ms, CopilotMarkdownConverter)

    m365 = get_converter("m365")
    assert isinstance(m365, CopilotMarkdownConverter)


def test_copilot_fai_bebop_single_citation() -> None:
    html = (
        '<p>This is a paragraph with factual info.<button type="button" class="fai-BebopCitation r1blrj54" '
        'data-grouped-citations="[{&quot;url&quot;:&quot;https://example.com/source1&quot;,&quot;name&quot;:&quot;example.com&quot;}]" '
        'aria-label="Citation: example — Example Source Title">'
        '<span class="fai-BebopCitation__content"><span class="fai-BebopCitation__text">example</span></span>'
        '</button></p>'
    )
    md = html_to_markdown(html, provider="copilot")
    assert "[example.com](https://example.com/source1)" in md
    assert "This is a paragraph with factual info. [example.com](https://example.com/source1)" in md


def test_copilot_fai_bebop_multi_citations() -> None:
    html = (
        '<p>Here are recent AI breakthroughs.'
        '<button type="button" class="fai-BebopCitation" '
        'data-grouped-citations="[{&quot;index&quot;:&quot;5-dbdc2c&quot;,&quot;occurrence&quot;:1,&quot;url&quot;:&quot;https://www.explainx.ai/news&quot;,&quot;name&quot;:&quot;explainx.ai&quot;},'
        '{&quot;index&quot;:&quot;6-7f797a&quot;,&quot;occurrence&quot;:1,&quot;url&quot;:&quot;https://www.volanea.com/blog/ai-breakthroughs-october-2026&quot;,&quot;name&quot;:&quot;volanea.com&quot;}]" '
        'aria-label="Citation: explainx — AI News Today plus 1 more">'
        '<span class="fai-BebopCitation__content"><span class="fai-BebopCitation__text">explainx</span><span class="fai-BebopCitation__overflowCount">+1</span></span>'
        '</button></p>'
    )
    md = html_to_markdown(html, provider="copilot")
    assert "[explainx.ai](https://www.explainx.ai/news)" in md
    assert "[volanea.com](https://www.volanea.com/blog/ai-breakthroughs-october-2026)" in md
    assert "explainx+1" not in md


def test_copilot_scriptor_code_block() -> None:
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
    md = html_to_markdown(html, provider="copilot")
    assert "Before code" in md
    assert "After code" in md
    assert "Copy code" not in md
    assert "```python\ndef add(a, b):\n    return a + b\n```" in md


def test_copilot_scriptor_plain_text_virtualized() -> None:
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
    md = html_to_markdown(html, provider="copilot")
    assert "Copy" not in md
    assert "Plain Text" not in md
    assert "```\nInput Layer\n      ↓\nOutput Layer\n```" in md


def test_copilot_table_and_markdown_reply() -> None:
    html = """
    <div data-testid="markdown-reply">
        <h3>Analysis Table</h3>
        <table>
            <thead>
                <tr><th>Metric</th><th>Score</th></tr>
            </thead>
            <tbody>
                <tr><td>Accuracy</td><td>98.5%</td></tr>
                <tr><td>Latency</td><td>45ms</td></tr>
            </tbody>
        </table>
        <button data-testid="CopyButtonTestId">Copy Response</button>
    </div>
    """
    md = html_to_markdown(html, provider="copilot")
    assert "### Analysis Table" in md
    assert "| Metric | Score |" in md
    assert "| Accuracy | 98.5% |" in md
    assert "| Latency | 45ms |" in md
    assert "Copy Response" not in md
