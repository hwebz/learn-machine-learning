import sqlite3
import json

conn = sqlite3.connect("data/app.db")
c = conn.cursor()

row = c.execute("SELECT id, status, report_markdown, error, provider_runs_json, created_at FROM job ORDER BY created_at DESC LIMIT 1").fetchone()
if not row:
    print("No jobs found")
    exit()

job_id = row[0]
print(f"Latest Job ID: {job_id}")
print(f"Status: {row[1]}")
print(f"Error: {row[3]}")
print(f"Created: {row[5]}")
print(f"Runs: {row[4]}")

print("\n--- Provider Runs ---")
for pr in c.execute("SELECT id, provider, status, answer_md FROM providerrun WHERE id LIKE ?", (f"{job_id}%",)):
    ans_len = len(pr[3]) if pr[3] else 0
    print(f"Provider: {pr[1]}, Status: {pr[2]}, Answer len: {ans_len}")

print("\n--- Job Events ---")
for r in c.execute("SELECT event_type, provider, step, message, data_json, created_at FROM jobevent WHERE job_id = ? ORDER BY id ASC", (job_id,)):
    msg = (r[3] or "").encode("ascii", errors="replace").decode("ascii")
    print(f"{r[5]} | {r[0]} | {r[1]} | {r[2]} | {msg}")
    if r[4] and ("error" in r[4] or "block" in r[4] or "needs_user_action" in r[4]):
        d_str = r[4].encode("ascii", errors="replace").decode("ascii")
        print(f"   Data: {d_str[:300]}")
