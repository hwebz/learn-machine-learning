import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'data/artifacts/ui-chatgpt-1791890145/chatgpt/page-1791890213.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("--- data-d-default-strong occurrences ---")
for m in re.finditer(r'<span[^>]*data-d-default-strong[^>]*>([\s\S]*?)</span>', html):
    txt = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    print(f"Strong: '{txt}' | tag: {m.group(0)[:120]}")

print("\n--- data-d-text-decoration='underline' occurrences ---")
for m in re.finditer(r'<[^>]*data-d-text-decoration=["\']underline["\'][^>]*>([\s\S]*?)</[^>]+>', html):
    txt = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    print(f"Underline: '{txt}' | tag: {m.group(0)[:120]}")

print("\n--- Backticks in code occurrences ---")
for m in re.finditer(r'<code[^>]*>([\s\S]*?)</code>', html):
    txt = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if '`' in txt:
        print(f"Code with backtick: '{txt}'")
