import streamlit as st
from database.database import init_db, get_conn
from styles.theme import get_user_theme
from styles.css import inject_css
from components.navbar import render_navbar
from components.sidebar import render_sidebar
from components.common import render_login_required_view
from auth.login import render_login_page
from pages.home import render_home_view
from pages.ai_tutor import render_chat_view
from pages.summarizer import render_summary_view
from pages.planner import render_planner_view
from pages.analytics import render_analytics_view
from components.activity import render_activity_view
from pages.profile import render_profile_view
from pages.settings import render_settings_view

def render_main_content():
    """Routes to the correct view."""
    # Auth routing
    if not st.session_state["logged_in"] and st.session_state["page"] in ("login", "register"):
        render_login_page()
        return

    protected = {"chat", "summary", "planner", "analytics", "activity", "history", "profile", "settings"}
    view = st.session_state["current_view"]

    if view in protected and not st.session_state["logged_in"]:
        render_login_required_view()
        return

    if   view == "home":      render_home_view()
    elif view == "chat":      render_chat_view()
    elif view == "summary":   render_summary_view()
    elif view == "planner":   render_planner_view()
    elif view == "analytics": render_analytics_view()
    elif view == "activity":  render_activity_view()
    elif view == "profile":   render_profile_view()
    elif view == "settings":  render_settings_view()
    else:
        render_home_view()

def render_app_shell():
    """Top-level shell: sidebar + navbar + content."""
    # Render sidebar (always, for all users — hidden via CSS when collapsed)
    with st.sidebar:
        render_sidebar()

    # Navbar
    render_navbar()

    # Main content
    render_main_content()


# ============================================================
# ENTRY POINT
# ============================================================

st.set_page_config(page_title="StudyPilot", page_icon="assets/logo_light.png", layout="wide")

init_db()

defaults = {
    "theme": "light",
    "page": "landing",
    "logged_in": False, "username": "", "message_history": {},
    "current_view": "home", "auth_view": "welcome",
    "reg_step": "input_email", "forgot_step": "verify_email",
    "generated_otp": None, "otp_timestamp": None,
    "temp_identity": "", "recovery_target_user": "",
    "editing_item_id": "", "rename_feature_target": "",
    "active_menu_item_id": "", "active_bubble_menu_id": "",
    "show_copy_summary": False, "user_db": {},
    "all_chats": {}, "active_chat_id": "",
    "all_summaries": {}, "active_summary_id": "",
    "all_plans": {}, "active_planner_id": "",
    "nav_history_stack": [],
    "sidebar_open": True,
    "activity_filter": "All",
    "_intended_view": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "users_loaded" not in st.session_state:
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT username, email, password FROM users").fetchall()
            st.session_state["user_db"] = {
                r["username"]: {"identity": r["email"], "password": r["password"]}
                for r in rows
            }
    except Exception:
        pass
    st.session_state["users_loaded"] = True

if st.session_state["logged_in"] and st.session_state["username"]:
    st.session_state["theme"] = get_user_theme(st.session_state["username"])

inject_css(st.session_state.get("theme", "light"))
render_app_shell()
