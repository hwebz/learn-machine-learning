import re
from app.browser.converters import html_to_markdown

html_path = r"data\artifacts\ui-chatgpt-1791888941\chatgpt\page-1791889002.html"
with open(html_path, "r", encoding="utf-8") as f:
    h = f.read()

md = html_to_markdown(h, provider="chatgpt")
print("Extracted markdown length:", len(md))
print("Start of extracted markdown:")
print(md[:500])
print("\nEnd of extracted markdown:")
print(md[-500:])
