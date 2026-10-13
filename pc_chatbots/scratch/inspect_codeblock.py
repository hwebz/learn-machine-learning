html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

cb_idx = html.find("CodeBlock-zu1QM3")
if cb_idx != -1:
    print("=== CODEBLOCK BODY ===")
    print(html[cb_idx+1200:cb_idx+3000])
