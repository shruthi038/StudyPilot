from models.database import get_conn

def get_all_users() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT username, email, password FROM users").fetchall()
        return [dict(r) for r in rows]

def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT username, email, password FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

def upsert_user(username: str, email: str, password_hash: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (username, email, password) VALUES (?, ?, ?)
               ON CONFLICT(username) DO UPDATE SET
                   email=excluded.email, password=excluded.password""",
            (username, email, password_hash),
        )
