import sqlite3
import json

conn = sqlite3.connect("pc_chatbots/data/app.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

row = cursor.execute("SELECT * FROM job WHERE id='5af9fca4-6c96-4cde-8814-4385b1cca94d'").fetchone()
if row:
    d = dict(row)
    d.pop("report_markdown", None)
    print(json.dumps(d, indent=2, ensure_ascii=True, default=str))
else:
    print("Job not found")
