
# ---------------------- UI HELPERS ----------------------

def _do_logout():
    """Centralized logout — clears session and returns to landing."""
    save_data()
    for k, v in {
        "logged_in": False, "username": "", "auth_view": "welcome",
        "page": "landing", "current_view": "welcome_hub",
        "sidebar_open": False, "all_chats": {}, "all_summaries": {},
        "all_plans": {}, "active_chat_id": "", "active_summary_id": "",
        "active_planner_id": "", "nav_history_stack": [],
    }.items():
        st.session_state[k] = v
    st.rerun()


def _time_greeting():
    h = datetime.datetime.now().hour
    return "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")


# ---------------------- FEATURE HISTORY PANEL ----------------------
# Used inside Chat, Summary, Planner views to show item history

def render_sidebar_section(feature_key, friendly_name):
    if feature_key == "chat":
        history_dict = st.session_state["all_chats"]
        active_id    = st.session_state["active_chat_id"]
    elif feature_key == "summary":
        history_dict = st.session_state["all_summaries"]
        active_id    = st.session_state["active_summary_id"]
    else:
        history_dict = st.session_state["all_plans"]
        active_id    = st.session_state["active_planner_id"]

    st.markdown(
        f"<p style='font-weight:700;font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;"
        f"letter-spacing:0.08em;margin:0 0 8px 0;'>{friendly_name} History</p>",
        unsafe_allow_html=True,
    )

    if st.button(f"＋  New {friendly_name}", use_container_width=True, key=f"new_{feature_key}"):
        nid = f"{feature_key}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if feature_key == "chat":
            st.session_state["all_chats"][nid] = []
            st.session_state["active_chat_id"] = nid
            save_chat_immediately(nid, [], st.session_state["username"])
        elif feature_key == "summary":
            st.session_state["all_summaries"][nid] = {
                "text": "", "summary": "", "word_count": 80,
                "format_style": "Plain Text", "title": "Untitled Summary",
            }
            st.session_state["active_summary_id"] = nid
        else:
            st.session_state["all_plans"][nid] = {
                "subjects": "", "weak": "", "mood": "",
                "schedule": [], "title": "Untitled Plan",
            }
            st.session_state["active_planner_id"] = nid
        save_data()
        st.rerun()

    if not history_dict:
        st.markdown(
            "<div style='text-align:center;padding:2rem 1rem;color:var(--text-muted);font-size:0.85rem;'>"
            f"<div style='font-size:1.5rem;margin-bottom:0.5rem;opacity:0.5;'>📂</div>"
            f"No {friendly_name.lower()}s yet</div>",
            unsafe_allow_html=True,
        )
        return

    open_menu = st.session_state.get("active_menu_item_id", "")

    for item_id in list(history_dict.keys()):
        if feature_key == "chat":
            msgs  = history_dict[item_id]
            label = msgs[0]["text"][:22] + "…" if msgs else "Untitled Chat"
        else:
            label = history_dict[item_id].get("title", "Untitled")[:22]

        is_active = item_id == active_id
        is_open   = open_menu == item_id

        col_sel, col_dot = st.columns([8, 2])

        with col_sel:
            prefix = "● " if is_active else ""
            if st.button(f"{prefix}{label}", key=f"sel_{item_id}_{feature_key}", use_container_width=True):
                if feature_key == "chat":
                    st.session_state["active_chat_id"] = item_id
                elif feature_key == "summary":
                    st.session_state["active_summary_id"] = item_id
                else:
                    st.session_state["active_planner_id"] = item_id
                st.rerun()

        with col_dot:
            if st.button("⋮", key=f"dots_{item_id}_{feature_key}", use_container_width=True):
                st.session_state["active_menu_item_id"] = item_id if not is_open else ""
                st.rerun()

        if is_open:
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("Rename", key=f"ren_{item_id}_{feature_key}", use_container_width=True):
                    st.session_state["editing_item_id"]       = item_id
                    st.session_state["rename_feature_target"] = feature_key
                    st.session_state["active_menu_item_id"]   = ""
                    st.rerun()
            with dc2:
                if st.button("Delete", key=f"del_{item_id}_{feature_key}", use_container_width=True):
                    del history_dict[item_id]
                    delete_item_from_db(feature_key, item_id)
                    st.session_state["active_menu_item_id"] = ""
                    if active_id == item_id:
                        remaining = list(history_dict.keys())
                        fallback  = remaining[0] if remaining else ""
                        if feature_key == "chat":      st.session_state["active_chat_id"]    = fallback
                        elif feature_key == "summary": st.session_state["active_summary_id"] = fallback
                        else:                          st.session_state["active_planner_id"]  = fallback
                    st.rerun()

    eid = st.session_state.get("editing_item_id", "")
    if eid in history_dict and st.session_state.get("rename_feature_target") == feature_key:
        with st.form(f"rename_form_{feature_key}"):
            new_title = st.text_input("New name", placeholder="Enter title…", label_visibility="collapsed")
            if st.form_submit_button("Save", use_container_width=True):
                if new_title.strip():
                    if feature_key == "chat":
                        msgs = st.session_state["all_chats"][eid]
                        if not msgs:
                            msgs.append({"role": "assistant", "text": new_title.strip()})
                        else:
                            msgs[0]["text"] = new_title.strip()
                    else:
                        history_dict[eid]["title"] = new_title.strip()
                    save_data()
                    st.session_state["editing_item_id"] = ""
                    st.rerun()


# ---------------------- MAIN CONTENT VIEWS ----------------------

def render_chat_view():
    """ChatGPT-style AI Tutor interface."""
    col_list, col_content = st.columns([2.5, 7.5])

    with col_list:
        st.markdown("<div class='history-panel'>", unsafe_allow_html=True)
        render_sidebar_section("chat", "Chat")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_content:
        st.markdown(
            "<h2 class='view-title'>💬 AI Tutor</h2>"
            "<p class='view-subtitle'>Get instant help with programming, ML, DSA, and more</p>",
            unsafe_allow_html=True,
        )

        if not st.session_state["all_chats"]:
            default_id = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state["all_chats"][default_id] = []
            st.session_state["active_chat_id"] = default_id
            save_chat_immediately(default_id, [], st.session_state["username"])
        elif not st.session_state["active_chat_id"]:
            st.session_state["active_chat_id"] = list(st.session_state["all_chats"].keys())[0]

        active_chat_id = st.session_state["active_chat_id"]
        active_chat = st.session_state["all_chats"].get(active_chat_id, [])

        # Handle suggestion chip click → auto-send
        prefill = st.session_state.pop("_chat_prefill", None)
        if prefill:
            with st.spinner("Thinking…"):
                ans, sentiment = get_chat_response(prefill, active_chat)
            if sentiment["compound"] >= 0.05:
                st.toast("Positive vibes! 😊")
            elif sentiment["compound"] <= -0.05:
                st.toast("You seem stressed. Take it easy! 💙")
            active_chat.append({"role": "user", "text": prefill})
            active_chat.append({"role": "assistant", "text": ans})
            st.session_state["all_chats"][active_chat_id] = active_chat
            save_chat_immediately(active_chat_id, active_chat, st.session_state["username"])
            st.rerun()

        # ── Empty state with suggestion chips ──
        if not active_chat:
            st.markdown(
                """<div class='chat-empty'>
                    <div style='font-size:3.5rem;margin-bottom:1rem;opacity:0.8;'>✈️</div>
                    <h3 style='font-weight:800;color:var(--text-primary);margin:0 0 0.5rem 0;font-size:1.5rem;'>
                        What would you like to learn?
                    </h3>
                    <p style='color:var(--text-muted);font-size:0.95rem;margin:0;'>
                        Pick a suggestion or type your own question below
                    </p>
                </div>""",
                unsafe_allow_html=True,
            )
            suggestions = [
                ("💡", "Explain binary search step by step"),
                ("🧠", "What is overfitting in machine learning?"),
                ("📝", "Summarize key Python data structures"),
                ("❓", "Generate practice questions on DSA"),
            ]
            c1, c2 = st.columns(2)
            for i, (icon, text) in enumerate(suggestions):
                with (c1 if i % 2 == 0 else c2):
                    if st.button(f"{icon}  {text}", key=f"suggest_{i}", use_container_width=True):
                        st.session_state["_chat_prefill"] = text
                        st.rerun()
        else:
            # ── Render messages ──
            for idx, msg in enumerate(active_chat):
                msg_id = f"msg_{active_chat_id}_{idx}"
                if msg["role"] == "user":
                    st.markdown(
                        f"<div class='chat-row user-row'><div class='chat-msg user-bubble'>{msg['text']}</div></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='chat-row bot-row'>"
                        f"<div class='bot-avatar'>🤖</div>"
                        f"<div class='chat-msg bot-bubble'>{msg['text']}</div></div>",
                        unsafe_allow_html=True,
                    )
                # Copy button for bot messages
                if msg["role"] == "assistant":
                    _, _, cc = st.columns([6, 3, 1])
                    with cc:
                        if st.button("📋", key=f"cp_{msg_id}", help="Copy response"):
                            try:
                                pyperclip.copy(msg["text"])
                            except Exception:
                                pass
                            st.toast("Copied! ✅")

        # ── Input form ──
        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            chat_input = st.text_input(
                "", placeholder="Ask anything about Python, ML, DSA…", label_visibility="collapsed"
            )
            send = st.form_submit_button("Send →", use_container_width=True)

        if send and chat_input.strip():
            with st.spinner("Thinking…"):
                ans, sentiment = get_chat_response(chat_input, active_chat)
            if sentiment["compound"] >= 0.05:
                st.toast("Positive vibes! 😊")
            elif sentiment["compound"] <= -0.05:
                st.toast("You seem stressed. Take it easy! 💙")
            active_chat.append({"role": "user",      "text": chat_input})
            active_chat.append({"role": "assistant", "text": ans})
            st.session_state["all_chats"][active_chat_id] = active_chat
            save_chat_immediately(active_chat_id, active_chat, st.session_state["username"])
            st.rerun()


def render_summary_view():
    """Card-based summarizer with input and output panels."""
    col_list, col_content = st.columns([2.5, 7.5])

    with col_list:
        st.markdown("<div class='history-panel'>", unsafe_allow_html=True)
        render_sidebar_section("summary", "Summary")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_content:
        st.markdown(
            "<h2 class='view-title'>📝 Smart Summarizer</h2>"
            "<p class='view-subtitle'>Transform lengthy notes into concise, structured study material</p>",
            unsafe_allow_html=True,
        )

        if not st.session_state["all_summaries"]:
            st.session_state["all_summaries"]["summary_default"] = {
                "text": "", "summary": "", "word_count": 80,
                "format_style": "Plain Text", "title": "Untitled Summary",
            }
            st.session_state["active_summary_id"] = "summary_default"
            save_data()
        elif not st.session_state["active_summary_id"]:
            st.session_state["active_summary_id"] = list(st.session_state["all_summaries"].keys())[0]

        node = st.session_state["all_summaries"].get(st.session_state["active_summary_id"])

        # ── Input card ──
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<p class='card-label'>📄 Input Text</p>", unsafe_allow_html=True)
        raw_text = st.text_area(
            "", value=node["text"], height=200,
            placeholder="Paste your lecture notes, articles, or study material here…",
            label_visibility="collapsed",
        )
        if raw_text.strip():
            st.caption(f"📄 {len(raw_text.split())} words")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Controls ──
        cc, cf = st.columns(2)
        with cc:
            target_words = st.number_input(
                "Target word count", min_value=10, max_value=1000,
                value=int(node.get("word_count", 80)), step=10,
            )
        with cf:
            fmt_options = ["Plain Text", "Bullet Points", "Essay", "Letter", "Email"]
            fmt = st.selectbox(
                "Output format", fmt_options,
                index=fmt_options.index(node.get("format_style", "Plain Text")),
            )

        node["text"]         = raw_text
        node["word_count"]   = target_words
        node["format_style"] = fmt

        if st.button("✨  Generate Summary", use_container_width=True, key="gen_sum_btn", type="primary"):
            if len(raw_text.strip()) < 20:
                st.warning("Please paste more text first.")
            else:
                with st.spinner(f"Generating ~{target_words} word {fmt} summary…"):
                    formatted, engine = get_summary(
                        raw_text, target_words, fmt, st.session_state["username"]
                    )
                    node["summary"]     = formatted
                    node["raw_summary"] = formatted
                    node["engine"]      = engine
                    if node["title"].startswith("Untitled"):
                        node["title"] = raw_text[:18] + "..."
                    st.session_state["all_summaries"][st.session_state["active_summary_id"]] = node
                    save_data()
                    st.rerun()

        # ── Output card ──
        if node["summary"]:
            st.markdown("<div class='content-card' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
            st.markdown("<p class='card-label'>📝 Generated Summary</p>", unsafe_allow_html=True)
            st.markdown(node["summary"])

            c_copy, c_code = st.columns([1, 1])
            with c_copy:
                if st.button("📋 Copy Summary", key="cp_sum", use_container_width=True):
                    st.session_state["show_copy_summary"] = True
            with c_code:
                if st.button("📤 Share", key="sh_sum", use_container_width=True):
                    st.toast("Link copied!")

            if st.session_state.get("show_copy_summary", False):
                st.code(node.get("raw_summary", node["summary"]), language="text")
                if st.button("✕ Close", key="close_copy_sum"):
                    st.session_state["show_copy_summary"] = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def render_planner_view():
    """Mood-adaptive study planner with schedule generation."""
    col_list, col_content = st.columns([2.5, 7.5])

    with col_list:
        st.markdown("<div class='history-panel'>", unsafe_allow_html=True)
        render_sidebar_section("planner", "Planner")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_content:
        st.markdown(
            "<h2 class='view-title'>📅 Adaptive Study Planner</h2>"
            "<p class='view-subtitle'>Your schedule adapts based on how you feel — because wellbeing matters</p>",
            unsafe_allow_html=True,
        )

        if not st.session_state["all_plans"]:
            st.session_state["all_plans"]["planner_default"] = {
                "subjects": "", "weak": "", "mood": "", "schedule": [], "title": "Untitled Plan",
            }
            st.session_state["active_planner_id"] = "planner_default"
            save_data()
        elif not st.session_state["active_planner_id"]:
            st.session_state["active_planner_id"] = list(st.session_state["all_plans"].keys())[0]

        plan = st.session_state["all_plans"].get(st.session_state["active_planner_id"])

        # ── Input form ──
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        with st.form("planner_form"):
            c1, c2 = st.columns(2)
            with c1:
                subj       = st.text_input("Subjects", value=plan["subjects"],
                                           placeholder="e.g. Python, ML, DSA")
                start_time = st.time_input("Start Time", datetime.time(9, 0))
            with c2:
                weak     = st.text_input("Weak Subject", value=plan["weak"],
                                         placeholder="e.g. Python")
                end_time = st.time_input("End Time", datetime.time(12, 0))
            mood = st.text_input("How are you feeling right now?", value=plan["mood"],
                                 placeholder="e.g. tired, stressed, excited…")
            gen  = st.form_submit_button("Generate My Schedule", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Schedule generation logic (PRESERVED) ──
        if gen:
            slist = [s.strip() for s in subj.split(",") if s.strip()]
            if not slist:
                st.error("Please enter at least one subject.")
            elif end_time <= start_time:
                st.error("End time must be after start time.")
            else:
                sia        = get_sia()
                mood_score = sia.polarity_scores(mood)["compound"]
                boost, mood_cat, checkin = get_motivational_message(mood_score)
                plan.update({"subjects": subj, "weak": weak, "mood": mood})
                if plan["title"].startswith("Untitled") and slist:
                    plan["title"] = f"Plan: {slist[0]}"

                start_dt      = datetime.datetime.combine(datetime.date.today(), start_time)
                end_dt        = datetime.datetime.combine(datetime.date.today(), end_time)
                total_minutes = int((end_dt - start_dt).total_seconds() / 60)

                if mood_score <= -0.3:
                    work_mins, break_mins, mode = 20, 10, "gentle"
                elif mood_score <= -0.1:
                    work_mins, break_mins, mode = 25, 10, "mellow"
                else:
                    work_mins, break_mins, mode = 25, 5, "classic"

                weighted = []
                for s in slist:
                    weighted.append(s)
                    if s.lower() == weak.strip().lower():
                        weighted.append(s)

                schedule, t, i, session_num = [], start_dt, 0, 1
                while t < end_dt:
                    remaining = int((end_dt - t).total_seconds() / 60)
                    if remaining < work_mins:
                        break
                    sub          = weighted[i % len(weighted)]
                    actual_work  = min(work_mins, remaining)
                    end_session  = t + datetime.timedelta(minutes=actual_work)
                    actual_break = min(break_mins, int((end_dt - end_session).total_seconds() / 60))
                    resume_at    = end_session + datetime.timedelta(minutes=actual_break)
                    schedule.append({
                        "session":  session_num,
                        "start":    t.strftime("%I:%M %p"),
                        "end":      end_session.strftime("%I:%M %p"),
                        "subject":  sub,
                        "is_weak":  sub.lower() == weak.strip().lower(),
                        "break_len": actual_break,
                        "resume":   resume_at.strftime("%I:%M %p"),
                        "mode":     mode,
                    })
                    t = resume_at
                    i += 1
                    session_num += 1

                plan.update({
                    "schedule": schedule, "boost": boost, "checkin": checkin,
                    "mood_cat": mood_cat, "mode": mode, "total_minutes": total_minutes,
                })
                st.session_state["all_plans"][st.session_state["active_planner_id"]] = plan
                save_data()
                st.rerun()

        # ── Display generated schedule ──
        if plan.get("schedule"):
            mood_cat = plan.get("mood_cat", "neutral")
            checkin  = plan.get("checkin", "")
            mood_colors = {"positive": "#10B981", "neutral": "#6366F1", "negative": "#EF4444"}
            mood_bg     = {"positive": "rgba(16,185,129,0.08)", "neutral": "rgba(99,102,241,0.08)", "negative": "rgba(239,68,68,0.08)"}
            mood_icons  = {"positive": "🌟", "neutral": "🎯", "negative": "💙"}

            st.markdown(
                f"""<div class='content-card' style='border-left:4px solid {mood_colors[mood_cat]};background:{mood_bg[mood_cat]};'>
                    <div style='font-weight:700;color:{mood_colors[mood_cat]};margin-bottom:6px;'>
                        {mood_icons[mood_cat]} Mood Check-in
                    </div>
                    <p style='color:var(--text-secondary);margin:0;font-size:0.92rem;'>{checkin}</p>
                </div>""",
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""<div class='content-card' style='border-left:4px solid #F59E0B;margin-top:1rem;'>
                    <div style='font-weight:700;color:#F59E0B;margin-bottom:6px;'>✨ Motivation</div>
                    <p style='color:var(--text-secondary);margin:0;font-size:0.92rem;font-style:italic;'>
                        "{plan['boost']}"
                    </p>
                </div>""",
                unsafe_allow_html=True,
            )

            mode = plan.get("mode", "classic")
            mode_info = {
                "gentle": ("🌙 Gentle Mode", "20 min focus + 10 min recovery", "#EF4444"),
                "mellow": ("🌙 Mellow Mode", "25 min focus + 10 min recovery", "#F59E0B"),
                "classic": ("⚡ Classic Mode", "25 min focus + 5 min breaks", "#10B981"),
            }
            m_label, m_desc, m_color = mode_info[mode]
            st.markdown(
                f"""<div class='content-card' style='border-left:4px solid {m_color};margin-top:1rem;'>
                    <span style='font-weight:700;color:{m_color};'>{m_label}</span>
                    <span style='color:var(--text-muted);font-size:0.88rem;margin-left:8px;'>{m_desc}</span>
                </div>""",
                unsafe_allow_html=True,
            )

            # Stats row
            total    = plan.get("total_minutes", 0)
            sessions = len(plan["schedule"])
            st.markdown(
                f"""<div style='display:flex;gap:12px;margin:1.5rem 0;'>
                    <div class='stat-mini'><div class='stat-num' style='color:var(--accent);'>{sessions}</div><div class='stat-label'>Sessions</div></div>
                    <div class='stat-mini'><div class='stat-num' style='color:#10B981;'>{total}</div><div class='stat-label'>Total Mins</div></div>
                    <div class='stat-mini'><div class='stat-num' style='color:#F59E0B;'>{plan["schedule"][0]["break_len"]}</div><div class='stat-label'>Break Mins</div></div>
                </div>""",
                unsafe_allow_html=True,
            )

            # Schedule table
            st.markdown("<p class='card-label'>📋 Your Schedule</p>", unsafe_allow_html=True)
            table_rows = ""
            for s in plan["schedule"]:
                bg = "var(--accent-light)" if s["is_weak"] else "transparent"
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

            if mood_cat == "negative":
                st.markdown(
                    """<div class='content-card' style='border-left:4px solid #EF4444;background:rgba(239,68,68,0.06);margin-top:1.5rem;'>
                        <span style='color:#EF4444;font-weight:700;'>💙 A Note For You</span>
                        <p style='color:var(--text-secondary);margin:6px 0 0;font-size:0.9rem;'>
                        It's okay to not be okay. If you feel overwhelmed, step away.
                        Your mental health always comes first. Even one session today is a win. 🤍
                        </p>
                    </div>""",
                    unsafe_allow_html=True,
                )


def render_history_view():
    """Unified learning history with type-specific styling."""
    st.markdown(
        "<h2 class='view-title'>📚 Learning History</h2>"
        "<p class='view-subtitle'>All your past chats, summaries, and schedules in one place</p>",
        unsafe_allow_html=True,
    )

    history_items = []
    type_meta = {
        "Chat":    {"icon": "💬", "color": "#6366F1"},
        "Summary": {"icon": "📝", "color": "#10B981"},
        "Planner": {"icon": "📅", "color": "#F59E0B"},
    }

    for cid, msgs in st.session_state["all_chats"].items():
        date_str = "Recent"
        match = re.search(r'chat_(\d{8})', cid)
        if match:
            date_str = datetime.datetime.strptime(match.group(1), "%Y%m%d").strftime("%B %d, %Y")
        label = msgs[0]["text"][:40] + "…" if msgs else "Untitled Chat"
        history_items.append({
            "type": "Chat", "label": label, "date": date_str,
            "id": cid, "view": "chat", "active_key": "active_chat_id"
        })

    for sid, data in st.session_state["all_summaries"].items():
        date_str = "Recent"
        match = re.search(r'summary_(\d{8})', sid)
        if match:
            date_str = datetime.datetime.strptime(match.group(1), "%Y%m%d").strftime("%B %d, %Y")
        label = data.get("title", "Untitled Summary")[:40]
        history_items.append({
            "type": "Summary", "label": label, "date": date_str,
            "id": sid, "view": "summary", "active_key": "active_summary_id"
        })

    for pid, data in st.session_state["all_plans"].items():
        date_str = "Recent"
        match = re.search(r'planner_(\d{8})', pid)
        if match:
            date_str = datetime.datetime.strptime(match.group(1), "%Y%m%d").strftime("%B %d, %Y")
        label = data.get("title", "Untitled Plan")[:40]
        history_items.append({
            "type": "Planner", "label": label, "date": date_str,
            "id": pid, "view": "planner", "active_key": "active_planner_id"
        })

    if not history_items:
        st.markdown(
            """<div class='empty-state'>
                <div style='font-size:3rem;margin-bottom:1rem;'>📂</div>
                <h3 style='font-weight:700;color:var(--text-primary);margin:0 0 0.5rem 0;'>No history yet</h3>
                <p style='color:var(--text-muted);margin:0;'>Start using AI Tutor, Summarizer, or Planner to build your learning history.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # Group by date
    grouped = {}
    for item in history_items:
        grouped.setdefault(item["date"], []).append(item)

    for date_val, items in sorted(grouped.items(), reverse=True):
        st.markdown(
            f"<p style='font-weight:700;color:var(--accent);font-size:0.8rem;text-transform:uppercase;"
            f"letter-spacing:0.05em;border-bottom:1px solid var(--border);padding-bottom:6px;"
            f"margin-top:1.5rem;'>{date_val}</p>",
            unsafe_allow_html=True,
        )
        for idx, item in enumerate(items):
            meta = type_meta[item["type"]]
            col_lbl, col_btn = st.columns([8.5, 1.5])
            with col_lbl:
                st.markdown(
                    f"""<div class='content-card' style='padding:0.8rem 1rem;margin-bottom:6px;display:flex;align-items:center;gap:10px;'>
                        <span style='font-size:1.2rem;'>{meta['icon']}</span>
                        <span class='badge' style='background:{meta['color']}20;color:{meta['color']};'>{item['type']}</span>
                        <span style='color:var(--text-primary);font-size:0.9rem;'>{item['label']}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col_btn:
                if st.button("Open →", key=f"hist_go_{item['id']}_{idx}", use_container_width=True):
                    st.session_state[item["active_key"]] = item["id"]
                    st.session_state["current_view"] = item["view"]
                    st.rerun()


def render_profile_view():
    """User profile with avatar and stats."""
    st.markdown(
        "<h2 class='view-title'>👤 Profile</h2>"
        "<p class='view-subtitle'>Your account details and productivity stats</p>",
        unsafe_allow_html=True,
    )

    uid   = st.session_state["username"]
    email = st.session_state["user_db"].get(uid, {}).get("identity", "N/A")
    initial = uid[0].upper() if uid else "?"
    total_chats    = len(st.session_state.get("all_chats", {}))
    total_summaries = len(st.session_state.get("all_summaries", {}))
    total_plans    = len(st.session_state.get("all_plans", {}))

    st.markdown(
        f"""<div class='content-card' style='max-width:600px;'>
            <div style='display:flex;align-items:center;gap:20px;margin-bottom:2rem;'>
                <div class='avatar-circle'>{initial}</div>
                <div>
                    <h3 style='margin:0;font-weight:800;color:var(--text-primary);'>{uid}</h3>
                    <span style='color:var(--text-muted);font-size:0.9rem;'>{email}</span>
                </div>
            </div>
            <p class='card-label'>Productivity Insights</p>
            <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;'>
                <div class='stat-mini'><div class='stat-num'>{total_chats}</div><div class='stat-label'>Tutor Chats</div></div>
                <div class='stat-mini'><div class='stat-num'>{total_summaries}</div><div class='stat-label'>Summaries</div></div>
                <div class='stat-mini'><div class='stat-num'>{total_plans}</div><div class='stat-label'>Plans</div></div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_settings_view():
    """Account settings with password change and data management."""
    st.markdown(
        "<h2 class='view-title'>⚙️ Settings</h2>"
        "<p class='view-subtitle'>Manage your account and preferences</p>",
        unsafe_allow_html=True,
    )

    uid = st.session_state["username"]

    # ── Password Section ──
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<p class='card-label'>🔒 Change Password</p>", unsafe_allow_html=True)
    with st.form("settings_form"):
        old_pwd  = st.text_input("Current Password", type="password")
        new_pwd  = st.text_input("New Password", type="password")
        conf_pwd = st.text_input("Confirm New Password", type="password")
        save_btn = st.form_submit_button("Update Password", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if save_btn:
        if not old_pwd or not new_pwd or not conf_pwd:
            st.error("Please fill in all password fields.")
        elif new_pwd != conf_pwd:
            st.error("New passwords do not match.")
        elif len(new_pwd) < 4:
            st.error("New password must be at least 4 characters long.")
        else:
            with get_conn() as conn:
                row = conn.execute("SELECT password FROM users WHERE username=?", (uid,)).fetchone()
            if row and row["password"] == hash_password(old_pwd):
                new_hash = hash_password(new_pwd)
                with get_conn() as conn:
                    conn.execute("UPDATE users SET password=? WHERE username=?", (new_hash, uid))
                st.session_state["user_db"][uid]["password"] = new_hash
                st.success("Password updated successfully!")
            else:
                st.error("Incorrect current password.")

    # ── Danger Zone ──
    st.markdown(
        "<div class='content-card' style='border:1px solid rgba(239,68,68,0.3);margin-top:1.5rem;'>",
        unsafe_allow_html=True,
    )
    st.markdown("<p class='card-label' style='color:#EF4444;'>⚠️ Danger Zone</p>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:var(--text-muted);font-size:0.88rem;margin:0 0 1rem 0;'>"
        "Permanently delete all your AI Tutor chats, summaries, and study plans. This cannot be undone.</p>",
        unsafe_allow_html=True,
    )
    if st.button("🗑️ Clear All History Data", key="clear_all_data", use_container_width=True):
        username = st.session_state["username"]
        with get_conn() as conn:
            conn.execute("DELETE FROM chats WHERE username=?", (username,))
            conn.execute("DELETE FROM summaries WHERE username=?", (username,))
            conn.execute("DELETE FROM plans WHERE username=?", (username,))
        st.session_state["all_chats"]         = {}
        st.session_state["all_summaries"]     = {}
        st.session_state["all_plans"]         = {}
        st.session_state["active_chat_id"]    = ""
        st.session_state["active_summary_id"] = ""
        st.session_state["active_planner_id"] = ""
        st.toast("History cleared! 🧹")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_analytics_view():
    """Study analytics with progress visualization."""
    st.markdown(
        "<h2 class='view-title'>📊 Study Analytics</h2>"
        "<p class='view-subtitle'>Track your learning patterns, productivity, and wellbeing</p>",
        unsafe_allow_html=True,
    )

    total_chats     = len(st.session_state.get("all_chats", {}))
    total_summaries = len(st.session_state.get("all_summaries", {}))
    total_plans     = len(st.session_state.get("all_plans", {}))

    total_minutes = 0
    modes = {"classic": 0, "mellow": 0, "gentle": 0}
    moods = {"positive": 0, "neutral": 0, "negative": 0}
    for plan in st.session_state.get("all_plans", {}).values():
        total_minutes += plan.get("total_minutes", 0)
        mode = plan.get("mode", "classic")
        modes[mode] = modes.get(mode, 0) + 1
        mood_cat = plan.get("mood_cat", "neutral")
        moods[mood_cat] = moods.get(mood_cat, 0) + 1

    # Stats row
    c1, c2, c3, c4 = st.columns(4)
    stats = [
        (c1, "⏱️", total_minutes, "Study Minutes", "var(--accent)"),
        (c2, "📅", total_plans,    "Schedules",     "#10B981"),
        (c3, "💬", total_chats,    "Tutor Queries", "#6366F1"),
        (c4, "📝", total_summaries,"Summaries",     "#F59E0B"),
    ]
    for col, icon, num, label, color in stats:
        with col:
            st.markdown(
                f"""<div class='content-card' style='text-align:center;padding:1.2rem;'>
                    <div style='font-size:1.3rem;margin-bottom:4px;'>{icon}</div>
                    <div style='font-size:1.8rem;font-weight:800;color:{color};'>{num}</div>
                    <div style='color:var(--text-muted);font-size:0.78rem;margin-top:2px;'>{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("<div class='content-card' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
        st.markdown("<p class='card-label'>🎯 Pomodoro Mode Breakdown</p>", unsafe_allow_html=True)
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
                            <span style='color:{color};font-weight:700;font-size:0.85rem;'>{count}</span>
                        </div>
                        <div style='background:var(--bg-secondary);border-radius:8px;height:6px;overflow:hidden;'>
                            <div style='width:{pct}%;height:100%;background:{color};border-radius:8px;transition:width 0.5s;'></div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='content-card' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
        st.markdown("<p class='card-label'>🧠 Mental Wellbeing Insights</p>", unsafe_allow_html=True)
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
                            <span style='color:{color};font-weight:700;font-size:0.85rem;'>{count}</span>
                        </div>
                        <div style='background:var(--bg-secondary);border-radius:8px;height:6px;overflow:hidden;'>
                            <div style='width:{pct}%;height:100%;background:{color};border-radius:8px;transition:width 0.5s;'></div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)


def render_login_required_view():
    """Shown when unauthenticated users try to access protected features."""
    st.markdown("<div style='padding-top:60px;'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        view_name = st.session_state["current_view"].replace("_", " ").title()
        st.markdown(
            f"""<div class='content-card' style='text-align:center;padding:3rem;'>
                <div style='font-size:3rem;margin-bottom:1rem;'>🔒</div>
                <h3 style='font-weight:800;color:var(--text-primary);margin:0 0 0.5rem 0;'>Sign in to continue</h3>
                <p style='color:var(--text-muted);font-size:0.95rem;margin:0 0 2rem 0;'>
                    Access <strong>{view_name}</strong> and save your progress
                </p>
            </div>""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sign In", key="req_login_btn", use_container_width=True, type="primary"):
                st.session_state["page"] = "login"
                st.session_state["auth_view"] = "login"
                st.rerun()
        with c2:
            if st.button("Create Account", key="req_register_btn", use_container_width=True):
                st.session_state["page"] = "register"
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"] = "input_email"
                st.rerun()


def render_dashboard_view():
    """Main dashboard — command center when logged in, hero page when logged out."""

    if st.session_state["logged_in"]:
        # ── Logged-in dashboard ──
        greeting = _time_greeting()
        uname    = st.session_state["username"]
        st.markdown(
            f"<h2 style='font-weight:800;color:var(--text-primary);margin:0;'>{greeting}, {uname} 👋</h2>"
            f"<p style='color:var(--text-muted);margin:4px 0 2rem 0;font-size:1rem;'>Ready to study?</p>",
            unsafe_allow_html=True,
        )

        # Stats row
        total_chats     = len(st.session_state.get("all_chats", {}))
        total_summaries = len(st.session_state.get("all_summaries", {}))
        total_plans     = len(st.session_state.get("all_plans", {}))
        total_mins      = sum(p.get("total_minutes", 0) for p in st.session_state.get("all_plans", {}).values())

        c1, c2, c3, c4 = st.columns(4)
        for col, num, label, icon in [
            (c1, total_chats,     "Chats",     "💬"),
            (c2, total_summaries, "Summaries", "📝"),
            (c3, total_plans,     "Plans",     "📅"),
            (c4, total_mins,      "Study Mins","⏱️"),
        ]:
            with col:
                st.markdown(
                    f"""<div class='content-card' style='text-align:center;padding:1rem;'>
                        <div style='font-size:1.1rem;'>{icon}</div>
                        <div style='font-size:1.6rem;font-weight:800;color:var(--accent);'>{num}</div>
                        <div style='font-size:0.75rem;color:var(--text-muted);'>{label}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    else:
        # ── Logged-out hero ──
        st.markdown(
            """<div style='text-align:center;max-width:700px;margin:2rem auto 3rem auto;'>
                <h1 style='font-size:3.2rem;font-weight:900;background:linear-gradient(135deg,#4F46E5,#7C3AED);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.15;
                    margin-bottom:1rem;letter-spacing:-1.5px;'>
                    Learn Faster.<br>Remember More.
                </h1>
                <p style='font-size:1.15rem;color:var(--text-muted);max-width:550px;margin:0 auto;line-height:1.6;'>
                    AI tutoring, intelligent summarization, and adaptive study planning in one seamless experience.
                </p>
            </div>""",
            unsafe_allow_html=True,
        )
        _, cb1, cb2, _ = st.columns([2, 1.5, 1, 2])
        with cb1:
            if st.button("Start Learning Free", key="land_cta", use_container_width=True, type="primary"):
                st.session_state["page"] = "register"
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"] = "input_email"
                st.rerun()
        with cb2:
            if st.button("Sign In", key="land_login_hero", use_container_width=True):
                st.session_state["page"] = "login"
                st.session_state["auth_view"] = "login"
                st.rerun()

    # ── Quick Action Cards (shown for all users) ──
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    cards = [
        ("💬", "AI Tutor",          "Get instant help with programming, DSA, and ML concepts.", "chat",      "#6366F1"),
        ("📝", "Smart Summarizer",  "Transform notes into concise, structured study material.", "summary",   "#10B981"),
        ("📅", "Adaptive Planner",  "Generate mood-based study schedules with Pomodoro.",       "planner",   "#F59E0B"),
        ("📊", "Study Analytics",   "Track learning patterns, productivity, and wellbeing.",    "analytics", "#EC4899"),
    ]

    c1, c2 = st.columns(2)
    for i, (icon, title, desc, view, color) in enumerate(cards):
        with (c1 if i % 2 == 0 else c2):
            st.markdown(
                f"""<div class='action-card' style='border-top:3px solid {color};'>
                    <div style='font-size:2rem;margin-bottom:0.6rem;'>{icon}</div>
                    <h3 style='font-weight:700;color:var(--text-primary);margin:0 0 0.4rem 0;font-size:1.1rem;'>{title}</h3>
                    <p style='color:var(--text-muted);font-size:0.88rem;margin:0;line-height:1.45;'>{desc}</p>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button(f"Launch {title} →", key=f"card_btn_{view}", use_container_width=True):
                st.session_state["current_view"] = view
                st.rerun()

    # ── Recent Activity (logged in only) ──
    if st.session_state["logged_in"]:
        recent = []
        for cid, msgs in list(st.session_state["all_chats"].items())[:3]:
            label = msgs[0]["text"][:35] + "…" if msgs else "Untitled Chat"
            recent.append(("💬", label, cid, "chat", "active_chat_id"))
        for sid, data in list(st.session_state["all_summaries"].items())[:2]:
            label = data.get("title", "Untitled")[:35]
            recent.append(("📝", label, sid, "summary", "active_summary_id"))

        if recent:
            st.markdown(
                "<p class='card-label' style='margin-top:2.5rem;'>🕐 Recent Activity</p>",
                unsafe_allow_html=True,
            )
            for icon, label, item_id, view, key in recent:
                cl, cr = st.columns([9, 1])
                with cl:
                    st.markdown(
                        f"<div style='padding:8px 12px;background:var(--bg-secondary);border-radius:var(--radius-sm);"
                        f"margin-bottom:6px;font-size:0.88rem;color:var(--text-secondary);display:flex;align-items:center;gap:8px;'>"
                        f"<span>{icon}</span>{label}</div>",
                        unsafe_allow_html=True,
                    )
                with cr:
                    if st.button("→", key=f"recent_{item_id}", use_container_width=True):
                        st.session_state[key] = item_id
                        st.session_state["current_view"] = view
                        st.rerun()


# ---------------------- AUTH ----------------------

def render_login_page():
    """Authentication flow — login, register, forgot password."""
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            """<div class='auth-card'>
                <div style='text-align:center;margin-bottom:2rem;'>
                    <div style='font-size:2.5rem;margin-bottom:0.5rem;'>✈️</div>
                    <h1 style='font-weight:900;font-size:2rem;margin:0;letter-spacing:-1px;
                        background:linear-gradient(135deg,#4F46E5,#7C3AED);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
                        StudyPilot
                    </h1>
                    <p style='color:var(--text-muted);font-size:0.9rem;margin:4px 0 0;'>Your AI Learning Companion</p>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        if st.session_state["auth_view"] == "welcome":
            if st.button("Sign In", use_container_width=True, type="primary"):
                st.session_state["auth_view"] = "login"
                st.rerun()
            st.write("")
            if st.button("Create Account", use_container_width=True):
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"]  = "input_email"
                st.rerun()

        elif st.session_state["auth_view"] == "login":
            st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Sign In</h3>", unsafe_allow_html=True)
            with st.form("login_form"):
                u   = st.text_input("Username")
                p   = st.text_input("Password", type="password")
                sub = st.form_submit_button("Sign In →", use_container_width=True)
            if sub:
                try:
                    with get_conn() as conn:
                        row = conn.execute(
                            "SELECT password FROM users WHERE username=?", (u.strip(),)
                        ).fetchone()
                    if row and row["password"] == hash_password(p.strip()):
                        st.session_state["logged_in"] = True
                        st.session_state["username"]  = u.strip()
                        load_data()
                        st.session_state["page"]         = "landing"
                        st.session_state["current_view"] = "welcome_hub"
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                except Exception:
                    st.error("Database error. Please try again.")
            cl, cr = st.columns(2)
            with cl:
                if st.button("← Back", key="back_login", use_container_width=True):
                    st.session_state["auth_view"] = "welcome"
                    st.session_state["page"] = "landing"
                    st.rerun()
            with cr:
                if st.button("Forgot Password?", key="forgot_btn", use_container_width=True):
                    st.session_state["auth_view"]   = "forgot_password"
                    st.session_state["forgot_step"] = "verify_email"
                    st.rerun()

        elif st.session_state["auth_view"] == "register":
            st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Create Account</h3>", unsafe_allow_html=True)

            # Step indicator
            steps = ["Email", "Verify", "Setup"]
            step_idx = {"input_email": 0, "verify_otp": 1, "set_credentials": 2}.get(st.session_state["reg_step"], 0)
            dots_html = ""
            for si, s_label in enumerate(steps):
                color = "var(--accent)" if si <= step_idx else "var(--text-muted)"
                weight = "700" if si == step_idx else "400"
                dots_html += f"<span style='color:{color};font-weight:{weight};font-size:0.82rem;'>{s_label}</span>"
                if si < len(steps) - 1:
                    line_c = "var(--accent)" if si < step_idx else "var(--border)"
                    dots_html += f"<span style='display:inline-block;width:30px;height:2px;background:{line_c};vertical-align:middle;margin:0 8px;'></span>"
            st.markdown(f"<div style='text-align:center;margin-bottom:1.5rem;'>{dots_html}</div>", unsafe_allow_html=True)

            if st.session_state["reg_step"] == "input_email":
                with st.form("reg_email_form"):
                    ei   = st.text_input("Email Address", placeholder="name@gmail.com")
                    send = st.form_submit_button("Send Verification Code →", use_container_width=True)
                if send:
                    if not validate_email(ei.strip()):
                        st.error("Enter a valid email.")
                    else:
                        existing_emails = [m["identity"] for m in st.session_state["user_db"].values()]
                        if ei.strip() in existing_emails:
                            st.error("An account with this email already exists.")
                        else:
                            otp = str(random.randint(100000, 999999))
                            ok, err = send_otp_email(ei.strip(), otp)
                            if ok:
                                st.session_state.update({
                                    "generated_otp": otp,
                                    "otp_timestamp": datetime.datetime.now(),
                                    "temp_identity": ei.strip(),
                                    "reg_step":      "verify_otp",
                                })
                                st.success(f"OTP sent to {ei.strip()}!")
                                st.rerun()
                            else:
                                st.error(f"Failed: {err}")
                if st.button("← Cancel", use_container_width=True):
                    st.session_state["auth_view"] = "welcome"
                    st.session_state["page"] = "landing"
                    st.rerun()

            elif st.session_state["reg_step"] == "verify_otp":
                st.info(f"📬 OTP sent to **{st.session_state['temp_identity']}**")
                if is_otp_expired():
                    st.error("⏰ OTP expired.")
                    if st.button("Resend OTP", use_container_width=True):
                        otp = str(random.randint(100000, 999999))
                        ok, _ = send_otp_email(st.session_state["temp_identity"], otp)
                        if ok:
                            st.session_state.update({
                                "generated_otp": otp,
                                "otp_timestamp": datetime.datetime.now(),
                            })
                            st.success("New OTP sent!")
                            st.rerun()
                else:
                    with st.form("otp_form"):
                        entered = st.text_input("Enter 6-Digit OTP", max_chars=6, placeholder="______")
                        verify  = st.form_submit_button("Verify →", use_container_width=True)
                    if verify:
                        if entered.strip() == st.session_state["generated_otp"]:
                            st.session_state["reg_step"] = "set_credentials"
                            st.rerun()
                        else:
                            st.error("Incorrect OTP.")
                    if st.button("← Back", key="back_otp"):
                        st.session_state["reg_step"] = "input_email"
                        st.rerun()

            elif st.session_state["reg_step"] == "set_credentials":
                st.success(f"✅ Email verified: {st.session_state['temp_identity']}")
                with st.form("cred_form"):
                    ru   = st.text_input("Choose a Username")
                    rp   = st.text_input("Choose a Password", type="password")
                    rc   = st.text_input("Confirm Password", type="password")
                    done = st.form_submit_button("Create Account →", use_container_width=True)
                if done:
                    existing_emails = [m["identity"] for m in st.session_state["user_db"].values()]
                    if len(ru.strip()) < 3:
                        st.error("Username too short.")
                    elif ru.strip() in st.session_state["user_db"]:
                        st.error("Username taken.")
                    elif st.session_state["temp_identity"] in existing_emails:
                        st.error("An account with this email already exists.")
                    elif rp != rc:
                        st.error("Passwords don't match.")
                    elif len(rp) < 4:
                        st.error("Password too short.")
                    else:
                        new_user = {
                            "identity": st.session_state["temp_identity"],
                            "password": hash_password(rp.strip()),
                        }
                        st.session_state["user_db"][ru.strip()] = new_user
                        try:
                            with get_conn() as conn:
                                conn.execute(
                                    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                                    (ru.strip(), new_user["identity"], new_user["password"]),
                                )
                        except Exception:
                            pass
                        st.session_state["logged_in"] = True
                        st.session_state["username"]  = ru.strip()
                        load_data()
                        st.session_state["page"]         = "landing"
                        st.session_state["current_view"] = "welcome_hub"
                        st.rerun()

        elif st.session_state["auth_view"] == "forgot_password":
            st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Reset Password</h3>", unsafe_allow_html=True)
            if st.session_state["forgot_step"] == "verify_email":
                with st.form("forgot_form"):
                    re_email = st.text_input("Registered Email")
                    lookup   = st.form_submit_button("Send Reset OTP →", use_container_width=True)
                if lookup:
                    found = next(
                        (u for u, m in st.session_state["user_db"].items() if m["identity"] == re_email.strip()),
                        None,
                    )
                    if found:
                        otp = str(random.randint(100000, 999999))
                        ok, err = send_otp_email(re_email.strip(), otp)
                        if ok:
                            st.session_state.update({
                                "recovery_target_user": found,
                                "generated_otp":        otp,
                                "otp_timestamp":        datetime.datetime.now(),
                                "forgot_step":          "verify_otp",
                            })
                            st.success("OTP sent!")
                            st.rerun()
                        else:
                            st.error(f"Failed: {err}")
                    else:
                        st.error("No account found.")
                if st.button("← Back", key="back_forgot", use_container_width=True):
                    st.session_state["auth_view"] = "login"
                    st.rerun()

            elif st.session_state["forgot_step"] == "verify_otp":
                st.info("📬 OTP sent to your registered email.")
                if not is_otp_expired():
                    with st.form("forgot_otp_form"):
                        rotp = st.text_input("6-Digit OTP", max_chars=6)
                        vrfy = st.form_submit_button("Verify →", use_container_width=True)
                    if vrfy:
                        if rotp.strip() == st.session_state["generated_otp"]:
                            st.session_state["forgot_step"] = "reset_password"
                            st.rerun()
                        else:
                            st.error("Incorrect OTP.")
                else:
                    st.error("⏰ OTP expired.")

            elif st.session_state["forgot_step"] == "reset_password":
                with st.form("reset_form"):
                    np1  = st.text_input("New Password", type="password")
                    np2  = st.text_input("Confirm", type="password")
                    save = st.form_submit_button("Update Password →", use_container_width=True)
                if save:
                    if np1 != np2:
                        st.error("Passwords don't match.")
                    elif len(np1) < 4:
                        st.error("Too short.")
                    else:
                        target   = st.session_state["recovery_target_user"]
                        new_hash = hash_password(np1.strip())
                        st.session_state["user_db"][target]["password"] = new_hash
                        try:
                            with get_conn() as conn:
                                conn.execute(
                                    "UPDATE users SET password=? WHERE username=?",
                                    (new_hash, target),
                                )
                        except Exception:
                            pass
                        st.success("🔒 Password updated! Sign in now.")
                        st.session_state["auth_view"] = "login"
                        st.rerun()


# ---------------------- APP SHELL ----------------------

def render_sidebar_navigation():
    """Persistent sidebar navigation using st.sidebar."""
    st.markdown(
        "<div style='margin-bottom:1.5rem;'>"
        "<div style='font-size:1.3rem;font-weight:800;color:var(--text-primary);display:flex;align-items:center;gap:8px;'>"
        "✈️ StudyPilot</div>"
        "<div style='font-size:0.78rem;color:var(--text-muted);margin-top:2px;'>AI Learning Companion</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Primary navigation
    nav_items = [
        ("🏠", "Dashboard",  "welcome_hub"),
        ("💬", "AI Tutor",   "chat"),
        ("📝", "Summarizer", "summary"),
        ("📅", "Planner",    "planner"),
        ("📊", "Analytics",  "analytics"),
    ]

    for icon, label, view in nav_items:
        is_active = st.session_state["current_view"] == view
        if is_active:
            st.markdown(
                f"<div class='nav-active'>{icon}  {label}</div>",
                unsafe_allow_html=True,
            )
        else:
            if st.button(f"{icon}  {label}", key=f"nav_{view}", use_container_width=True):
                st.session_state["current_view"] = view
                st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:1rem 0;'>", unsafe_allow_html=True)

    # Secondary navigation
    secondary = [
        ("📚", "History",  "history"),
        ("👤", "Profile",  "profile"),
        ("⚙️", "Settings", "settings"),
    ]
    for icon, label, view in secondary:
        is_active = st.session_state["current_view"] == view
        if is_active:
            st.markdown(
                f"<div class='nav-active'>{icon}  {label}</div>",
                unsafe_allow_html=True,
            )
        else:
            if st.button(f"{icon}  {label}", key=f"nav_{view}", use_container_width=True):
                st.session_state["current_view"] = view
                st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid var(--border);margin:1rem 0;'>", unsafe_allow_html=True)

    # Theme toggle
    current_theme = st.session_state.get("theme", "light")
    t_icon  = "☀️" if current_theme == "dark" else "🌙"
    t_label = "Light Mode" if current_theme == "dark" else "Dark Mode"
    if st.button(f"{t_icon}  {t_label}", key="nav_theme", use_container_width=True):
        new_theme = "light" if current_theme == "dark" else "dark"
        st.session_state["theme"] = new_theme
        if st.session_state["logged_in"]:
            save_user_theme(st.session_state["username"], new_theme)
        st.rerun()

    # Logout
    if st.button("🚪  Logout", key="nav_logout", use_container_width=True):
        _do_logout()


def render_main_content():
    """Routes to the correct view based on session state."""
    # Auth pages
    if not st.session_state["logged_in"] and st.session_state["page"] in ["login", "register"]:
        render_login_page()
        return

    # Protected views
    protected = ["chat", "summary", "planner", "history", "profile", "settings", "analytics"]
    if st.session_state["current_view"] in protected and not st.session_state["logged_in"]:
        render_login_required_view()
        return

    view = st.session_state["current_view"]
    if view == "welcome_hub":
        render_dashboard_view()
    elif view == "chat":
        render_chat_view()
    elif view == "summary":
        render_summary_view()
    elif view == "planner":
        render_planner_view()
    elif view == "history":
        render_history_view()
    elif view == "profile":
        render_profile_view()
    elif view == "settings":
        render_settings_view()
    elif view == "analytics":
        render_analytics_view()


def render_app_shell():
    """Top-level app shell — sidebar + main content."""
    if st.session_state["logged_in"]:
        with st.sidebar:
            render_sidebar_navigation()
    else:
        # Logged-out top bar
        c_logo, _, c_login, c_reg = st.columns([3, 5, 1, 1.5])
        with c_logo:
            st.markdown(
                "<div style='font-size:1.2rem;font-weight:800;color:var(--text-primary);padding:0.5rem 0;display:flex;align-items:center;gap:6px;'>"
                "✈️ StudyPilot</div>",
                unsafe_allow_html=True,
            )
        with c_login:
            if st.button("Login", key="topbar_login"):
                st.session_state["page"] = "login"
                st.session_state["auth_view"] = "login"
                st.rerun()
        with c_reg:
            if st.button("Get Started", key="topbar_register", type="primary"):
                st.session_state["page"] = "register"
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"] = "input_email"
                st.rerun()

    render_main_content()


# ---------------------- CSS DESIGN SYSTEM ----------------------

def inject_css(theme="light"):
    """Inject the complete design system CSS based on the current theme."""

    if theme == "light":
        theme_vars = """
        :root {
            --bg-primary: #F8FAFC;
            --bg-secondary: #F1F5F9;
            --bg-card: #FFFFFF;
            --text-primary: #0F172A;
            --text-secondary: #475569;
            --text-muted: #94A3B8;
            --border: #E2E8F0;
            --accent: #4F46E5;
            --accent-hover: #4338CA;
            --accent-light: rgba(79, 70, 229, 0.06);
            --accent-gradient: linear-gradient(135deg, #4F46E5, #7C3AED);
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
            --shadow-lg: 0 12px 32px rgba(0,0,0,0.08);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --sidebar-bg: #FFFFFF;
            --sidebar-border: #E2E8F0;
        }
        """
    else:
        theme_vars = """
        :root {
            --bg-primary: #0B1120;
            --bg-secondary: #1E293B;
            --bg-card: #151D2E;
            --text-primary: #F1F5F9;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            --border: rgba(255,255,255,0.08);
            --accent: #818CF8;
            --accent-hover: #6366F1;
            --accent-light: rgba(129, 140, 248, 0.1);
            --accent-gradient: linear-gradient(135deg, #6366F1, #8B5CF6);
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.2);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.3);
            --shadow-lg: 0 12px 32px rgba(0,0,0,0.4);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
            --sidebar-bg: #111827;
            --sidebar-border: rgba(255,255,255,0.06);
        }
        """

    st.markdown(f"<style>{theme_vars}</style>", unsafe_allow_html=True)

    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* ── Reset Streamlit chrome ── */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="collapsedControl"],
    .viewerBadge_container__1QSob { display:none !important; }

    /* ── Global ── */
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    .stApp {
        background: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
        border-right: 1px solid var(--sidebar-border) !important;
        width: 260px !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding: 1.5rem 1rem !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        color: var(--text-secondary) !important;
        text-align: left !important;
        justify-content: flex-start !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        height: 40px !important;
        border-radius: var(--radius-sm) !important;
        padding: 0 12px !important;
        margin-bottom: 2px !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: var(--accent-light) !important;
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 0.8rem 0 !important;
    }

    /* Active nav item */
    .nav-active {
        background: var(--accent-light);
        color: var(--accent);
        font-weight: 700;
        font-size: 0.9rem;
        padding: 8px 12px;
        border-radius: var(--radius-sm);
        border-left: 3px solid var(--accent);
        margin-bottom: 2px;
    }

    /* ── Typography ── */
    .view-title {
        font-weight: 800;
        font-size: 1.6rem;
        color: var(--text-primary);
        margin: 0 0 4px 0;
        letter-spacing: -0.5px;
    }
    .view-subtitle {
        color: var(--text-muted);
        font-size: 0.92rem;
        margin: 0 0 1.5rem 0;
    }
    .card-label {
        font-weight: 700;
        font-size: 0.78rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 0 0 10px 0;
    }

    /* ── Cards ── */
    .content-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.5rem;
        box-shadow: var(--shadow-sm);
        margin-bottom: 0;
    }
    .action-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.8rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-sm);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .action-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
        border-color: var(--accent);
    }
    .auth-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 2.5rem;
        box-shadow: var(--shadow-md);
    }

    /* Stats */
    .stat-mini {
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 0.8rem;
        text-align: center;
        flex: 1;
    }
    .stat-num {
        font-size: 1.4rem;
        font-weight: 800;
        color: var(--accent);
    }
    .stat-label {
        font-size: 0.72rem;
        color: var(--text-muted);
        margin-top: 2px;
    }

    /* Avatar */
    .avatar-circle {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: var(--accent-gradient);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        font-weight: 800;
        flex-shrink: 0;
    }

    /* Badges */
    .badge {
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .badge-weak {
        background: #F59E0B;
        color: #000;
        font-size: 0.65rem;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: 700;
        margin-left: 6px;
    }

    /* Table */
    .th {
        padding: 10px 12px;
        text-align: left;
        color: var(--text-muted);
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .td {
        padding: 10px 12px;
        color: var(--text-primary);
        font-size: 0.88rem;
    }

    /* ── Empty States ── */
    .empty-state, .chat-empty {
        text-align: center;
        padding: 3rem 2rem;
    }

    /* ── Chat Bubbles ── */
    .chat-row { display: flex; margin-bottom: 8px; align-items: flex-start; gap: 8px; }
    .user-row { justify-content: flex-end; }
    .bot-row  { justify-content: flex-start; }
    .bot-avatar {
        width: 32px; height: 32px; border-radius: 50%;
        background: var(--bg-secondary); border: 1px solid var(--border);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.9rem; flex-shrink: 0; margin-top: 4px;
    }
    .chat-msg {
        padding: 0.8rem 1.1rem;
        border-radius: 16px;
        font-size: 0.92rem;
        line-height: 1.6;
        max-width: 75%;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    .user-bubble {
        background: var(--accent-gradient) !important;
        color: #fff !important;
        border-bottom-right-radius: 4px !important;
    }
    .bot-bubble {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-bottom-left-radius: 4px !important;
    }
    .bot-bubble p  { color: var(--text-primary) !important; margin: 0.3rem 0 !important; }
    .bot-bubble strong { color: var(--accent) !important; font-weight: 700 !important; }
    .bot-bubble em { color: var(--accent) !important; }
    .bot-bubble h1,.bot-bubble h2,.bot-bubble h3,.bot-bubble h4 { color: var(--accent) !important; margin: 0.5rem 0 0.2rem !important; }
    .bot-bubble ul, .bot-bubble ol { padding-left: 1.3rem !important; margin: 0.3rem 0 !important; }
    .bot-bubble li { color: var(--text-primary) !important; margin: 0.2rem 0 !important; }
    .bot-bubble code { background: var(--bg-secondary) !important; color: #10B981 !important; padding: 1px 5px !important; border-radius: 4px !important; font-size: 0.88em !important; }
    .bot-bubble pre { background: var(--bg-secondary) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; padding: 0.6rem 1rem !important; overflow-x: auto !important; margin: 0.4rem 0 !important; }
    .bot-bubble pre code { background: transparent !important; color: #10B981 !important; padding: 0 !important; }
    .bot-bubble blockquote { border-left: 3px solid var(--accent) !important; background: var(--bg-secondary) !important; padding: 0.4rem 0.8rem !important; border-radius: 0 6px 6px 0 !important; margin: 0.4rem 0 !important; }

    /* ── History panel (inside views) ── */
    .history-panel {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1rem;
        box-shadow: var(--shadow-sm);
    }

    /* ── Buttons ── */
    .stButton > button {
        background: var(--bg-secondary) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        height: 38px !important;
        font-size: 0.88rem !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background: var(--accent) !important;
        color: #fff !important;
        border-color: var(--accent) !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--accent-gradient) !important;
        color: #fff !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(79, 70, 229, 0.35) !important;
    }

    /* Form inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px var(--accent-light) !important;
    }

    /* Form submit button */
    [data-testid="stFormSubmitButton"] button {
        background: var(--accent-gradient) !important;
        color: #fff !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        height: 42px !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.2) !important;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(79, 70, 229, 0.3) !important;
    }

    /* Forms */
    [data-testid="stForm"] { border: none !important; background: transparent !important; padding: 0 !important; }
    .stAlert { border-radius: var(--radius-sm) !important; }

    /* History list items */
    .history-panel .stButton > button {
        background: transparent !important;
        border: none !important;
        color: var(--text-secondary) !important;
        font-size: 0.82rem !important;
        font-weight: 400 !important;
        height: 32px !important;
        padding: 4px 8px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 6px !important;
    }
    .history-panel .stButton > button:hover {
        background: var(--accent-light) !important;
        color: var(--text-primary) !important;
    }

    /* Suggestion chips */
    div[data-testid="column"]:has(button[key^="suggest_"]) .stButton > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        height: auto !important;
        padding: 10px 14px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: var(--radius-md) !important;
        line-height: 1.4 !important;
    }
    div[data-testid="column"]:has(button[key^="suggest_"]) .stButton > button:hover {
        border-color: var(--accent) !important;
        background: var(--accent-light) !important;
        color: var(--accent) !important;
    }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        .action-card { padding: 1.2rem; }
        .view-title { font-size: 1.3rem; }
        .chat-msg { max-width: 90%; }
    }

    /* ── Animations ── */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .content-card, .action-card, .auth-card {
        animation: fadeIn 0.3s ease forwards;
    }

    </style>""", unsafe_allow_html=True)


# ---------------------- ENTRY POINT ----------------------

st.set_page_config(page_title="StudyPilot", page_icon="✈️", layout="wide")

init_db()

defaults = {
    "theme": "light",
    "page": "landing",
    "logged_in": False, "username": "", "message_history": {},
    "show_profile_tray": False, "active_menu_item_id": "", "active_bubble_menu_id": "",
    "current_view": "welcome_hub", "auth_view": "welcome",
    "reg_step": "input_email", "forgot_step": "verify_email",
    "generated_otp": None, "otp_timestamp": None,
    "temp_identity": "", "recovery_target_user": "",
    "editing_item_id": "", "rename_feature_target": "",
    "show_copy_summary": False, "user_db": {},
    "all_chats": {}, "active_chat_id": "",
    "all_summaries": {}, "active_summary_id": "",
    "all_plans": {}, "active_planner_id": "",
    "nav_history_stack": [],
    "sidebar_open": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "users_loaded" not in st.session_state:
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT username, email, password FROM users").fetchall()
            st.session_state["user_db"] = {
                r["username"]: {"identity": r["email"], "password": r["password"]}
                for r in rows
            }
    except Exception:
        pass
    st.session_state["users_loaded"] = True

if st.session_state["logged_in"] and st.session_state["username"]:
    st.session_state["theme"] = get_user_theme(st.session_state["username"])

inject_css(st.session_state.get("theme", "light"))
render_app_shell()
