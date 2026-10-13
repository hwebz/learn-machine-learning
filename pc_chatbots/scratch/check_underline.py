import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'data/artifacts/ui-chatgpt-1791890145/chatgpt/page-1791890213.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = list(re.finditer(r'<([a-zA-Z0-9]+)[^>]*data-d-text-decoration=["\']underline["\'][^>]*>([\s\S]*?)</\1>', html))
print(f"Count of underline matches: {len(matches)}")
for m in matches:
    print('Underline match:', repr(re.sub(r'<[^>]+>', '', m.group(2)).strip()))
    print('Raw snippet:', repr(m.group(0)[:200]))
