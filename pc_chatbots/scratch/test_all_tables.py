from app.browser.extraction import html_to_markdown

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find('data-markdown-text-style="assistant-message"')
msg_html = html[idx:] # all the way to the end

md = html_to_markdown(msg_html)

table_lines = [l for l in md.splitlines() if l.startswith("|")]
print(f"Total table lines extracted: {len(table_lines)}")
for tl in table_lines:
    print(tl)
