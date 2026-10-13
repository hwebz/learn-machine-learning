import sqlite3
import json
import re
from app.browser.converters import html_to_markdown

html_path = r"data\artifacts\ui-chatgpt-1791884443\chatgpt\page-1791884510.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Convert with new ChatGPT converter
new_md = html_to_markdown(html, provider="chatgpt")

# Clean footer if present
if "ChatGPT can make mistakes" in new_md:
    new_md = new_md.split("ChatGPT can make mistakes")[0].strip()

print("Converted new markdown length:", len(new_md))

job_id = "d9c9649b-adc0-4165-ab47-dce7c9a36930"
conn = sqlite3.connect("data/app.db")
cursor = conn.cursor()

# Update providerrun
cursor.execute(
    "UPDATE providerrun SET answer_md = ? WHERE id = ?",
    (new_md, f"{job_id}:chatgpt:run")
)

# Update job.provider_runs_json and report_markdown
job_row = cursor.execute("SELECT provider_runs_json FROM job WHERE id = ?", (job_id,)).fetchone()
if job_row and job_row[0]:
    runs = json.loads(job_row[0])
    for r in runs:
        if r.get("provider") == "chatgpt":
            r["answer_markdown"] = new_md
    cursor.execute(
        "UPDATE job SET provider_runs_json = ?, report_markdown = ? WHERE id = ?",
        (json.dumps(runs), new_md, job_id)
    )

# Also update jobevents if any event has data_json with report or answer
events = cursor.execute("SELECT id, data_json FROM jobevent WHERE job_id = ?", (job_id,)).fetchall()
for eid, d_json in events:
    if d_json and "markdown" in d_json:
        try:
            s_obj = json.loads(d_json)
            if "report_markdown" in s_obj:
                s_obj["report_markdown"] = new_md
            if "answer_markdown" in s_obj:
                s_obj["answer_markdown"] = new_md
            cursor.execute("UPDATE jobevent SET data_json = ? WHERE id = ?", (json.dumps(s_obj), eid))
        except Exception:
            pass

conn.commit()
print("Updated database providerrun, job, and jobevents for d9c9649b!")
