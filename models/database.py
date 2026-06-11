import sqlite3
from utils.constants import DB_FILE
from utils.helpers import hash_password

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                email    TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id       TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                messages TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id       TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                data     TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id       TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                data     TEXT NOT NULL DEFAULT '{}'
            )
        """)
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing == 0:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                ("admin", "admin@studypilot.com", hash_password("student123")),
            )
