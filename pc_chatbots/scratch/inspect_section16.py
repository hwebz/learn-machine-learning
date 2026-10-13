with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    h = f.read()

import re

m = re.search(r'Escaping', h)
idx = m.start()
m2 = re.search(r'Combined', h[idx:])
end = idx + m2.start() if m2 else idx + 5000
section = h[idx:end]
print("Any backslashes in section 16?", "\\" in section)
print("All text in section 16:")
clean = re.sub(r'<[^>]+>', '', section)
print(clean)
