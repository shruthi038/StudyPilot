import json
from models.database import get_conn

def get_summaries_by_user(username: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, data FROM summaries WHERE username=?", (username,)).fetchall()
        return [{"id": r["id"], "data": json.loads(r["data"])} for r in rows]

def upsert_summary(summary_id: str, username: str, data: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO summaries (id, username, data) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET data=excluded.data""",
            (summary_id, username, json.dumps(data, ensure_ascii=False)),
        )

def delete_summary(summary_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM summaries WHERE id=?", (summary_id,))
