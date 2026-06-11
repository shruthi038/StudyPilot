import streamlit as st
from controllers.auth_controller import login_user

def render_login_page():
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            """<div style='text-align:center;margin-bottom:2rem;'>
                <div style='font-size:2.5rem;'>✈️</div>
                <h1 style='font-weight:900;font-size:2rem;margin:0.3rem 0 0;letter-spacing:-1px;
                    background:linear-gradient(135deg,#4F46E5,#7C3AED);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
                    StudyPilot
                </h1>
                <p style='color:var(--text-muted);font-size:0.88rem;margin:4px 0 0;'>Your AI Learning Companion</p>
            </div>""",
            unsafe_allow_html=True,
        )
        with st.container(border=True):

            av = st.session_state["auth_view"]
    
            if av == "welcome":
                if st.button("Sign In", use_container_width=True, type="primary"):
                    st.session_state["auth_view"] = "login"
                    st.rerun()
                st.write("")
                if st.button("Create Account", use_container_width=True):
                    st.session_state["auth_view"] = "register"
                    st.session_state["reg_step"]  = "input_email"
                    st.rerun()
    
            elif av == "login":
                st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Sign In</h3>", unsafe_allow_html=True)
                with st.form("login_form"):
                    u   = st.text_input("Username")
                    p   = st.text_input("Password", type="password")
                    sub = st.form_submit_button("Sign In →", use_container_width=True)
                if sub:
                    if login_user(u.strip(), p.strip()):
                        st.session_state["page"]         = "landing"
                        st.session_state["current_view"] = "home"
                        intended = st.session_state.pop("_intended_view", None)
                        if intended:
                            st.session_state["current_view"] = intended
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                cl, cr = st.columns(2)
                with cl:
                    if st.button("← Back", key="back_login"):
                        st.session_state["auth_view"] = "welcome"
                        st.session_state["page"]      = "landing"
                        st.rerun()
                with cr:
                    if st.button("Forgot Password?", key="forgot_btn"):
                        st.session_state["auth_view"]   = "forgot_password"
                        st.session_state["forgot_step"] = "verify_email"
                        st.rerun()
    
            elif av == "register":
                render_signup_flow()
    
            elif av == "forgot_password":
                render_forgot_password_flow()
