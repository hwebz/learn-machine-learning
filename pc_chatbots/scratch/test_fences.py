from app.browser.converters import html_to_markdown

with open(r'data\artifacts\ui-chatgpt-1791881861\chatgpt\page-1791881877.html', encoding='utf-8') as f:
    html = f.read()

idx = html.find('assistant-message')
md = html_to_markdown(html[idx:], provider="chatgpt")
for l in md.splitlines():
    if l.startswith("```"):
        print(l)
