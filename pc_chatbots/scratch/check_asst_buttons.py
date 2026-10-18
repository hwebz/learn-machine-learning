import re

html_path = "pc_chatbots/data/artifacts/ui-zhipu-1792345549/zhipu/page-1792346756.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

start = 264917
asst_chunk = content[start:]

print("copy-response-button in whole content?", "copy-response-button" in content)
print("copy-response-button in asst_chunk?", "copy-response-button" in asst_chunk)

# Find all occurrences of "copy" in content
for m in re.finditer(r'class="[^"]*copy[^"]*"', content, re.I):
    print("MATCH CLASS COPY:", m.group(0))

for m in re.finditer(r'aria-label="[^"]*copy[^"]*"', content, re.I):
    print("MATCH ARIA COPY:", m.group(0))
