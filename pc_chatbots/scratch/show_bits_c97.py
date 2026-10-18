import re

html_path = "pc_chatbots/data/artifacts/ui-zhipu-1792345549/zhipu/page-1792346756.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

pos = content.find("bits-c97")
if pos != -1:
    with open("pc_chatbots/scratch/bits_c97_context.txt", "w", encoding="utf-8") as out:
        out.write("--- 1000 CHARS BEFORE bits-c97 ---\n")
        out.write(content[max(0, pos-1000):pos])
        out.write("\n\n--- 1000 CHARS AFTER bits-c97 ---\n")
        out.write(content[pos:pos+1000])

print("Written to pc_chatbots/scratch/bits_c97_context.txt")
