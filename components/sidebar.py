import datetime
import streamlit as st
from database.database import save_data, delete_item_from_db, save_chat_immediately
from auth.session import _do_logout, _require_login
from styles.theme import save_user_theme

def _sidebar_mode():
    """'feature' for Chat/Summary/Planner; 'global' everywhere else."""
    return "feature" if st.session_state.get("current_view") in {"chat", "summary", "planner"} else "global"

def render_sidebar():
    mode = _sidebar_mode()
    if mode == "feature":
        _render_feature_sidebar()
    else:
        _render_global_sidebar()

def _render_global_sidebar():
    """Sidebar for Home, Analytics, Activity, Profile, Settings."""

    # ── Logo ──
    st.markdown(
        "<div class='sb-logo'>✈️ <span>StudyPilot</span></div>"
        "<div class='sb-tagline'>AI Learning Companion</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── User Profile ──
    if st.session_state["logged_in"]:
        uname   = st.session_state["username"]
        email   = st.session_state["user_db"].get(uname, {}).get("identity", "")
        initial = uname[0].upper()
        st.markdown(
            f"""<div class='sb-profile'>
                <div class='sb-avatar'>{initial}</div>
                <div>
                    <div class='sb-uname'>{uname}</div>
                    <div class='sb-email'>{email}</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Features nav ──
    st.markdown("<div class='sb-section-label'>FEATURES</div>", unsafe_allow_html=True)

    nav_items = [
        ("Home",             "home"),
        ("AI Tutor",         "chat"),
        ("Smart Summarizer", "summary"),
        ("Adaptive Planner", "planner"),
        ("Analytics",        "analytics"),
    ]
    protected = {"chat", "summary", "planner", "analytics"}

    for label, view in nav_items:
        is_active = st.session_state["current_view"] == view
        if is_active:
            st.markdown(f"<div class='nav-item-active'>{label}</div>", unsafe_allow_html=True)
        else:
            if st.button(label, key=f"sib_{view}", use_container_width=True):
                if view in protected and not st.session_state["logged_in"]:
                    _require_login(view)
                else:
                    st.session_state["current_view"] = view
                    st.rerun()

    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Activity ──
    st.markdown("<div class='sb-section-label'>ACTIVITY</div>", unsafe_allow_html=True)
    is_activity = st.session_state["current_view"] == "activity"
    if is_activity:
        st.markdown("<div class='nav-item-active'>Activity Dashboard</div>", unsafe_allow_html=True)
    else:
        if st.button("Activity Dashboard", key="sib_activity", use_container_width=True):
            if not st.session_state["logged_in"]:
                _require_login("activity")
            else:
                st.session_state["current_view"] = "activity"
                st.rerun()

    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Preferences ──
    st.markdown("<div class='sb-section-label'>PREFERENCES</div>", unsafe_allow_html=True)
    theme   = st.session_state.get("theme", "light")
    t_icon  = "☀️" if theme == "dark" else "🌙"
    t_label = "Light Mode" if theme == "dark" else "Dark Mode"
    if st.button(f"{t_icon}  {t_label}", key="sib_theme", use_container_width=True):
        new_theme = "light" if theme == "dark" else "dark"
        st.session_state["theme"] = new_theme
        if st.session_state["logged_in"]:
            save_user_theme(st.session_state["username"], new_theme)
        st.rerun()

    # ── Pinned Logout ──
    st.markdown("<div class='sb-spacer'></div>", unsafe_allow_html=True)
    if st.session_state["logged_in"]:
        st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)
        if st.button("Logout", key="sib_logout", use_container_width=True):
            _do_logout()

def _render_feature_sidebar():
    """Sidebar for AI Tutor / Summarizer / Planner — shows feature history only."""
    view = st.session_state["current_view"]

    # ── Compact profile ──
    if st.session_state["logged_in"]:
        uname   = st.session_state["username"]
        initial = uname[0].upper()
        st.markdown(
            f"""<div class='sb-profile-compact'>
                <div class='sb-avatar-sm'>{initial}</div>
                <div class='sb-uname'>{uname}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Back to Home ──
    if st.button("← Home", key="sib_back_home", use_container_width=True):
        st.session_state["current_view"] = "home"
        st.rerun()

    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Feature-specific history ──
    if view == "chat":
        st.markdown("<div class='sb-section-label'>CHAT HISTORY</div>", unsafe_allow_html=True)
        render_history_panel("chat", "Chat")
    elif view == "summary":
        st.markdown("<div class='sb-section-label'>SUMMARY HISTORY</div>", unsafe_allow_html=True)
        render_history_panel("summary", "Summary")
    elif view == "planner":
        st.markdown("<div class='sb-section-label'>PLAN HISTORY</div>", unsafe_allow_html=True)
        render_history_panel("planner", "Planner")

    # ── Pinned Logout ──
    st.markdown("<div class='sb-spacer'></div>", unsafe_allow_html=True)
    if st.session_state["logged_in"]:
        st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)
        if st.button("Logout", key="sib_logout_feat", use_container_width=True):
            _do_logout()

def render_history_panel(feature_key, friendly_name):
    """Compact history list for the contextual sidebar."""
    if feature_key == "chat":
        history_dict = st.session_state["all_chats"]
        active_id    = st.session_state["active_chat_id"]
    elif feature_key == "summary":
        history_dict = st.session_state["all_summaries"]
        active_id    = st.session_state["active_summary_id"]
    else:
        history_dict = st.session_state["all_plans"]
        active_id    = st.session_state["active_planner_id"]

    if st.button(f"＋  New {friendly_name}", use_container_width=True, key=f"new_{feature_key}_sb"):
        nid = f"{feature_key}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if feature_key == "chat":
            st.session_state["all_chats"][nid] = []
            st.session_state["active_chat_id"] = nid
            save_chat_immediately(nid, [], st.session_state["username"])
        elif feature_key == "summary":
            st.session_state["all_summaries"][nid] = {
                "text": "", "summary": "", "word_count": 80,
                "format_style": "Plain Text", "title": "Untitled Summary",
            }
            st.session_state["active_summary_id"] = nid
        else:
            st.session_state["all_plans"][nid] = {
                "subjects": "", "weak": "", "mood": "", "schedule": [], "title": "Untitled Plan",
            }
            st.session_state["active_planner_id"] = nid
        save_data()
        st.rerun()

    if not history_dict:
        st.markdown(
            f"<div class='sidebar-empty'>📂 No {friendly_name.lower()}s yet</div>",
            unsafe_allow_html=True,
        )
        return

    open_menu = st.session_state.get("active_menu_item_id", "")

    for item_id in list(history_dict.keys()):
        if feature_key == "chat":
            msgs  = history_dict[item_id]
            label = msgs[0]["text"][:24] + "…" if msgs else "Untitled Chat"
        else:
            label = history_dict[item_id].get("title", "Untitled")[:24]

        is_active = item_id == active_id
        is_open   = open_menu == item_id
        prefix    = "● " if is_active else ""

        col_sel, col_dot = st.columns([8, 2])
        with col_sel:
            if st.button(f"{prefix}{label}", key=f"sel_{item_id}_{feature_key}", use_container_width=True):
                if feature_key == "chat":      st.session_state["active_chat_id"]    = item_id
                elif feature_key == "summary": st.session_state["active_summary_id"] = item_id
                else:                          st.session_state["active_planner_id"]  = item_id
                st.rerun()
        with col_dot:
            if st.button("⋮", key=f"dots_{item_id}_{feature_key}", use_container_width=True):
                st.session_state["active_menu_item_id"] = item_id if not is_open else ""
                st.rerun()

        if is_open:
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("Rename", key=f"ren_{item_id}_{feature_key}", use_container_width=True):
                    st.session_state["editing_item_id"]       = item_id
                    st.session_state["rename_feature_target"] = feature_key
                    st.session_state["active_menu_item_id"]   = ""
                    st.rerun()
            with dc2:
                if st.button("Delete", key=f"del_{item_id}_{feature_key}", use_container_width=True):
                    del history_dict[item_id]
                    delete_item_from_db(feature_key, item_id)
                    st.session_state["active_menu_item_id"] = ""
                    if active_id == item_id:
                        remaining = list(history_dict.keys())
                        fallback  = remaining[0] if remaining else ""
                        if feature_key == "chat":      st.session_state["active_chat_id"]    = fallback
                        elif feature_key == "summary": st.session_state["active_summary_id"] = fallback
                        else:                          st.session_state["active_planner_id"]  = fallback
                    st.rerun()

    eid = st.session_state.get("editing_item_id", "")
    if eid in history_dict and st.session_state.get("rename_feature_target") == feature_key:
        with st.form(f"rename_form_{feature_key}"):
            new_title = st.text_input("New name", placeholder="Enter title…", label_visibility="collapsed")
            if st.form_submit_button("Save", use_container_width=True):
                if new_title.strip():
                    if feature_key != "chat":
                        history_dict[eid]["title"] = new_title.strip()
                    save_data()
                    st.session_state["editing_item_id"] = ""
                    st.rerun()
