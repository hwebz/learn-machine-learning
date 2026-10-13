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


def test_chatgpt_escaped_characters_and_headings() -> None:
    html = """
    <p><span>Escaped Markdown characters: </span><span>*</span><span>not italic</span><span>*</span><span>, </span><span>`</span><span>not code</span><span>`</span><span>, </span><span># </span><span>not a heading.</span></p>
    <p><span>#</span> <span>This should not become a heading.</span></p>
    <p><span>&gt;</span> <span>This should not become a blockquote.</span></p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert r"\*not italic\*" in md
    assert r"\`not code\`" in md
    assert r"\# This should not become a heading." in md
    assert r"\> This should not become a blockquote." in md


def test_chatgpt_table_alignment_and_special_pipe() -> None:
    html = """
    <table>
        <thead>
            <tr>
                <th data-d-align="start">Left</th>
                <th data-d-align="center">Center</th>
                <th data-d-align="end">Right</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>a \\| b</code></td>
                <td>Center text</td>
                <td>123</td>
            </tr>
        </tbody>
    </table>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "| :--- | :---: | ---: |" in md
    assert "| `a \\| b` | Center text | 123 |" in md


def test_chatgpt_dividers_italic_and_strikethrough() -> None:
    html = """
    <p>Above divider</p>
    <div class="Divider-WkGDyu" data-d-component="divider"></div>
    <p><span data-d-font-style="italic">Footnote rendering depends on the Markdown implementation.</span></p>
    <p><span data-d-text-decoration="line-through">Strikethrough text</span></p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "---" in md
    assert "*Footnote rendering depends on the Markdown implementation.*" in md
    assert "~~Strikethrough text~~" in md


def test_chatgpt_checklists_and_tasklists() -> None:
    html = """
    <ul>
        <li><button role="checkbox" aria-checked="false" data-state="unchecked"></button>Task unchecked</li>
        <li><button role="checkbox" aria-checked="true" data-state="checked"></button>Task checked</li>
    </ul>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "- [ ] Task unchecked" in md
    assert "- [x] Task checked" in md


def test_chatgpt_er_diagram_mermaid() -> None:
    html = """
    <div data-chatgpt-mermaid-preview="">
        <svg aria-roledescription="er" class="erDiagram">
            <g id="preview-entity-USER-0">
                <g class="label attribute-type"><text>int</text></g>
                <g class="label attribute-name"><text>id</text></g>
                <g class="label attribute-keys"><text>PK</text></g>
            </g>
            <g id="preview-entity-ORDER-1">
                <g class="label attribute-type"><text>int</text></g>
                <g class="label attribute-name"><text>id</text></g>
                <g class="label attribute-keys"><text>PK</text></g>
            </g>
            <g class="edges edgePaths">
                <path data-id="id_entity-USER-0_entity-ORDER-1_0" marker-start="url(#onlyOneStart)" marker-end="url(#zeroOrMoreEnd)"></path>
            </g>
            <g class="label" data-id="id_entity-USER-0_entity-ORDER-1_0"><text>places</text></g>
        </svg>
    </div>
    </div>
    </div>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "```mermaid" in md
    assert "erDiagram" in md
    assert "USER {" in md
    assert "int id PK" in md
    assert "ORDER {" in md
    assert "USER ||--o{ ORDER : places" in md


def test_chatgpt_default_strong_bold() -> None:
    html = """
    <p>This is <span class="TextBase-hXhSqg Text-lIMP0_" data-d-text-flow="" data-d-component="text" data-d-default-strong="" data-d-inline=""><span data-d-text-flow="word" data-d-stream-word="">Bold </span><span data-d-text-flow="word" data-d-stream-word="">text</span></span> in ChatGPT.</p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "**Bold text**" in md


def test_chatgpt_and_base_underline() -> None:
    html = """
    <p><span class="TextBase-hXhSqg Text-lIMP0_" data-d-text-flow="" data-d-component="text" data-d-inline="" data-d-text-decoration="underline"><span data-d-text-flow="word" data-d-stream-word="">Underlined </span><span data-d-text-flow="word" data-d-stream-word="">text</span></span></p>
    <p><u>HTML u tag</u> and <ins>HTML ins tag</ins></p>
    """
    md_chatgpt = html_to_markdown(html, provider="chatgpt")
    assert "<u>Underlined text</u>" in md_chatgpt
    assert "<u>HTML u tag</u>" in md_chatgpt
    assert "<u>HTML ins tag</u>" in md_chatgpt

    md_base = html_to_markdown(html, provider="base")
    assert "<u>HTML u tag</u>" in md_base
    assert "<u>HTML ins tag</u>" in md_base


def test_inline_code_backtick_escaping() -> None:
    html = """
    <p><code>Test with nested `code` block</code></p>
    <p><code class="Code-kbs71c" data-d-component="code"><span data-d-text-flow="word">Use </span><span data-d-text-flow="word">`npm </span><span data-d-text-flow="word">install` </span><span data-d-text-flow="word">to </span><span data-d-text-flow="word">install </span><span data-d-text-flow="word">dependencies.</span></code></p>
    <p><code>`</code></p>
    <p><code>foo `` bar</code></p>
    <p><code>simple code</code></p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "``Test with nested `code` block``" in md
    assert "``Use `npm install` to install dependencies.``" in md
    assert "`` ` ``" in md
    assert "```foo `` bar```" in md
    assert "`simple code`" in md


def test_chatgpt_standalone_raw_html_component_row() -> None:
    html = """
    <p>Before calculator</p>
    <div class="Box-qIMv6G custom-calc" data-d-component="row">
        <label>Input X</label>
        <input type="number" value="42" />
        <button>Calculate</button>
    </div>
    <p>After calculator</p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "Before calculator" in md
    assert '<div class="Box-qIMv6G custom-calc" data-d-component="row">' in md
    assert '<input type="number" value="42" />' in md
    assert '<button>Calculate</button>' in md
    assert "</div>" in md
    assert "After calculator" in md


def test_chatgpt_standalone_box_component_with_nested_styles_and_controls() -> None:
    html = """
    <p>Top section</p>
    <div class="Box-d8a1c9 custom-tool" data-d-component="row">
        <div class="Box-col" data-d-component="column">
            <label><span data-d-weight="bold">Select Option:</span></label>
            <select name="options">
                <option value="1">Option 1</option>
                <option value="2">Option 2</option>
            </select>
        </div>
        <div class="Box-col" data-d-component="column">
            <input type="text" placeholder="Custom value" value="Test" />
            <button class="btn-action">Apply</button>
        </div>
    </div>
    <p>Bottom section</p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "Top section" in md
    assert '<div class="Box-d8a1c9 custom-tool" data-d-component="row">' in md
    assert '<select name="options">' in md
    assert '<option value="1">Option 1</option>' in md
    assert '<input type="text" placeholder="Custom value" value="Test" />' in md
    assert '<button class="btn-action">Apply</button>' in md
    assert "Bottom section" in md
    # Markdown symbols should not leak outside or inside the raw HTML block
    assert "**Select Option:**" not in md


def test_chatgpt_full_page_snapshot_isolation() -> None:
    full_page_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <nav id="history-sidebar">
            <a href="#main">Skip to content</a>
            <button>New chat</button>
            <p>Recents</p>
            <a href="/c/123">Old chat 1</a>
        </nav>
        <main id="main">
            <h4>You said:</h4>
            <p>Calculate 2+2</p>
            <div data-markdown-text-style="assistant-message" class="MarkdownRoot-test">
                <p>The answer is <strong>4</strong>.</p>
            </div>
        </main>
    </body>
    </html>
    """
    md = html_to_markdown(full_page_html, provider="chatgpt")
    assert "The answer is **4**." in md
    assert "Skip to content" not in md
    assert "New chat" not in md
    assert "Recents" not in md
    assert "Old chat 1" not in md
    assert "You said:" not in md


def test_chatgpt_full_page_ignores_tertiary_thinking_container() -> None:
    full_page_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <nav><a href="#content">Skip to content</a></nav>
        <div data-markdown-text-style="assistant-message" data-markdown-text-tone="tertiary">
            <span>Thinking process: Finalized assumptions and formulas...</span>
        </div>
        <div data-markdown-text-style="assistant-message" class="MarkdownRoot">
            <p>Here is your <strong>ROI Calculator</strong> result.</p>
        </div>
    </body>
    </html>
    """
    md = html_to_markdown(full_page_html, provider="chatgpt")
    assert "Here is your **ROI Calculator** result." in md
    assert "Thinking process" not in md


def test_chatgpt_interactive_tool_components() -> None:
    html = """
    <p>Intro text</p>
    <div class="Box-qIMv6G" data-d-component="box" data-d-direction="col">
        <div class="Box-header" data-d-component="row">
            <h3>AI Workflow ROI Calculator</h3>
        </div>
        <div class="Slider-veC4c6" data-d-component="slider">
            <div class="SliderContainer-csaRc8">
                <span role="slider" aria-valuemin="0" aria-valuemax="100" aria-valuenow="65" class="Thumb-ZDGlbm"></span>
            </div>
        </div>
        <div role="radiogroup" data-d-component="radio-group" class="RadioGroup-tMSWPY">
            <button type="button" role="radio" aria-checked="true" data-state="checked" value="USD"></button>
            <button type="button" role="radio" aria-checked="false" data-state="unchecked" value="EUR"></button>
        </div>
        <input data-d-component="input" type="number" value="10" />
    </div>
    <p>Outro text</p>
    """
    md = html_to_markdown(html, provider="chatgpt")
    assert "Intro text" in md
    assert '<div class="Box-qIMv6G" data-d-component="box" data-d-direction="col">' in md
    assert 'data-d-component="slider"' in md
    assert 'role="radiogroup"' in md
    assert '<input data-d-component="input" type="number" value="10" />' in md
    assert "Outro text" in md





