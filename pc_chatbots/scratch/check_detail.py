import json
import re

d = json.load(open('scratch/minimax_thinking_probe.json', encoding='utf-8'))
html = d['full_html']

pos = html.find('turn-process-detail')
if pos != -1:
    start = max(0, pos - 200)
    end = min(len(html), pos + 3000)
    print("Found around turn-process-detail:")
    print(html[start:end])
else:
    print("Not found")
