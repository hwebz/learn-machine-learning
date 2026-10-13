with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    h = f.read()

import re

idx = 629625
sub = h[idx:idx + 40000]
print(re.sub(r'<[^>]+>', ' ', sub))
