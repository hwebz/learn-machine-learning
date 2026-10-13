with open('scratch/test_conversion_output.md', encoding='utf-8') as f:
    md = f.read()

import re

print("=== 1. Escaped characters ===")
m = re.search(r'Escaped Markdown characters.*', md)
if m:
    print("Line:", m.group(0))

print("\n=== 2 & 3. Nested & mixed lists ===")
m2 = re.search(r'## Nested ordered list[\s\S]*?## Mixed list[\s\S]*?## Task list', md)
if m2:
    print(m2.group(0)[:500])

print("\n=== 4. Column alignment table ===")
m4 = re.search(r'## Column alignment[\s\S]*?\n\n', md)
if m4:
    print(m4.group(0))

print("\n=== 5. Table special characters ===")
m5 = re.search(r'\| `a \\\| b` \|.*', md)
if m5:
    print("Found special char cell:", m5.group(0))
else:
    m5_alt = re.search(r'\| `a.*', md)
    print("Special char row:", m5_alt.group(0) if m5_alt else "Not found")

print("\n=== 6. Horizontal rules ===")
m6 = re.search(r'# 13\. Horizontal Rules[\s\S]*?# 14\.', md)
if m6:
    print(m6.group(0))

print("\n=== 7. Footnotes italic ===")
m7 = re.search(r'Footnote rendering depends.*', md)
if m7:
    print("Footnote italic line:", m7.group(0))

print("\n=== 8. Strikethrough ===")
m8 = re.findall(r'~~[^~]+~~', md)
print("Strikethrough count:", len(m8), "Sample:", m8[:4])

print("\n=== 9. Mermaid diagrams ===")
m9 = re.findall(r'```mermaid[\s\S]*?```', md)
print("Mermaid blocks count:", len(m9))
for i, b in enumerate(m9):
    print(f"Block {i}:", b.splitlines()[0], b.splitlines()[1])

print("\n=== 10. Section 16 Escaped characters ===")
m10 = re.search(r'# 16\. Escaping and Literal Syntax[\s\S]*?## Inline code', md)
if m10:
    print(m10.group(0))

print("\n=== 11 & 12. Checklists and Section 18 ===")
m11 = re.findall(r'-\s+\[[ x]\]', md)
print("Total checkboxes found in markdown:", len(m11))
m12 = re.search(r'# 18\. Rendering Compatibility Checklist[\s\S]*?Compatibility note', md)
if m12:
    print("Section 18 start:")
    print(m12.group(0)[:600])
