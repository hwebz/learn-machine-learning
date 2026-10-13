html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

idx = html.find('HelloWorld.java')
if idx != -1:
    print(html[idx:idx+1200])
