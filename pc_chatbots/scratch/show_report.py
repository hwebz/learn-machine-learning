import sqlite3

conn = sqlite3.connect("pc_chatbots/data/app.db")
r = conn.cursor().execute("SELECT report_markdown FROM job WHERE id='5af9fca4-6c96-4cde-8814-4385b1cca94d'").fetchone()
if r:
    print("Report len:", len(r[0]))
    with open("pc_chatbots/scratch/report_out.txt", "w", encoding="utf-8") as f:
        f.write(r[0])
    print("Written to pc_chatbots/scratch/report_out.txt")
else:
    print("None")
