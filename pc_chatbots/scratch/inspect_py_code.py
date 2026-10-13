html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

py_idx = html.find('print("Hello')
if py_idx != -1:
    print("=== AROUND PYTHON CODE (1000 chars before) ===")
    print(html[max(0, py_idx-600):py_idx+200])
