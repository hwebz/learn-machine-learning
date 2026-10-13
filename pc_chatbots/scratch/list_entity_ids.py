import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('scratch/er_svg_only.svg', 'r', encoding='utf-8') as f:
    svg = f.read()

print("All entity IDs:")
for m in re.finditer(r'id="([^"]*?-entity-[^"]*?)"', svg):
    print(m.group(1))
