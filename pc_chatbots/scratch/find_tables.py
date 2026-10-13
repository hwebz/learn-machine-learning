import re
html_path = r"data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html"

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's search for any <table> tags anywhere in the file
tables = [m.start() for m in re.finditer(r'<table', html, re.IGNORECASE)]
print("Total <table> occurrences in file:", len(tables))

for t_idx in tables:
    print("\n--- TABLE AT", t_idx, "---")
    print(html[t_idx:t_idx+800])
