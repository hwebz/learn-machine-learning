import sqlite3
import json
from app.browser.converters import html_to_markdown

html_path = r"data\artifacts\ui-chatgpt-1791881861\chatgpt\page-1791881877.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Find assistant message
idx = html.find('data-markdown-text-style="assistant-message"')
div_start = html.rfind('<div', 0, idx)

msg_html = html[div_start:]
new_md = html_to_markdown(msg_html, provider="chatgpt")

if "## Summary" in new_md:
    p1, p2 = new_md.split("## Summary", 1)
    summary_text = p2.split("ChatGPT can make mistakes")[0]
    final_md = (p1 + "## Summary" + summary_text).strip()
else:
    final_md = new_md.strip()

print("New markdown length:", len(final_md))

# Update DB
conn = sqlite3.connect("data/app.db")
cursor = conn.cursor()
cursor.execute(
    "UPDATE providerrun SET answer_md = ? WHERE id = ?",
    (final_md, "7ddae118-6fc6-46a9-9d2b-7e46f58c2c5e:chatgpt:run")
)

# Update job.provider_runs_json
job_row = cursor.execute("SELECT provider_runs_json FROM job WHERE id = '7ddae118-6fc6-46a9-9d2b-7e46f58c2c5e'").fetchone()
if job_row and job_row[0]:
    runs = json.loads(job_row[0])
    for r in runs:
        if r.get("provider") == "chatgpt":
            r["answer_markdown"] = final_md
    cursor.execute(
        "UPDATE job SET provider_runs_json = ?, report_markdown = ? WHERE id = '7ddae118-6fc6-46a9-9d2b-7e46f58c2c5e'",
        (json.dumps(runs), final_md)
    )

conn.commit()
print("Updated database providerrun AND job for 7ddae118!")
