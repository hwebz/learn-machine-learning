import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.browser.extraction import _MarkdownRenderer

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find('data-markdown-text-style="assistant-message"')
msg_html = html[idx:idx+90000]

# Let's see what happens if we patch _MarkdownRenderer to support ChatGPT code blocks
# Let's inspect class definition and test

class TestRenderer(_MarkdownRenderer):
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        cls = attr_map.get("class", "")

        is_chatgpt_block = (
            "CodeBlock" in cls
            or attr_map.get("data-markdown-copy") == "code-block"
        )
        if is_chatgpt_block and not self._code_stack:
            self._code_stack.append({
                "tag": tag,
                "depth": 1,
                "lang": None,
                "lang_text": [],
                "in_lang": False,
                "lang_depth": 0,
                "view_lines": [],
                "curr_line": [],
                "in_line": False,
                "line_depth": 0,
                "general_text": [],
                "skip_depth": 0,
            })
            return

        if self._code_stack:
            top = self._code_stack[-1]
            if "truncate" in cls and not top["lang"]:
                top["in_lang"] = True
                top["lang_depth"] = 1
            if "cm-line" in cls:
                top["in_line"] = True
                top["line_depth"] = 1
                top["curr_line"] = []

        super().handle_starttag(tag, attrs)

renderer = TestRenderer()
renderer.feed(msg_html)
renderer.close()
res = renderer.markdown()

print("=== TEST RENDER RESULT (first 3000 chars) ===")
print(res[:3000])
