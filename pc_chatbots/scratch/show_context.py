import re

html_path = "pc_chatbots/data/artifacts/ui-zhipu-1792345549/zhipu/page-1792346756.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

def show_context(pattern, size=500):
    for m in re.finditer(pattern, content, re.I):
        start = max(0, m.start() - 100)
        end = min(len(content), m.end() + size)
        print("MATCH:", m.group(0))
        print("CONTEXT:\n", content[start:end])
        print("="*60)

print("--- STOP CONTEXT ---")
show_context(r'<[^>]*aria-label="Stop"[^>]*>')

print("\n--- COPY CONTEXT ---")
show_context(r'<[^>]*aria-label="Copy"[^>]*>')
