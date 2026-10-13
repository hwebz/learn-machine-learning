import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('scratch/er_svg_only.svg', 'r', encoding='utf-8') as f:
    svg = f.read()

idx = svg.find('>USER<')
# Look back for <g id="...entity
prev_entity = svg.rfind('id="', 0, idx)
print(svg[prev_entity:prev_entity+100])

prev_g = svg.rfind('<g class="entityBox', 0, idx)
if prev_g == -1:
    prev_g = svg.rfind('<g ', 0, idx-500)
print("Previous g:", svg[prev_g:prev_g+100])
