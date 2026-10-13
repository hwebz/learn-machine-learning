with open(r'data\artifacts\ui-chatgpt-1791881861\chatgpt\page-1791881877.html', encoding='utf-8') as f:
    html = f.read()

import re

blocks = list(re.finditer(r'class="[^"]*CodeBlock-zu1QM3[^"]*"', html))
for i, m in enumerate(blocks):
    idx = m.start()
    sub = html[idx:idx + 1000]
    ex_start = sub.find('data-markdown-copy="exclude"')
    if ex_start != -1:
        ex_end = sub.find('</div>', ex_start + 400)
        print(f"--- HEADER EXCLUDE {i} ---")
        print(sub[ex_start:ex_end].encode('ascii', errors='replace').decode('ascii'))
