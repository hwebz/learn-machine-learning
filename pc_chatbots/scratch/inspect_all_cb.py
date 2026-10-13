import sys
sys.stdout.reconfigure(encoding='utf-8')

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

import re

m = re.search(r'truncate">Python</div>[\s\S]*?</code>', html)
if m:
    print("=== PYTHON CODEBLOCK FULL ===")
    print(m.group(0))
