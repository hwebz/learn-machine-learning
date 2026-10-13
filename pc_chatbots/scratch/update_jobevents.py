import sqlite3, json

conn = sqlite3.connect("data/app.db")
cursor = conn.cursor()

# Get latest markdown from providerrun
cursor.execute("SELECT answer_md FROM providerrun WHERE id LIKE '70f9d95a%'")
row = cursor.fetchone()
if not row:
    print("No providerrun found")
    exit(0)

new_md = row[0]
print("New MD length:", len(new_md))

# Check job events
for r in cursor.execute("SELECT id, step, message, data_json FROM jobevent WHERE job_id LIKE '70f9d95a%'").fetchall():
    eid, step, msg, data_json = r
    if data_json and ("LaTeX" in data_json or "E = mc^2" in data_json):
        try:
            d = json.loads(data_json)
            print(f"Updating event {eid}: step={step}")
            if "description" in d:
                d["description"] = new_md
            if "response_content" in d:
                d["response_content"] = new_md
            if "answer_markdown" in d:
                d["answer_markdown"] = new_md
            cursor.execute("UPDATE jobevent SET data_json = ? WHERE id = ?", (json.dumps(d), eid))
        except Exception as e:
            print("Error parsing data_json:", e)

conn.commit()
print("Updated jobevents!")
