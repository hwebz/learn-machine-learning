import sys
sys.stdout.reconfigure(encoding='utf-8')

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

import re

tables = re.findall(r'<table[\s\S]*?</table>', html)
print(f"Total tables: {len(tables)}")
for i, t in enumerate(tables):
    print(f"\n=================== TABLE {i+1} ===================")
    print(t[:2000])
