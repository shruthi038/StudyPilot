import streamlit as st

def update_theme(new_theme: str):
    st.session_state["theme"] = new_theme
    
def update_view(view_name: str):
    st.session_state["current_view"] = view_name

from models.user_model import get_user_by_username, upsert_user
from models.chat_model import delete_chat
from models.summary_model import delete_summary
from models.planner_model import delete_plan
from utils.helpers import hash_password

def change_password(uid, old_pwd, new_pwd) -> bool:
    user = get_user_by_username(uid)
    if user and user["password"] == hash_password(old_pwd):
        upsert_user(uid, user["email"], hash_password(new_pwd))
        return True
    return False

def clear_user_history(uid):
    chats = st.session_state.get("all_chats", {}).keys()
    for cid in list(chats): delete_chat(cid)
    sums = st.session_state.get("all_summaries", {}).keys()
    for sid in list(sums): delete_summary(sid)
    plans = st.session_state.get("all_plans", {}).keys()
    for pid in list(plans): delete_plan(pid)
    
    st.session_state["all_chats"] = {}
    st.session_state["all_summaries"] = {}
    st.session_state["all_plans"] = {}
    st.session_state["active_chat_id"] = ""
    st.session_state["active_summary_id"] = ""
    st.session_state["active_planner_id"] = ""
