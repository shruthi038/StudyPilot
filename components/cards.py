import streamlit as st

def render_stat_card(icon: str, num: int, label: str, color: str = None):
    color_style = f" style='color:{color};'" if color else ""
    st.markdown(
        f"""<div class='stat-card'>
            <div class='stat-icon'>{icon}</div>
            <div class='stat-num'{color_style}>{num}</div>
            <div class='stat-label'>{label}</div>
        </div>""",
        unsafe_allow_html=True,
    )

def render_recent_item(icon: str, label: str, item_id: str, view: str, key: str, idx: int):
    rl, rr = st.columns([9, 1])
    with rl:
        st.markdown(
            f"<div class='recent-item'><span>{icon}</span> {label}</div>",
            unsafe_allow_html=True,
        )
    with rr:
        if st.button("→", key=f"recent_{item_id}_{idx}", use_container_width=True):
            st.session_state[key] = item_id
            st.session_state["current_view"] = view
            st.rerun()
