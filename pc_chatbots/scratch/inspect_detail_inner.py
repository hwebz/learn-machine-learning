import json
import re

d = json.load(open('scratch/minimax_thinking_probe.json', encoding='utf-8'))
html = d['full_html']

detail_match = re.search(r'<div[^>]*data-testid=[\'"]turn-process-detail[\'"][^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>', html, re.DOTALL)
if detail_match:
    inner = detail_match.group(1)
    print("turn-process-detail length:", len(inner))
    testids = re.findall(r'data-testid=[\'"]([^\'"]+)[\'"]', inner)
    print("Testids inside detail:", sorted(set(testids)))
    # print structure
    lines = [line.strip() for line in inner.split('\n') if line.strip() and not line.strip().startswith('<svg') and not line.strip().startswith('<path')]
    print("Sample lines inside detail:\n" + '\n'.join(lines[:40]))
else:
    print("turn-process-detail not matched by regex")
