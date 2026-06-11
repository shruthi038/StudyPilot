import streamlit as st
from models.user_model import get_user_by_username, upsert_user
from models.chat_model import get_chats_by_user
from models.summary_model import get_summaries_by_user
from models.planner_model import get_plans_by_user
from utils.helpers import hash_password

def login_user(username: str, password: str) -> bool:
    user = get_user_by_username(username)
    if user and user["password"] == hash_password(password):
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        load_user_data(username)
        return True
    return False

def register_user(username: str, email: str, password: str) -> bool:
    if get_user_by_username(username):
        return False
    upsert_user(username, email, hash_password(password))
    return True

def load_user_data(username: str):
    chats = get_chats_by_user(username)
    st.session_state["all_chats"] = {c["id"]: c["messages"] for c in chats}
    
    summaries = get_summaries_by_user(username)
    st.session_state["all_summaries"] = {s["id"]: s["data"] for s in summaries}
    
    plans = get_plans_by_user(username)
    st.session_state["all_plans"] = {p["id"]: p["data"] for p in plans}
    
    if chats:
        st.session_state["active_chat_id"] = chats[0]["id"]
    if summaries:
        st.session_state["active_summary_id"] = summaries[0]["id"]
    if plans:
        st.session_state["active_planner_id"] = plans[0]["id"]
    
    st.session_state["users_loaded"] = True

def save_all_data():
    username = st.session_state.get("username")
    if not username: return
    for cid, msgs in st.session_state.get("all_chats", {}).items():
        upsert_chat(cid, username, msgs)
    for sid, data in st.session_state.get("all_summaries", {}).items():
        upsert_summary(sid, username, data)
    for pid, data in st.session_state.get("all_plans", {}).items():
        upsert_plan(pid, username, data)

def logout_user():
    save_all_data()
    sidebar_pref = st.session_state.get("sidebar_open", True)
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["all_chats"] = {}
    st.session_state["all_summaries"] = {}
    st.session_state["all_plans"] = {}
    st.session_state["active_chat_id"] = ""
    st.session_state["active_summary_id"] = ""
    st.session_state["active_planner_id"] = ""
    st.session_state["auth_view"] = "welcome"
    st.session_state["page"] = "landing"
    st.session_state["current_view"] = "home"
    st.session_state["nav_history_stack"] = []
    st.session_state["sidebar_open"] = sidebar_pref
