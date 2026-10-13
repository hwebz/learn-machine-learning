with open(r'data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html', encoding='utf-8') as f:
    html = f.read()

idx = 629757
print(html[idx + 1000:idx + 3500].encode('ascii', errors='replace').decode('ascii'))
