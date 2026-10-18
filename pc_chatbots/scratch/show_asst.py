import re

html_path = "pc_chatbots/data/artifacts/ui-zhipu-1792345549/zhipu/page-1792346756.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Find assistant message container
for m in re.finditer(r'<[^>]*class="[^"]*chat-assistant[^"]*"[^>]*>', content, re.I):
    start = m.start()
    print("Found chat-assistant at index", start)
    with open("pc_chatbots/scratch/assistant_content.txt", "w", encoding="utf-8") as out:
        out.write(content[start:start+4000])
    break
