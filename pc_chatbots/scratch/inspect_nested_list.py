with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    html = f.read()

import re

for m in re.finditer(r'Design\s*</span>', html):
    idx = m.start()
    print("Match around:", idx)
    print(html[idx - 150:idx + 600].encode('ascii', errors='replace').decode('ascii'))
