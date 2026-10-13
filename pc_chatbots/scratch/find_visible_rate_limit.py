import re
from html.parser import HTMLParser

html_path = r"data\artifacts\ui-chatgpt-1791888941\chatgpt\page-1791889002.html"
with open(html_path, "r", encoding="utf-8") as f:
    h = f.read()

# Strip script and style
cleaned = re.sub(r'<(script|style|noscript)[^>]*>[\s\S]*?</\1>', '', h, flags=re.IGNORECASE)
visible_text = re.sub(r'<[^>]+>', ' ', cleaned)
visible_text = re.sub(r'\s+', ' ', visible_text)

print("Visible text length:", len(visible_text))
matches = list(re.finditer(r'rate[\s_-]*limit', visible_text, re.IGNORECASE))
print(f"Matches count in visible text: {len(matches)}")
for m in matches:
    start = max(0, m.start() - 100)
    end = min(len(visible_text), m.start() + 100)
    print("MATCH:")
    print(visible_text[start:end])
