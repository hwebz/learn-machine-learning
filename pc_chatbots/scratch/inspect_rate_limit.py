import re

html_path = r"data\artifacts\ui-chatgpt-1791888941\chatgpt\page-1791889002.html"
with open(html_path, "r", encoding="utf-8") as f:
    h = f.read()

print("HTML length:", len(h))
# Find where 'rate limit' appears!
for m in re.finditer(r'rate[\s_-]*limit', h, re.IGNORECASE):
    idx = m.start()
    print(f"Match at {idx}:")
    print(h[max(0, idx - 150):idx + 250].encode('ascii', errors='replace').decode('ascii'))
