import sqlite3

conn = sqlite3.connect("data/app.db")
c = conn.cursor()
cols = [r[1] for r in c.execute("PRAGMA table_info(providerrun)")]
print("providerrun columns:", cols)

for r in c.execute("SELECT id FROM providerrun"):
    print("providerrun row id:", r[0])
