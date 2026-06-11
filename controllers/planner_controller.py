import streamlit as st
from models.planner_model import upsert_plan, delete_plan

def save_current_plan(plan_id: str, data: dict):
    username = st.session_state.get("username")
    if username:
        upsert_plan(plan_id, username, data)
    if "all_plans" in st.session_state:
        st.session_state["all_plans"][plan_id] = data

def remove_plan(plan_id: str):
    username = st.session_state.get("username")
    if username:
        delete_plan(plan_id)
    if plan_id in st.session_state.get("all_plans", {}):
        del st.session_state["all_plans"][plan_id]
