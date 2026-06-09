import streamlit as st
from auth.session import _do_logout, _require_login

def render_navbar():
    """Sticky top navbar: ☰ + logo | Features popover | auth/profile."""
    is_logged_in = st.session_state["logged_in"]

    # Three flush sections: toggle+logo | spacer | features | auth
    c_toggle, c_logo, c_spacer, c_feat, c_auth = st.columns([0.8, 1.5, 5.3, 1.5, 2.0])

    # ── Toggle ──
    with c_toggle:
        icon = "✕" if st.session_state.get("sidebar_open", True) else "☰"
        if st.button(icon, key="nav_toggle", help="Toggle sidebar"):
            st.session_state["sidebar_open"] = not st.session_state.get("sidebar_open", True)
            st.rerun()

    # ── Logo ──
    with c_logo:
        if st.button("StudyPilot", key="nav_logo"):
            st.session_state["current_view"] = "home"
            st.session_state["page"]         = "landing"
            st.rerun()

    with c_spacer:
        st.empty()

    # ── Features popover (center) ──
    with c_feat:
        with st.popover("Features  ▾", use_container_width=True):
            feature_list = [
                ("💬", "Tutor",           "chat"),
                ("📝", "Smart Summarizer", "summary"),
                ("📅", "Adaptive Planner", "planner"),
            ]
            for f_icon, f_label, f_view in feature_list:
                if st.button(f"{f_icon}  {f_label}", key=f"feat_{f_view}_nav", use_container_width=True):
                    if not is_logged_in:
                        _require_login(f_view)
                    else:
                        st.session_state["current_view"] = f_view
                        st.rerun()

    # ── Auth / profile (right) ──
    with c_auth:
        if is_logged_in:
            uname = st.session_state["username"]
            with st.popover(f"{uname}", use_container_width=True):
                if st.button("Profile",  key="nav_profile",  use_container_width=True):
                    st.session_state["current_view"] = "profile"
                    st.rerun()
                if st.button("Settings", key="nav_settings", use_container_width=True):
                    st.session_state["current_view"] = "settings"
                    st.rerun()
                st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)
                if st.button("Logout", key="nav_logout_pop", use_container_width=True):
                    _do_logout()
        else:
            cl, cr = st.columns(2)
            with cl:
                if st.button("Login", key="nav_login", type="primary", use_container_width=True):
                    st.session_state["page"]      = "login"
                    st.session_state["auth_view"] = "login"
                    st.rerun()
            with cr:
                if st.button("Sign Up", key="nav_register", type="primary", use_container_width=True):
                    st.session_state["page"]      = "register"
                    st.session_state["auth_view"] = "register"
                    st.session_state["reg_step"]  = "input_email"
                    st.rerun()

    st.markdown("<div class='navbar-divider'></div>", unsafe_allow_html=True)
