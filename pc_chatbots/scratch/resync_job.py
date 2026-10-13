import json
import sqlite3
from datetime import datetime, timezone

def main():
    with open("scratch/extracted_answer.md", "r", encoding="utf-8") as f:
        answer_md = f.read()

    job_id = "64188c7a-92a6-465e-84b1-18b6461cee61"
    now_str = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect("data/app.db")
    cur = conn.cursor()

    # Update providerrun
    cur.execute(
        "UPDATE providerrun SET status = 'ok', answer_md = ?, finished_at = ? WHERE subtask_id LIKE ?",
        (answer_md, now_str, f"%{job_id}%"),
    )

    # Update subtask
    cur.execute(
        "UPDATE subtask SET status = 'completed' WHERE job_id = ?",
        (job_id,),
    )

    # Update job
    runs = [{
        "provider": "chatgpt",
        "status": "ok",
        "elapsed_ms": 72368,
        "answer_markdown": answer_md.strip(),
        "error": None,
    }]
    report = (
        "# Research response\n\n"
        f"## Chatgpt response\n\n{answer_md.strip()}\n\n"
        "The provider response is shown as returned; claims have not been independently verified.\n"
    )

    cur.execute(
        """UPDATE job
           SET status = 'completed',
               error = NULL,
               subtasks_total = 1,
               subtasks_done = 1,
               provider_runs_json = ?,
               report_markdown = ?,
               finished_at = ?,
               updated_at = ?
           WHERE id = ?""",
        (json.dumps(runs), report, now_str, now_str, job_id),
    )

    # Add completion event
    cur.execute(
        """INSERT INTO jobevent (job_id, status, subtasks_total, subtasks_done, created_at, event_type, provider, step, message)
           VALUES (?, 'completed', 1, 1, ?, 'progress', 'chatgpt', 'completed', 'Hoàn thành xử lý chatgpt (ok). Trạng thái phiên: completed.')""",
        (job_id, now_str),
    )

    conn.commit()
    conn.close()
    print("Successfully updated database for job", job_id)

if __name__ == "__main__":
    main()
