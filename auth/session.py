import streamlit as st
from controllers.auth_controller import logout_user

def _do_logout():
    """Centralised logout — preserves sidebar preference."""
    logout_user()
    st.rerun()

def _require_login(view):
    """Redirect to login if user is not authenticated."""
    st.session_state["page"] = "login"
    st.session_state["auth_view"] = "login"
    st.session_state["_intended_view"] = view
    st.rerun()
