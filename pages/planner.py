import datetime
import streamlit as st
from services.planner import generate_schedule
from database.database import save_data

def render_planner_view():
    st.markdown(
        "<h2 class='view-title'>📅 Adaptive Study Planner</h2>"
        "<p class='view-subtitle'>Your schedule adapts to your mood — because wellbeing matters</p>",
        unsafe_allow_html=True,
    )

    if not st.session_state["all_plans"]:
        nid = f"planner_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state["all_plans"][nid] = {
            "subjects": "", "weak": "", "mood": "", "schedule": [], "title": "Untitled Plan",
        }
        st.session_state["active_planner_id"] = nid
        save_data()
    elif not st.session_state["active_planner_id"]:
        st.session_state["active_planner_id"] = list(st.session_state["all_plans"].keys())[0]

    plan = st.session_state["all_plans"].get(st.session_state["active_planner_id"])

    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    with st.form("planner_form"):
        c1, c2 = st.columns(2)
        with c1:
            subj       = st.text_input("Subjects", value=plan["subjects"], placeholder="e.g. Python, ML, DSA")
            start_time = st.time_input("Start Time", datetime.time(9, 0))
        with c2:
            weak     = st.text_input("Weak Subject", value=plan["weak"], placeholder="e.g. Python")
            end_time = st.time_input("End Time", datetime.time(12, 0))
        mood = st.text_input("How are you feeling right now?", value=plan["mood"],
                             placeholder="e.g. tired, stressed, excited…")
        gen  = st.form_submit_button("Generate My Schedule", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if gen:
        try:
            plan = generate_schedule(subj, weak, mood, start_time, end_time, plan)
            st.session_state["all_plans"][st.session_state["active_planner_id"]] = plan
            save_data()
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    if plan.get("schedule"):
        mood_cat = plan.get("mood_cat", "neutral")
        mood_colors = {"positive": "#10B981", "neutral": "#6366F1", "negative": "#EF4444"}
        mood_bg     = {"positive": "rgba(16,185,129,0.08)", "neutral": "rgba(99,102,241,0.08)", "negative": "rgba(239,68,68,0.08)"}
        mood_icons  = {"positive": "🌟", "neutral": "🎯", "negative": "💙"}

        st.markdown(
            f"""<div class='content-card' style='border-left:4px solid {mood_colors[mood_cat]};background:{mood_bg[mood_cat]};margin-top:1.5rem;'>
                <div style='font-weight:700;color:{mood_colors[mood_cat]};margin-bottom:6px;'>{mood_icons[mood_cat]} Mood</div>
                <p style='color:var(--text-secondary);margin:0;font-size:0.92rem;'>{plan.get("checkin","")}</p>
            </div>
            <div class='content-card' style='border-left:4px solid #F59E0B;margin-top:1rem;'>
                <div style='font-weight:700;color:#F59E0B;margin-bottom:6px;'>✨ Motivation</div>
                <p style='color:var(--text-secondary);margin:0;font-size:0.92rem;font-style:italic;'>"{plan.get("boost","")}"</p>
            </div>""",
            unsafe_allow_html=True,
        )
        mode = plan.get("mode", "classic")
        mode_info = {
            "gentle":  ("🌙 Gentle Mode",  "20 min focus + 10 min recovery", "#EF4444"),
            "mellow":  ("🌙 Mellow Mode",  "25 min focus + 10 min recovery", "#F59E0B"),
            "classic": ("⚡ Classic Mode", "25 min focus + 5 min breaks",    "#10B981"),
        }
        m_label, m_desc, m_color = mode_info[mode]
        st.markdown(
            f"""<div class='content-card' style='border-left:4px solid {m_color};margin-top:1rem;'>
                <span style='font-weight:700;color:{m_color};'>{m_label}</span>
                <span style='color:var(--text-muted);font-size:0.88rem;margin-left:8px;'>{m_desc}</span>
            </div>""",
            unsafe_allow_html=True,
        )

        table_rows = ""
        for s in plan["schedule"]:
            bg    = "var(--accent-light)" if s["is_weak"] else "transparent"
            badge = " <span class='badge-weak'>WEAK</span>" if s["is_weak"] else ""
            table_rows += (
                f"<tr style='border-bottom:1px solid var(--border);background:{bg};'>"
                f"<td class='td'>#{s['session']}</td>"
                f"<td class='td' style='color:var(--accent);font-weight:600;white-space:nowrap;'>{s['start']}</td>"
                f"<td class='td' style='color:var(--accent);font-weight:600;white-space:nowrap;'>{s['end']}</td>"
                f"<td class='td' style='font-weight:600;'>{s['subject']}{badge}</td>"
                f"<td class='td' style='color:var(--text-muted);font-size:0.85rem;'>☕ {s['break_len']}m → {s['resume']}</td>"
                f"</tr>"
            )
        st.markdown("<p class='card-label' style='margin-top:1.5rem;'>📋 Your Schedule</p>", unsafe_allow_html=True)
        st.markdown(
            f"""<div style='overflow-x:auto;border-radius:var(--radius-md);border:1px solid var(--border);'>
            <table style='width:100%;border-collapse:collapse;'>
                <thead><tr style='background:var(--bg-secondary);border-bottom:2px solid var(--border);'>
                    <th class='th'>#</th><th class='th'>Start</th><th class='th'>End</th>
                    <th class='th'>Subject</th><th class='th'>Break</th>
                </tr></thead>
                <tbody>{table_rows}</tbody>
            </table></div>""",
            unsafe_allow_html=True,
        )
