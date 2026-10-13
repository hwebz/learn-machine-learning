import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'data/artifacts/ui-chatgpt-1791890145/chatgpt/page-1791890213.html', 'r', encoding='utf-8') as f:
    html = f.read()

for term in ["Backtick", "backtick", "nested `code`", "npm install", "16. Escaping"]:
    idx = html.find(term)
    print(f"Term '{term}': {idx}")
    if idx != -1:
        print(html[idx-50:idx+350])
        print("---")
