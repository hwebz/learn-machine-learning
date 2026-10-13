import sqlite3

conn = sqlite3.connect("data/app.db")
cursor = conn.cursor()
cursor.execute("SELECT answer_md FROM providerrun WHERE id LIKE '70f9d95a%'")
row = cursor.fetchone()
if row and row[0]:
    answer_md = row[0]
    cursor.execute("UPDATE job SET report_markdown = ? WHERE id LIKE '70f9d95a%'", (answer_md,))
    conn.commit()
    print("Updated job.report_markdown for 70f9d95a!")
