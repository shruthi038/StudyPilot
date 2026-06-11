import random
import datetime
import streamlit as st
from controllers.auth_controller import register_user, load_user_data
from models.user_model import get_all_users
from utils.helpers import hash_password, validate_email, is_otp_expired, send_otp_email

def render_signup_flow():
    st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Create Account</h3>", unsafe_allow_html=True)
    steps   = ["Email", "Verify", "Setup"]
    step_idx = {"input_email": 0, "verify_otp": 1, "set_credentials": 2}.get(st.session_state["reg_step"], 0)
    dots_html = ""
    for si, s_label in enumerate(steps):
        color  = "var(--accent)" if si <= step_idx else "var(--text-muted)"
        weight = "700" if si == step_idx else "400"
        dots_html += f"<span style='color:{color};font-weight:{weight};font-size:0.82rem;'>{s_label}</span>"
        if si < len(steps) - 1:
            lc = "var(--accent)" if si < step_idx else "var(--border)"
            dots_html += f"<span style='display:inline-block;width:30px;height:2px;background:{lc};vertical-align:middle;margin:0 8px;'></span>"
    st.markdown(f"<div style='text-align:center;margin-bottom:1.5rem;'>{dots_html}</div>", unsafe_allow_html=True)

    if st.session_state["reg_step"] == "input_email":
        with st.form("reg_email_form"):
            ei   = st.text_input("Email Address", placeholder="name@gmail.com")
            send = st.form_submit_button("Send Verification Code →", use_container_width=True)
        if send:
            if not validate_email(ei.strip()):
                st.error("Enter a valid email.")
            else:
                existing = [u["email"] for u in get_all_users()]
                if ei.strip() in existing:
                    st.error("Account with this email already exists.")
                else:
                    otp = str(random.randint(100000, 999999))
                    ok, err = send_otp_email(ei.strip(), otp)
                    if ok:
                        st.session_state.update({
                            "generated_otp": otp, "otp_timestamp": datetime.datetime.now(),
                            "temp_identity": ei.strip(), "reg_step": "verify_otp",
                        })
                        st.success(f"OTP sent to {ei.strip()}!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")
        if st.button("← Cancel"):
            st.session_state["auth_view"] = "welcome"
            st.session_state["page"]      = "landing"
            st.rerun()

    elif st.session_state["reg_step"] == "verify_otp":
        st.info(f"📬 OTP sent to **{st.session_state['temp_identity']}**")
        if is_otp_expired():
            st.error("⏰ OTP expired.")
            if st.button("Resend OTP", use_container_width=True):
                otp = str(random.randint(100000, 999999))
                ok, _ = send_otp_email(st.session_state["temp_identity"], otp)
                if ok:
                    st.session_state.update({"generated_otp": otp, "otp_timestamp": datetime.datetime.now()})
                    st.success("New OTP sent!")
                    st.rerun()
        else:
            with st.form("otp_form"):
                entered = st.text_input("6-Digit OTP", max_chars=6, placeholder="______")
                verify  = st.form_submit_button("Verify →", use_container_width=True)
            if verify:
                if entered.strip() == st.session_state["generated_otp"]:
                    st.session_state["reg_step"] = "set_credentials"
                    st.rerun()
                else:
                    st.error("Incorrect OTP.")
            if st.button("← Back", key="back_otp"):
                st.session_state["reg_step"] = "input_email"
                st.rerun()

    elif st.session_state["reg_step"] == "set_credentials":
        st.success(f"✅ Email verified: {st.session_state['temp_identity']}")
        with st.form("cred_form"):
            ru   = st.text_input("Choose a Username")
            rp   = st.text_input("Choose a Password", type="password")
            rc   = st.text_input("Confirm Password",  type="password")
            done = st.form_submit_button("Create Account →", use_container_width=True)
        if done:
            existing_users = get_all_users()
            existing_emails = [u["email"] for u in existing_users]
            existing_usernames = [u["username"] for u in existing_users]
            
            if len(ru.strip()) < 3:      st.error("Username too short.")
            elif ru.strip() in existing_usernames: st.error("Username taken.")
            elif st.session_state["temp_identity"] in existing_emails: st.error("Email already registered.")
            elif rp != rc:               st.error("Passwords don't match.")
            elif len(rp) < 4:            st.error("Password too short.")
            else:
                if register_user(ru.strip(), st.session_state["temp_identity"], rp.strip()):
                    st.session_state["logged_in"]    = True
                    st.session_state["username"]     = ru.strip()
                    load_user_data(ru.strip())
                    st.session_state["page"]         = "landing"
                    st.session_state["current_view"] = "home"
                    st.rerun()
                else:
                    st.error("Registration failed.")
                st.rerun()
