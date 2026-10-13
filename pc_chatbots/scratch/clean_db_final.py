import sqlite3
import json
from app.browser.extraction import html_to_markdown, clean_markdown_text

html_path = r'data\artifacts\ui-chatgpt-1791876747\chatgpt\page-1791876774.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

needle = 'data-markdown-text-style="assistant-message"'
idx = html.find(needle)
if idx != -1:
    idx = html.find('>', idx) + 1
    end_idx = html.rfind('</div>')
    inner = html[idx:end_idx]
    md = clean_markdown_text(html_to_markdown(inner))
    
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE providerrun SET answer_md = ? WHERE id LIKE '70f9d95a%'", (md,))
    cursor.execute("UPDATE job SET report_markdown = ? WHERE id LIKE '70f9d95a%'", (md,))
    
    cursor.execute("SELECT data_json FROM jobevent WHERE id = 1674")
    row = cursor.fetchone()
    if row and row[0]:
        d = json.loads(row[0])
        d['response_markdown'] = md
        d['response_length'] = len(md)
        cursor.execute("UPDATE jobevent SET data_json = ? WHERE id = 1674", (json.dumps(d),))
    
    conn.commit()
    print("Successfully updated! First 200 chars:")
    print(repr(md[:200]))
