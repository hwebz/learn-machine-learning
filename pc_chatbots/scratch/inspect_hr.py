with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    html = f.read()

import re

for m in re.finditer(r'Horizontal\s*</span>\s*<span[^>]*>Rules', html):
    idx = m.start()
    print("Match around:", idx)
    print(html[idx - 50:idx + 1500].encode('ascii', errors='replace').decode('ascii'))
