import sys
sys.stdout.reconfigure(encoding='utf-8')
# no bs4

html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

import re

# Let's inspect all code blocks in page-1791876774.html
# 1. CodeBlock divs
pattern = re.compile(r'<div[^>]*data-markdown-copy="code-block"[^>]*>([\s\S]*?)</div>\s*</div>\s*</div>', re.DOTALL)
matches = list(pattern.finditer(html))
print("Matched data-markdown-copy='code-block':", len(matches))

for i, m in enumerate(matches[:5]):
    block = m.group(0)
    lang_m = re.search(r'class="min-w-0 flex-1 truncate">([^<]+)<', block)
    lang = lang_m.group(1) if lang_m else ""
    code_m = re.search(r'<code[^>]*>([\s\S]*?)</code>', block)
    cm_m = re.search(r'<div[^>]*class="[^"]*cm-content[^"]*"[^>]*>([\s\S]*?)</div>\s*</div>', block)
    
    print(f"\n--- BLOCK {i+1} ---")
    print("Language:", lang)
    if code_m:
        raw_code = re.sub(r'<[^>]+>', '', code_m.group(1))
        print("Code from <code>:", repr(raw_code.strip()[:60]))
    elif cm_m:
        lines = re.findall(r'<div class="cm-line">([\s\S]*?)</div>', cm_m.group(1))
        clean_lines = [re.sub(r'<[^>]+>', '', l) for l in lines]
        print("Code from cm-line:", repr("\n".join(clean_lines)[:60]))
    else:
        print("No code found")
