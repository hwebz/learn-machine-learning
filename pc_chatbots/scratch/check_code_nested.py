import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'data/artifacts/ui-chatgpt-1791890145/chatgpt/page-1791890213.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('Backticks inside inline code')
if idx == -1:
    idx = html.find('nested `code`')
if idx == -1:
    idx = html.find('npm install')
print("Index:", idx)
if idx != -1:
    print(html[idx-100:idx+600])
