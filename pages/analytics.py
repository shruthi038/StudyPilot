import streamlit as st
from components.cards import render_stat_card

def render_analytics_view():
    st.markdown(
        "<h2 class='view-title'>📊 Study Analytics</h2>"
        "<p class='view-subtitle'>Track your learning patterns, productivity, and wellbeing</p>",
        unsafe_allow_html=True,
    )
    total_chats     = len(st.session_state.get("all_chats",     {}))
    total_summaries = len(st.session_state.get("all_summaries", {}))
    total_plans     = len(st.session_state.get("all_plans",     {}))
    total_minutes   = sum(p.get("total_minutes", 0) for p in st.session_state.get("all_plans", {}).values())
    modes = {"classic": 0, "mellow": 0, "gentle": 0}
    moods = {"positive": 0, "neutral": 0, "negative": 0}
    for plan in st.session_state.get("all_plans", {}).values():
        modes[plan.get("mode", "classic")] = modes.get(plan.get("mode", "classic"), 0) + 1
        moods[plan.get("mood_cat", "neutral")] = moods.get(plan.get("mood_cat", "neutral"), 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    stat_items = [
        (c1, "⏱️", total_minutes,   "Study Minutes", "var(--accent)"),
        (c2, "📅", total_plans,     "Schedules",     "#10B981"),
        (c3, "💬", total_chats,     "Tutor Queries", "#6366F1"),
        (c4, "📝", total_summaries, "Summaries",     "#F59E0B"),
    ]
    for col, icon, num, label, color in stat_items:
        with col:
            render_stat_card(icon, num, label, color)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("<div class='content-card' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
        st.markdown("<p class='card-label'>🎯 Pomodoro Breakdown</p>", unsafe_allow_html=True)
        if total_plans == 0:
            st.caption("No study plans created yet.")
        else:
            total_m = max(sum(modes.values()), 1)
            for label, count, color in [
                ("⚡ Classic", modes["classic"], "#10B981"),
                ("🌙 Mellow",  modes["mellow"],  "#F59E0B"),
                ("💙 Gentle",  modes["gentle"],  "#EF4444"),
            ]:
                pct = int(count / total_m * 100)
                st.markdown(
                    f"""<div style='margin-bottom:12px;'>
                        <div style='display:flex;justify-content:space-between;margin-bottom:4px;'>
                            <span style='color:var(--text-primary);font-weight:600;font-size:0.88rem;'>{label}</span>
                            <span style='color:{color};font-weight:700;'>{count}</span>
                        </div>
                        <div style='background:var(--bg-secondary);border-radius:8px;height:6px;overflow:hidden;'>
                            <div style='width:{pct}%;height:100%;background:{color};border-radius:8px;'></div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='content-card' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
        st.markdown("<p class='card-label'>🧠 Wellbeing Insights</p>", unsafe_allow_html=True)
        if total_plans == 0:
            st.caption("No emotional feedback collected yet.")
        else:
            total_mood = max(sum(moods.values()), 1)
            for label, count, color in [
                ("🌟 Positive", moods["positive"], "#10B981"),
                ("🎯 Neutral",  moods["neutral"],  "#6366F1"),
                ("💙 Stressed", moods["negative"], "#EF4444"),
            ]:
                pct = int(count / total_mood * 100)
                st.markdown(
                    f"""<div style='margin-bottom:12px;'>
                        <div style='display:flex;justify-content:space-between;margin-bottom:4px;'>
                            <span style='color:var(--text-primary);font-weight:600;font-size:0.88rem;'>{label}</span>
                            <span style='color:{color};font-weight:700;'>{count}</span>
                        </div>
                        <div style='background:var(--bg-secondary);border-radius:8px;height:6px;overflow:hidden;'>
                            <div style='width:{pct}%;height:100%;background:{color};border-radius:8px;'></div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)
