with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    html = f.read()

import re

print("data-d-font-style values:", set(re.findall(r'data-d-font-style="([^"]+)"', html)))
print("data-d-weight values:", set(re.findall(r'data-d-weight="([^"]+)"', html)))
print("data-d-font-weight values:", set(re.findall(r'data-d-font-weight="([^"]+)"', html)))
print("data-d-text-decoration values:", set(re.findall(r'data-d-text-decoration="([^"]+)"', html)))
print("data-d-decoration values:", set(re.findall(r'data-d-decoration="([^"]+)"', html)))
print("line-through in classes:", set(re.findall(r'class="[^"]*(?:line-through|strikethrough|strike)[^"]*"', html)))
