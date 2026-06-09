import re
import datetime
import streamlit as st

def render_activity_view():
    st.markdown(
        "<h2 class='view-title'>📊 Activity Dashboard</h2>"
        "<p class='view-subtitle'>Everything you've studied, summarised, and planned — in one place</p>",
        unsafe_allow_html=True,
    )

    # ── Filter bar ──
    active_filter = st.session_state.get("activity_filter", "All")
    filter_opts   = ["All", "Chats", "Summaries", "Plans"]
    f1, f2, f3, f4, _ = st.columns([1, 1, 1, 1, 4])
    for col, label in zip([f1, f2, f3, f4], filter_opts):
        with col:
            btn_type = "primary" if label == active_filter else "secondary"
            if st.button(label, key=f"af_{label}", use_container_width=True, type=btn_type):
                st.session_state["activity_filter"] = label
                st.rerun()

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Build timeline items ──
    items = []

    if active_filter in ("All", "Chats"):
        for cid, msgs in st.session_state.get("all_chats", {}).items():
            date_str = "Recent"
            match = re.search(r'chat_(\d{8}_\d{6})', cid)
            if match:
                try:
                    date_str = datetime.datetime.strptime(match.group(1), "%Y%m%d_%H%M%S").strftime("%b %d, %Y %H:%M")
                except Exception:
                    pass
            label = msgs[0]["text"][:50] + "…" if msgs else "Untitled Chat"
            items.append({
                "type": "Chat", "icon": "💬", "color": "#6366F1",
                "label": label, "date": date_str, "id": cid,
                "view": "chat", "key": "active_chat_id",
            })

    if active_filter in ("All", "Summaries"):
        for sid, data in st.session_state.get("all_summaries", {}).items():
            date_str = "Recent"
            match = re.search(r'summary_(\d{8}_\d{6})', sid)
            if match:
                try:
                    date_str = datetime.datetime.strptime(match.group(1), "%Y%m%d_%H%M%S").strftime("%b %d, %Y %H:%M")
                except Exception:
                    pass
            label = data.get("title", "Untitled Summary")[:50]
            items.append({
                "type": "Summary", "icon": "📝", "color": "#10B981",
                "label": label, "date": date_str, "id": sid,
                "view": "summary", "key": "active_summary_id",
            })

    if active_filter in ("All", "Plans"):
        for pid, data in st.session_state.get("all_plans", {}).items():
            date_str = "Recent"
            match = re.search(r'planner_(\d{8}_\d{6})', pid)
            if match:
                try:
                    date_str = datetime.datetime.strptime(match.group(1), "%Y%m%d_%H%M%S").strftime("%b %d, %Y %H:%M")
                except Exception:
                    pass
            label = data.get("title", "Untitled Plan")[:50]
            items.append({
                "type": "Plan", "icon": "📅", "color": "#F59E0B",
                "label": label, "date": date_str, "id": pid,
                "view": "planner", "key": "active_planner_id",
            })

    if not items:
        st.markdown(
            """<div class='empty-state'>
                <div style='font-size:3rem;margin-bottom:1rem;'>📂</div>
                <h3 style='font-weight:700;color:var(--text-primary);'>No activity yet</h3>
                <p style='color:var(--text-muted);'>Start using Tutor, Summarizer, or Planner to build your history.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # ── Render timeline ──
    for idx, item in enumerate(items):
        col_line, col_content, col_btn = st.columns([0.5, 8.5, 1])
        i_color = item["color"]
        i_icon  = item["icon"]
        i_type  = item["type"]
        i_date  = item["date"]
        i_label = item["label"]
        i_id    = item["id"]
        i_view  = item["view"]
        i_key   = item["key"]

        with col_line:
            st.markdown(
                f"<div class='timeline-dot' style='background:{i_color};'></div>",
                unsafe_allow_html=True,
            )

        with col_content:
            st.markdown(
                f"""<div class='timeline-card'>
                    <div class='timeline-header'>
                        <span class='timeline-badge' style='background:{i_color}20;color:{i_color};'>
                            {i_icon} {i_type}
                        </span>
                        <span class='timeline-date'>{i_date}</span>
                    </div>
                    <div class='timeline-label'>{i_label}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with col_btn:
            if st.button("Open →", key=f"act_open_{i_id}_{idx}", use_container_width=True):
                st.session_state[i_key]          = i_id
                st.session_state["current_view"] = i_view
                st.rerun()

        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
