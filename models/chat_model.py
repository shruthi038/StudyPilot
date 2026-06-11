import json
from models.database import get_conn

def get_chats_by_user(username: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT id, messages FROM chats WHERE username=?", (username,)).fetchall()
        return [{"id": r["id"], "messages": json.loads(r["messages"])} for r in rows]

def upsert_chat(chat_id: str, username: str, messages: list):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO chats (id, username, messages) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET messages=excluded.messages""",
            (chat_id, username, json.dumps(messages, ensure_ascii=False)),
        )

def delete_chat(chat_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))
