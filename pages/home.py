import streamlit as st
from components.cards import render_stat_card, render_recent_item
from utils.helpers import get_time_greeting

def render_home_view():
    is_logged_in = st.session_state["logged_in"]

    if is_logged_in:
        # ── Authenticated dashboard ──
        greeting = get_time_greeting()
        uname    = st.session_state["username"]

        st.markdown(
            f"<div class='home-welcome'>"
            f"<h1 class='home-greeting'>Welcome back, {uname}.</h1>"
            f"<p class='home-subtext'>Here is your learning overview for today.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Stats row
        total_chats     = len(st.session_state.get("all_chats",     {}))
        total_summaries = len(st.session_state.get("all_summaries", {}))
        total_plans     = len(st.session_state.get("all_plans",     {}))
        total_mins      = sum(
            p.get("total_minutes", 0)
            for p in st.session_state.get("all_plans", {}).values()
        )
        c1, c2, c3, c4 = st.columns(4)
        stat_items = [
            (c1, "💬", total_chats,     "Chats",      "#6366F1"),
            (c2, "📝", total_summaries, "Summaries",  "#10B981"),
            (c3, "📅", total_plans,     "Plans",      "#F59E0B"),
            (c4, "⏱️", total_mins,      "Study Mins", "#EC4899"),
        ]
        for col, icon, num, label, color in stat_items:
            with col:
                render_stat_card(icon, num, label, color)

    else:
        # ── Unauthenticated hero ──
        from utils.helpers import get_base64_logo
        theme = st.session_state.get("theme", "light")
        logo_b64 = get_base64_logo(theme)
        img_html = f"<img src='data:image/png;base64,{logo_b64}' style='height: 2.4rem; margin-right: 0.6rem; vertical-align: middle;'>" if logo_b64 else ""

        st.markdown(
            f"""<div class='hero-section'>
                <div style='text-align: center; margin-bottom: 1.2rem; display: flex; align-items: center; justify-content: center;'>
                    {img_html}
                    <span style='font-size: 2.2rem; font-weight: 900; background: linear-gradient(135deg, #4F46E5, #7C3AED); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>StudyPilot</span>
                </div>
                <div class='hero-badge'>✦ Student Learning Assistant </div>
                <h1 class='hero-title'>Learn Faster.<br>Remember More.</h1>
                <p class='hero-sub'> Tutoring, intelligent summarization, and adaptive study planning in one seamless experience.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        _, cb1, cb2, _ = st.columns([2.5, 1.5, 1.5, 2.5])
        with cb1:
            if st.button("Start Learning Free", key="hero_cta", use_container_width=True, type="primary"):
                st.session_state["page"]      = "register"
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"]  = "input_email"
                st.rerun()
        with cb2:
            if st.button("Sign In", key="hero_signin", use_container_width=True):
                st.session_state["page"]      = "login"
                st.session_state["auth_view"] = "login"
                st.rerun()

    # ── Recent Activity (logged-in only) ──
    if is_logged_in:
        recent = []
        for cid, msgs in list(st.session_state["all_chats"].items())[:3]:
            label = msgs[0]["text"][:40] + "…" if msgs else "Untitled Chat"
            recent.append(("", label, cid, "chat", "active_chat_id"))
        for sid, data in list(st.session_state["all_summaries"].items())[:2]:
            label = data.get("title", "Untitled")[:40]
            recent.append(("", label, sid, "summary", "active_summary_id"))
        for pid, data in list(st.session_state["all_plans"].items())[:2]:
            label = data.get("title", "Untitled Plan")[:40]
            recent.append(("", label, pid, "planner", "active_planner_id"))

        if recent:
            st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-label'>🕐 Recent Activity</p>", unsafe_allow_html=True)
            for idx, (icon, label, item_id, view, key) in enumerate(recent[:5]):
                render_recent_item(icon, label, item_id, view, key, idx)
