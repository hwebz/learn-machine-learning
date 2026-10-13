from app.browser.extraction import html_to_markdown

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Extract just the assistant message
import re
idx = html.find('data-markdown-text-style="assistant-message"')
# find closing or take next 60000 chars
msg_html = html[idx:idx+80000]

md = html_to_markdown(msg_html)
print("=== EXTRACTED MARKDOWN (first 2000 chars) ===")
print(md[:2000])

print("\n=== SEARCHING FOR TABLES IN EXTRACTED MD ===")
for line in md.splitlines():
    if "|" in line or "Language" in line or "Typing" in line:
        print("TABLE LINE:", line)
