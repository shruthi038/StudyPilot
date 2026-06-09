import streamlit as st

def render_profile_view():
    st.markdown(
        "<h2 class='view-title'>👤 Profile</h2>"
        "<p class='view-subtitle'>Your account details and productivity stats</p>",
        unsafe_allow_html=True,
    )
    uid   = st.session_state["username"]
    email = st.session_state["user_db"].get(uid, {}).get("identity", "N/A")
    initial         = uid[0].upper() if uid else "?"
    total_chats     = len(st.session_state.get("all_chats",     {}))
    total_summaries = len(st.session_state.get("all_summaries", {}))
    total_plans     = len(st.session_state.get("all_plans",     {}))
    st.markdown(
        f"""<div class='content-card' style='max-width:600px;'>
            <div style='display:flex;align-items:center;gap:20px;margin-bottom:2rem;'>
                <div class='sb-avatar-lg'>{initial}</div>
                <div>
                    <h3 style='margin:0;font-weight:800;color:var(--text-primary);'>{uid}</h3>
                    <span style='color:var(--text-muted);font-size:0.9rem;'>{email}</span>
                </div>
            </div>
            <p class='card-label'>Productivity Insights</p>
            <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;'>
                <div class='stat-card'><div class='stat-num'>{total_chats}</div><div class='stat-label'>Tutor Chats</div></div>
                <div class='stat-card'><div class='stat-num'>{total_summaries}</div><div class='stat-label'>Summaries</div></div>
                <div class='stat-card'><div class='stat-num'>{total_plans}</div><div class='stat-label'>Plans</div></div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
