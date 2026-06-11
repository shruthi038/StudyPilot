import streamlit as st
from models.summary_model import upsert_summary, delete_summary

def save_current_summary(summary_id: str, data: dict):
    username = st.session_state.get("username")
    if username:
        upsert_summary(summary_id, username, data)
    if "all_summaries" in st.session_state:
        st.session_state["all_summaries"][summary_id] = data

def remove_summary(summary_id: str):
    username = st.session_state.get("username")
    if username:
        delete_summary(summary_id)
    if summary_id in st.session_state.get("all_summaries", {}):
        del st.session_state["all_summaries"][summary_id]
