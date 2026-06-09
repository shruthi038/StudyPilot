import sqlite3
import json
import streamlit as st
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

def save_data():
    try:
        username = st.session_state.get("username", "")
        if not username:
            return
        with get_conn() as conn:
            for uname, meta in st.session_state.get("user_db", {}).items():
                conn.execute(
                    """INSERT INTO users (username, email, password) VALUES (?, ?, ?)
                       ON CONFLICT(username) DO UPDATE SET
                           email=excluded.email, password=excluded.password""",
                    (uname, meta["identity"], meta["password"]),
                )
            for cid, msgs in st.session_state.get("all_chats", {}).items():
                conn.execute(
                    """INSERT INTO chats (id, username, messages) VALUES (?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET messages=excluded.messages""",
                    (cid, username, json.dumps(msgs, ensure_ascii=False)),
                )
            for sid, data in st.session_state.get("all_summaries", {}).items():
                conn.execute(
                    """INSERT INTO summaries (id, username, data) VALUES (?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET data=excluded.data""",
                    (sid, username, json.dumps(data, ensure_ascii=False)),
                )
            for pid, data in st.session_state.get("all_plans", {}).items():
                conn.execute(
                    """INSERT INTO plans (id, username, data) VALUES (?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET data=excluded.data""",
                    (pid, username, json.dumps(data, ensure_ascii=False)),
                )
    except Exception as e:
        st.toast(f"⚠️ Save warning: {e}", icon="⚠️")

def save_chat_immediately(chat_id: str, messages: list, username: str):
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO chats (id, username, messages) VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET messages=excluded.messages""",
                (chat_id, username, json.dumps(messages, ensure_ascii=False)),
            )
    except Exception:
        pass

def delete_item_from_db(feature_key, item_id):
    table_map = {"chat": "chats", "summary": "summaries", "planner": "plans"}
    table = table_map.get(feature_key)
    if not table:
        return
    try:
        with get_conn() as conn:
            conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    except Exception:
        pass

def load_data():
    try:
        username = st.session_state.get("username", "")
        if not username:
            return
        with get_conn() as conn:
            rows = conn.execute("SELECT username, email, password FROM users").fetchall()
            st.session_state["user_db"] = {
                r["username"]: {"identity": r["email"], "password": r["password"]}
                for r in rows
            }
            rows = conn.execute(
                "SELECT id, messages FROM chats WHERE username=?", (username,)
            ).fetchall()
            st.session_state["all_chats"] = {
                r["id"]: json.loads(r["messages"]) for r in rows
            } if rows else {}
            rows = conn.execute(
                "SELECT id, data FROM summaries WHERE username=?", (username,)
            ).fetchall()
            st.session_state["all_summaries"] = {
                r["id"]: json.loads(r["data"]) for r in rows
            } if rows else {}
            rows = conn.execute(
                "SELECT id, data FROM plans WHERE username=?", (username,)
            ).fetchall()
            st.session_state["all_plans"] = {
                r["id"]: json.loads(r["data"]) for r in rows
            } if rows else {}
            if st.session_state["all_chats"]:
                st.session_state["active_chat_id"] = list(st.session_state["all_chats"].keys())[0]
            if st.session_state["all_summaries"]:
                st.session_state["active_summary_id"] = list(st.session_state["all_summaries"].keys())[0]
            if st.session_state["all_plans"]:
                st.session_state["active_planner_id"] = list(st.session_state["all_plans"].keys())[0]
    except Exception:
        pass
