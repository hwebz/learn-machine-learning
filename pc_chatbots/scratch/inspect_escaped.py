with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    html = f.read()

import re

for query in ['escaped', 'not italic', 'compatibility checklist', 'mermaid', 'footnote']:
    matches = [m.start() for m in re.finditer(query, html, re.IGNORECASE)]
    print(f"Query: '{query}', count: {len(matches)}")
    for idx in matches[:3]:
        print("  Snippet:", re.sub(r'<[^>]+>', ' ', html[max(0, idx-60):min(len(html), idx+140)]))
