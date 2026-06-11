import json
from models.database import get_conn

def get_plans_by_user(username: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, data FROM plans WHERE username=?", (username,)).fetchall()
        return [{"id": r["id"], "data": json.loads(r["data"])} for r in rows]

def upsert_plan(plan_id: str, username: str, data: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO plans (id, username, data) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET data=excluded.data""",
            (plan_id, username, json.dumps(data, ensure_ascii=False)),
        )

def delete_plan(plan_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM plans WHERE id=?", (plan_id,))
