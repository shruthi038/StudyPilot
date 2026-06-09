import streamlit as st

def render_login_required_view():
    st.markdown("<div style='padding-top:4rem;'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        view_name = st.session_state.get("current_view", "").replace("_", " ").title()
        st.markdown(
            f"""<div class='content-card' style='text-align:center;padding:3rem;'>
                <div style='font-size:3rem;margin-bottom:1rem;'>🔒</div>
                <h3 style='font-weight:800;color:var(--text-primary);margin:0 0 0.5rem;'>Sign in to continue</h3>
                <p style='color:var(--text-muted);margin:0 0 2rem;'>Access <strong>{view_name}</strong> and save your progress</p>
            </div>""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sign In", key="req_login", use_container_width=True, type="primary"):
                st.session_state["page"]      = "login"
                st.session_state["auth_view"] = "login"
                st.rerun()
        with c2:
            if st.button("Create Account", key="req_reg", use_container_width=True):
                st.session_state["page"]      = "register"
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"]  = "input_email"
                st.rerun()
