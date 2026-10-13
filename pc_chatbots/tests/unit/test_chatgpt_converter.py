from __future__ import annotations

import pytest

from app.browser.converters import (
    BaseMarkdownConverter,
    ChatGPTMarkdownConverter,
    get_converter,
    html_to_markdown,
)


def test_converter_factory() -> None:
    base = get_converter()
    assert isinstance(base, BaseMarkdownConverter)

    chatgpt = get_converter("chatgpt")
    assert isinstance(chatgpt, ChatGPTMarkdownConverter)

    openai = get_converter("openai")
    assert isinstance(openai, ChatGPTMarkdownConverter)

    unknown = get_converter("custom_provider_xyz")
    assert isinstance(unknown, BaseMarkdownConverter)


def test_chatgpt_codemirror_code_block() -> None:
    html = """
    <div class="CodeBlock-zu1QM3" data-markdown-copy="code-block">
        <div class="code-header">
            <span class="truncate">python</span>
            <button data-markdown-copy="exclude" aria-label="Copy code">Copy</button>
        </div>
        <div class="cm-editor">
            <div class="cm-scroller">
                <div class="cm-content">
                    <div class="cm-line">def hello():</div>
                    <div class="cm-line">    return "world"</div>
                </div>
            </div>
        </div>
    </div>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "```python" in md
    assert "def hello():" in md
    assert 'return "world"' in md
    assert "Copy code" not in md
    assert "Copy" not in md


def test_chatgpt_katex_math_and_latex_code_block() -> None:
    html = """
    <p>Display equation:</p>
    <span class="katex-display">
        <span class="katex">
            <span class="katex-html" aria-hidden="true"><span>E</span><span>=</span><span>mc</span></span>
            <annotation encoding="application/x-tex">E = mc^2</annotation>
        </span>
    </span>
    <p>LaTeX source block:</p>
    <p>`\\[\nE = mc^2\n\\]`</p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "$$\nE = mc^2\n$$" in md
    assert "```latex\n\\[\nE = mc^2\n\\]\n```" in md


def test_chatgpt_table_with_cell_math() -> None:
    html = """
    <table class="Table-QT1UX2">
        <thead>
            <tr data-d-component="table-row">
                <th data-d-component="table-cell">Concept</th>
                <th data-d-component="table-cell">Formula</th>
                <th data-d-component="table-cell">Notes</th>
            </tr>
        </thead>
        <tbody>
            <tr data-d-component="table-row">
                <td data-d-component="table-cell">Energy</td>
                <td data-d-component="table-cell">
                    <span class="katex">
                        <annotation encoding="application/x-tex">E = mc^2</annotation>
                    </span>
                </td>
                <td data-d-component="table-cell">Relativistic mass</td>
            </tr>
        </tbody>
    </table>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "| Concept | Formula | Notes |" in md
    assert "| --- | --- | --- |" in md
    assert "| Energy | $E = mc^2$ | Relativistic mass |" in md


def test_chatgpt_nested_lists_and_quotes() -> None:
    html = """
    <h1>Summary</h1>
    <ul>
        <li>Item 1</li>
        <li>Item 2
            <ol>
                <li>Sub-item A</li>
                <li>Sub-item B</li>
            </ol>
        </li>
    </ul>
    <blockquote>
        <p>A profound insight.</p>
    </blockquote>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "# Summary" in md
    assert "- Item 1" in md
    assert "- Item 2" in md
    assert "1. Sub-item A" in md
    assert "2. Sub-item B" in md
    assert "> A profound insight." in md
