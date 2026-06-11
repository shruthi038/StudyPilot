import random
import datetime
import streamlit as st
from models.user_model import get_all_users, get_user_by_username, upsert_user
from utils.helpers import hash_password, is_otp_expired, send_otp_email

def render_forgot_password_flow():
    st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Reset Password</h3>", unsafe_allow_html=True)
    if st.session_state["forgot_step"] == "verify_email":
        with st.form("forgot_form"):
            re_email = st.text_input("Registered Email")
            lookup   = st.form_submit_button("Send Reset OTP →", use_container_width=True)
        if lookup:
            users = get_all_users()
            found = next((u["username"] for u in users if u["email"] == re_email.strip()), None)
            if found:
                otp = str(random.randint(100000, 999999))
                ok, err = send_otp_email(re_email.strip(), otp)
                if ok:
                    st.session_state.update({
                        "recovery_target_user": found, "generated_otp": otp,
                        "otp_timestamp": datetime.datetime.now(), "forgot_step": "verify_otp",
                    })
                    st.success("OTP sent!")
                    st.rerun()
                else:
                    st.error(f"Failed: {err}")
            else:
                st.error("No account found.")
        if st.button("← Back", key="back_forgot"):
            st.session_state["auth_view"] = "login"
            st.rerun()

    elif st.session_state["forgot_step"] == "verify_otp":
        st.info("📬 OTP sent to your registered email.")
        if not is_otp_expired():
            with st.form("forgot_otp_form"):
                rotp = st.text_input("6-Digit OTP", max_chars=6)
                vrfy = st.form_submit_button("Verify →", use_container_width=True)
            if vrfy:
                if rotp.strip() == st.session_state["generated_otp"]:
                    st.session_state["forgot_step"] = "reset_password"
                    st.rerun()
                else:
                    st.error("Incorrect OTP.")
        else:
            st.error("⏰ OTP expired.")

    elif st.session_state["forgot_step"] == "reset_password":
        with st.form("reset_form"):
            np1  = st.text_input("New Password",     type="password")
            np2  = st.text_input("Confirm Password", type="password")
            save = st.form_submit_button("Update Password →", use_container_width=True)
        if save:
            if np1 != np2:   st.error("Don't match.")
            elif len(np1) < 4: st.error("Too short.")
            else:
                target   = st.session_state["recovery_target_user"]
                new_hash = hash_password(np1.strip())
                user_info = get_user_by_username(target)
                if user_info:
                    upsert_user(target, user_info["email"], new_hash)
                st.success("Password updated! Sign in now.")
                st.session_state["auth_view"] = "login"
                st.rerun()
