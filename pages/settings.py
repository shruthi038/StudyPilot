import streamlit as st
from controllers.settings_controller import change_password, clear_user_history

def render_settings_view():
    st.markdown(
        "<h2 class='view-title'>⚙️ Settings</h2>"
        "<p class='view-subtitle'>Manage your account and preferences</p>",
        unsafe_allow_html=True,
    )
    uid = st.session_state["username"]
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<p class='card-label'>🔒 Change Password</p>", unsafe_allow_html=True)
    with st.form("settings_form"):
        old_pwd  = st.text_input("Current Password", type="password")
        new_pwd  = st.text_input("New Password",     type="password")
        conf_pwd = st.text_input("Confirm Password", type="password")
        save_btn = st.form_submit_button("Update Password", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if save_btn:
        if not old_pwd or not new_pwd or not conf_pwd:
            st.error("Please fill all fields.")
        elif new_pwd != conf_pwd:
            st.error("Passwords don't match.")
        elif len(new_pwd) < 4:
            st.error("Password must be at least 4 characters.")
        else:
            if change_password(uid, old_pwd, new_pwd):
                st.success("Password updated!")
            else:
                st.error("Incorrect current password.")

    st.markdown(
        "<div class='content-card' style='border:1px solid rgba(239,68,68,0.3);margin-top:1.5rem;'>",
        unsafe_allow_html=True,
    )
    st.markdown("<p class='card-label' style='color:#EF4444;'>⚠️ Danger Zone</p>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:var(--text-muted);font-size:0.88rem;margin:0 0 1rem 0;'>"
        "Permanently delete all chats, summaries, and plans. Cannot be undone.</p>",
        unsafe_allow_html=True,
    )
    if st.button("🗑️ Clear All History", key="clear_all", use_container_width=True):
        clear_user_history(uid)
        st.toast("History cleared! 🧹")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
