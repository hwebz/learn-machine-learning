from app.browser.converters.base import BaseMarkdownConverter
from app.browser.converters.chatgpt import ChatGPTMarkdownConverter

html_snippet = """
<p><span data-d-text-flow="word">*</span><span data-d-text-flow="word">not </span><span data-d-text-flow="word">italic</span><span data-d-text-flow="word">*</span></p>
<p><span data-d-text-flow="word">#</span> <span data-d-text-flow="word">not a heading</span></p>
<p><span data-d-text-flow="word">&gt;</span> <span data-d-text-flow="word">not a quote</span></p>
<p><span data-d-font-style="italic">Footnote rendering depends on the Markdown implementation.</span></p>
<p><span data-d-text-decoration="line-through">Strikethrough text</span></p>
<div class="Divider-WkGDyu" data-d-component="divider"></div>
"""

# Test with current vs updated
print("Snippet test ready")
