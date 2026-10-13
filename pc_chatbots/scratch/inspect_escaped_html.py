with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    html = f.read()

import re

# Look for section 16 or escaped markdown characters
idx = html.find('Escaped')
while idx != -1:
    print("=" * 60)
    print("Match at index", idx)
    print(html[idx:idx + 800].encode('ascii', errors='replace').decode('ascii'))
    idx = html.find('Escaped', idx + 1)
