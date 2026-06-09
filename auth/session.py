import streamlit as st
from database.database import save_data

def _do_logout():
    """Centralised logout — preserves sidebar preference."""
    save_data()
    sidebar_pref = st.session_state.get("sidebar_open", True)
    for k, v in {
        "logged_in": False, "username": "", "auth_view": "welcome",
        "page": "landing", "current_view": "home",
        "all_chats": {}, "all_summaries": {}, "all_plans": {},
        "active_chat_id": "", "active_summary_id": "", "active_planner_id": "",
        "nav_history_stack": [], "activity_filter": "All",
    }.items():
        st.session_state[k] = v
    st.session_state["sidebar_open"] = sidebar_pref
    st.rerun()

def _require_login(view):
    """Redirect to login if user is not authenticated."""
    st.session_state["page"] = "login"
    st.session_state["auth_view"] = "login"
    st.session_state["_intended_view"] = view
    st.rerun()
