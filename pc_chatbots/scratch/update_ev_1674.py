import sqlite3, json

conn = sqlite3.connect("data/app.db")
cursor = conn.cursor()

cursor.execute("SELECT answer_md FROM providerrun WHERE id LIKE '70f9d95a%'")
new_md = cursor.fetchone()[0]

cursor.execute("SELECT data_json FROM jobevent WHERE id = 1674")
d = json.loads(cursor.fetchone()[0])
d["response_markdown"] = new_md
d["response_length"] = len(new_md)
cursor.execute("UPDATE jobevent SET data_json = ? WHERE id = 1674", (json.dumps(d),))
conn.commit()
print("Updated event 1674 response_markdown with length:", len(new_md))
