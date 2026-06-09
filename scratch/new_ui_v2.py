
# ============================================================
# UI HELPERS
# ============================================================

def _do_logout():
    """Centralised logout — preserves sidebar preference."""
    save_data()
    sidebar_pref = st.session_state.get("sidebar_open", True)
    for k, v in {
        "logged_in": False, "username": "", "auth_view": "welcome",
        "page": "landing", "current_view": "home",
        "all_chats": {}, "all_summaries": {}, "all_plans": {},
        "active_chat_id": "", "active_summary_id": "", "active_planner_id": "",
        "nav_history_stack": [], "activity_filter": "All",
    }.items():
        st.session_state[k] = v
    st.session_state["sidebar_open"] = sidebar_pref
    st.rerun()


def _time_greeting():
    h = datetime.datetime.now().hour
    return "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")


def _sidebar_mode():
    """'feature' for Chat/Summary/Planner; 'global' everywhere else."""
    return "feature" if st.session_state.get("current_view") in {"chat", "summary", "planner"} else "global"


def _require_login(view):
    """Redirect to login if user is not authenticated."""
    st.session_state["page"] = "login"
    st.session_state["auth_view"] = "login"
    st.session_state["_intended_view"] = view
    st.rerun()


# ============================================================
# HISTORY PANEL — used inside feature sidebars
# ============================================================

def render_history_panel(feature_key, friendly_name):
    """Compact history list for the contextual sidebar."""
    if feature_key == "chat":
        history_dict = st.session_state["all_chats"]
        active_id    = st.session_state["active_chat_id"]
    elif feature_key == "summary":
        history_dict = st.session_state["all_summaries"]
        active_id    = st.session_state["active_summary_id"]
    else:
        history_dict = st.session_state["all_plans"]
        active_id    = st.session_state["active_planner_id"]

    if st.button(f"＋  New {friendly_name}", use_container_width=True, key=f"new_{feature_key}_sb"):
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
                "subjects": "", "weak": "", "mood": "", "schedule": [], "title": "Untitled Plan",
            }
            st.session_state["active_planner_id"] = nid
        save_data()
        st.rerun()

    if not history_dict:
        st.markdown(
            f"<div class='sidebar-empty'>📂 No {friendly_name.lower()}s yet</div>",
            unsafe_allow_html=True,
        )
        return

    open_menu = st.session_state.get("active_menu_item_id", "")

    for item_id in list(history_dict.keys()):
        if feature_key == "chat":
            msgs  = history_dict[item_id]
            label = msgs[0]["text"][:24] + "…" if msgs else "Untitled Chat"
        else:
            label = history_dict[item_id].get("title", "Untitled")[:24]

        is_active = item_id == active_id
        is_open   = open_menu == item_id
        prefix    = "● " if is_active else ""

        col_sel, col_dot = st.columns([8, 2])
        with col_sel:
            if st.button(f"{prefix}{label}", key=f"sel_{item_id}_{feature_key}", use_container_width=True):
                if feature_key == "chat":      st.session_state["active_chat_id"]    = item_id
                elif feature_key == "summary": st.session_state["active_summary_id"] = item_id
                else:                          st.session_state["active_planner_id"]  = item_id
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
                    if feature_key != "chat":
                        history_dict[eid]["title"] = new_title.strip()
                    save_data()
                    st.session_state["editing_item_id"] = ""
                    st.rerun()


# ============================================================
# SIDEBAR — contextual dispatch
# ============================================================

def render_sidebar():
    mode = _sidebar_mode()
    if mode == "feature":
        _render_feature_sidebar()
    else:
        _render_global_sidebar()


def _render_global_sidebar():
    """Sidebar for Home, Analytics, Activity, Profile, Settings."""

    # ── Logo ──
    st.markdown(
        "<div class='sb-logo'>✈️ <span>StudyPilot</span></div>"
        "<div class='sb-tagline'>AI Learning Companion</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── User Profile ──
    if st.session_state["logged_in"]:
        uname   = st.session_state["username"]
        email   = st.session_state["user_db"].get(uname, {}).get("identity", "")
        initial = uname[0].upper()
        st.markdown(
            f"""<div class='sb-profile'>
                <div class='sb-avatar'>{initial}</div>
                <div>
                    <div class='sb-uname'>{uname}</div>
                    <div class='sb-email'>{email}</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Features nav ──
    st.markdown("<div class='sb-section-label'>📌 Features</div>", unsafe_allow_html=True)

    nav_items = [
        ("🏠", "Home",             "home"),
        ("💬", "AI Tutor",         "chat"),
        ("📝", "Smart Summarizer", "summary"),
        ("📅", "Adaptive Planner", "planner"),
        ("📊", "Analytics",        "analytics"),
    ]
    protected = {"chat", "summary", "planner", "analytics"}

    for icon, label, view in nav_items:
        is_active = st.session_state["current_view"] == view
        if is_active:
            st.markdown(f"<div class='nav-item-active'>{icon}  {label}</div>", unsafe_allow_html=True)
        else:
            if st.button(f"{icon}  {label}", key=f"sib_{view}", use_container_width=True):
                if view in protected and not st.session_state["logged_in"]:
                    _require_login(view)
                else:
                    st.session_state["current_view"] = view
                    st.rerun()

    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Activity ──
    st.markdown("<div class='sb-section-label'>📜 Activity</div>", unsafe_allow_html=True)
    is_activity = st.session_state["current_view"] == "activity"
    if is_activity:
        st.markdown("<div class='nav-item-active'>📊  Activity Dashboard</div>", unsafe_allow_html=True)
    else:
        if st.button("📊  Activity Dashboard", key="sib_activity", use_container_width=True):
            if not st.session_state["logged_in"]:
                _require_login("activity")
            else:
                st.session_state["current_view"] = "activity"
                st.rerun()

    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Preferences ──
    st.markdown("<div class='sb-section-label'>🎨 Preferences</div>", unsafe_allow_html=True)
    theme   = st.session_state.get("theme", "light")
    t_icon  = "☀️" if theme == "dark" else "🌙"
    t_label = "Light Mode" if theme == "dark" else "Dark Mode"
    if st.button(f"{t_icon}  {t_label}", key="sib_theme", use_container_width=True):
        new_theme = "light" if theme == "dark" else "dark"
        st.session_state["theme"] = new_theme
        if st.session_state["logged_in"]:
            save_user_theme(st.session_state["username"], new_theme)
        st.rerun()

    # ── Pinned Logout ──
    st.markdown("<div class='sb-spacer'></div>", unsafe_allow_html=True)
    if st.session_state["logged_in"]:
        st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)
        if st.button("🚪  Logout", key="sib_logout", use_container_width=True):
            _do_logout()


def _render_feature_sidebar():
    """Sidebar for AI Tutor / Summarizer / Planner — shows feature history only."""
    view = st.session_state["current_view"]

    # ── Compact profile ──
    if st.session_state["logged_in"]:
        uname   = st.session_state["username"]
        initial = uname[0].upper()
        st.markdown(
            f"""<div class='sb-profile-compact'>
                <div class='sb-avatar-sm'>{initial}</div>
                <div class='sb-uname'>{uname}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Back to Home ──
    if st.button("← Home", key="sib_back_home", use_container_width=True):
        st.session_state["current_view"] = "home"
        st.rerun()

    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)

    # ── Feature-specific history ──
    if view == "chat":
        st.markdown("<div class='sb-section-label'>📜 Chat History</div>", unsafe_allow_html=True)
        render_history_panel("chat", "Chat")
    elif view == "summary":
        st.markdown("<div class='sb-section-label'>📜 Summary History</div>", unsafe_allow_html=True)
        render_history_panel("summary", "Summary")
    elif view == "planner":
        st.markdown("<div class='sb-section-label'>📜 Plan History</div>", unsafe_allow_html=True)
        render_history_panel("planner", "Planner")

    # ── Pinned Logout ──
    st.markdown("<div class='sb-spacer'></div>", unsafe_allow_html=True)
    if st.session_state["logged_in"]:
        st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)
        if st.button("🚪  Logout", key="sib_logout_feat", use_container_width=True):
            _do_logout()


# ============================================================
# NAVBAR
# ============================================================

def render_navbar():
    """Sticky top navbar: ☰ + logo | Features popover | auth/profile."""
    is_logged_in = st.session_state["logged_in"]

    c_left, c_feat, c_right = st.columns([3, 4, 3])

    # ── Left: toggle + logo ──
    with c_left:
        hl, hr = st.columns([1, 5])
        with hl:
            icon = "✕" if st.session_state.get("sidebar_open", True) else "☰"
            if st.button(icon, key="nav_toggle", help="Toggle sidebar"):
                st.session_state["sidebar_open"] = not st.session_state.get("sidebar_open", True)
                st.rerun()
        with hr:
            if st.button("✈️  StudyPilot", key="nav_logo"):
                st.session_state["current_view"] = "home"
                st.session_state["page"]         = "landing"
                st.rerun()

    # ── Center: Features popover ──
    with c_feat:
        _, pop_col, _ = st.columns([1, 4, 1])
        with pop_col:
            with st.popover("✦  Features  ▾", use_container_width=True):
                feature_list = [
                    ("💬", "AI Tutor",         "chat"),
                    ("📝", "Smart Summarizer",  "summary"),
                    ("📅", "Adaptive Planner",  "planner"),
                ]
                for icon, label, view in feature_list:
                    if st.button(f"{icon}  {label}", key=f"feat_{view}_nav", use_container_width=True):
                        if not is_logged_in:
                            _require_login(view)
                        else:
                            st.session_state["current_view"] = view
                            st.rerun()

    # ── Right: auth / profile ──
    with c_right:
        if is_logged_in:
            uname = st.session_state["username"]
            _, pr = st.columns([1, 5])
            with pr:
                with st.popover(f"👤  {uname}", use_container_width=True):
                    if st.button("👤  Profile",  key="nav_profile",  use_container_width=True):
                        st.session_state["current_view"] = "profile"
                        st.rerun()
                    if st.button("⚙️  Settings", key="nav_settings", use_container_width=True):
                        st.session_state["current_view"] = "settings"
                        st.rerun()
                    st.markdown("<div class='sb-divider'></div>", unsafe_allow_html=True)
                    if st.button("🚪  Logout",   key="nav_logout_pop", use_container_width=True):
                        _do_logout()
        else:
            cl, cr = st.columns(2)
            with cl:
                if st.button("Login", key="nav_login", use_container_width=True):
                    st.session_state["page"]      = "login"
                    st.session_state["auth_view"] = "login"
                    st.rerun()
            with cr:
                if st.button("Get Started", key="nav_register", type="primary", use_container_width=True):
                    st.session_state["page"]      = "register"
                    st.session_state["auth_view"] = "register"
                    st.session_state["reg_step"]  = "input_email"
                    st.rerun()

    st.markdown("<div class='navbar-divider'></div>", unsafe_allow_html=True)


# ============================================================
# HOME VIEW — unified landing + dashboard
# ============================================================

def render_home_view():
    is_logged_in = st.session_state["logged_in"]

    if is_logged_in:
        # ── Authenticated dashboard ──
        greeting = _time_greeting()
        uname    = st.session_state["username"]

        st.markdown(
            f"<div class='home-welcome'>"
            f"<h1 class='home-greeting'>{greeting}, {uname} 👋</h1>"
            f"<p class='home-subtext'>Ready to study today?</p>"
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
        for col, icon, num, label, color in [
            (c1, "💬", total_chats,     "Chats",      "#6366F1"),
            (c2, "📝", total_summaries, "Summaries",  "#10B981"),
            (c3, "📅", total_plans,     "Plans",      "#F59E0B"),
            (c4, "⏱️", total_mins,      "Study Mins", "#EC4899"),
        ]:
            with col:
                st.markdown(
                    f"""<div class='stat-card'>
                        <div class='stat-icon'>{icon}</div>
                        <div class='stat-num' style='color:{color};'>{num}</div>
                        <div class='stat-label'>{label}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    else:
        # ── Unauthenticated hero ──
        st.markdown(
            """<div class='hero-section'>
                <div class='hero-badge'>✦ AI-Powered Learning</div>
                <h1 class='hero-title'>Learn Faster.<br>Remember More.</h1>
                <p class='hero-sub'>AI tutoring, intelligent summarization, and adaptive study planning in one seamless experience.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        _, cb1, cb2, _ = st.columns([2, 1.5, 1.2, 2])
        with cb1:
            if st.button("Start Learning Free →", key="hero_cta", use_container_width=True, type="primary"):
                st.session_state["page"]      = "register"
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"]  = "input_email"
                st.rerun()
        with cb2:
            if st.button("Sign In", key="hero_signin", use_container_width=True):
                st.session_state["page"]      = "login"
                st.session_state["auth_view"] = "login"
                st.rerun()

    # ── Feature Cards (all users) ──
    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    st.markdown("<p class='section-label'>🚀 Features</p>", unsafe_allow_html=True)

    cards = [
        ("💬", "AI Tutor",         "chat",    "#6366F1", "Ask questions, get explanations, practice coding and ML concepts with your personal AI tutor."),
        ("📝", "Smart Summarizer",  "summary", "#10B981", "Transform long notes, articles, and PDFs into concise, structured study material in seconds."),
        ("📅", "Adaptive Planner", "planner", "#F59E0B", "Generate mood-based Pomodoro schedules that adapt to how you feel — because wellbeing matters."),
    ]
    fc1, fc2, fc3 = st.columns(3)
    for col, (icon, title, view, color, desc) in zip([fc1, fc2, fc3], cards):
        with col:
            st.markdown(
                f"""<div class='feature-card' style='border-top:3px solid {color};'>
                    <div class='fc-icon' style='color:{color};'>{icon}</div>
                    <div class='fc-title'>{title}</div>
                    <div class='fc-desc'>{desc}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button(f"Open {title}", key=f"home_card_{view}", use_container_width=True):
                if not st.session_state["logged_in"]:
                    _require_login(view)
                else:
                    st.session_state["current_view"] = view
                    st.rerun()

    # ── Recent Activity (logged-in only) ──
    if is_logged_in:
        recent = []
        for cid, msgs in list(st.session_state["all_chats"].items())[:3]:
            label = msgs[0]["text"][:40] + "…" if msgs else "Untitled Chat"
            recent.append(("💬", label, cid, "chat", "active_chat_id"))
        for sid, data in list(st.session_state["all_summaries"].items())[:2]:
            label = data.get("title", "Untitled")[:40]
            recent.append(("📝", label, sid, "summary", "active_summary_id"))
        for pid, data in list(st.session_state["all_plans"].items())[:2]:
            label = data.get("title", "Untitled Plan")[:40]
            recent.append(("📅", label, pid, "planner", "active_planner_id"))

        if recent:
            st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
            st.markdown("<p class='section-label'>🕐 Recent Activity</p>", unsafe_allow_html=True)
            for icon, label, item_id, view, key in recent[:5]:
                rl, rr = st.columns([9, 1])
                with rl:
                    st.markdown(
                        f"<div class='recent-item'><span>{icon}</span> {label}</div>",
                        unsafe_allow_html=True,
                    )
                with rr:
                    if st.button("→", key=f"recent_{item_id}", use_container_width=True):
                        st.session_state[key] = item_id
                        st.session_state["current_view"] = view
                        st.rerun()


# ============================================================
# ACTIVITY VIEW — chronological timeline with filters
# ============================================================

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
                <p style='color:var(--text-muted);'>Start using AI Tutor, Summarizer, or Planner to build your history.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # ── Render timeline ──
    for idx, item in enumerate(items):
        col_line, col_content, col_btn = st.columns([0.5, 8.5, 1])

        with col_line:
            st.markdown(
                f"<div class='timeline-dot' style='background:{item[\"color\"]};'></div>",
                unsafe_allow_html=True,
            )

        with col_content:
            st.markdown(
                f"""<div class='timeline-card'>
                    <div class='timeline-header'>
                        <span class='timeline-badge' style='background:{item["color"]}20;color:{item["color"]};'>
                            {item["icon"]} {item["type"]}
                        </span>
                        <span class='timeline-date'>{item["date"]}</span>
                    </div>
                    <div class='timeline-label'>{item["label"]}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        with col_btn:
            if st.button("Open →", key=f"act_open_{item['id']}_{idx}", use_container_width=True):
                st.session_state[item["key"]] = item["id"]
                st.session_state["current_view"] = item["view"]
                st.rerun()

        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


# ============================================================
# CHAT VIEW
# ============================================================

def render_chat_view():
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
    active_chat    = st.session_state["all_chats"].get(active_chat_id, [])

    # Handle suggestion chip auto-send
    prefill = st.session_state.pop("_chat_prefill", None)
    if prefill:
        with st.spinner("Thinking…"):
            ans, sentiment = get_chat_response(prefill, active_chat)
        if sentiment["compound"] >= 0.05:  st.toast("Positive vibes! 😊")
        elif sentiment["compound"] <= -0.05: st.toast("You seem stressed. Take it easy! 💙")
        active_chat.append({"role": "user",      "text": prefill})
        active_chat.append({"role": "assistant", "text": ans})
        st.session_state["all_chats"][active_chat_id] = active_chat
        save_chat_immediately(active_chat_id, active_chat, st.session_state["username"])
        st.rerun()

    # ── Empty state with suggestion chips ──
    if not active_chat:
        st.markdown(
            """<div class='chat-empty'>
                <div style='font-size:3.5rem;margin-bottom:1rem;opacity:0.8;'>✈️</div>
                <h3 class='chat-empty-title'>What would you like to learn?</h3>
                <p class='chat-empty-sub'>Pick a suggestion or type your own question below</p>
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
                    f"<div class='chat-row user-row'>"
                    f"<div class='chat-msg user-bubble'>{msg['text']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='chat-row bot-row'>"
                    f"<div class='bot-avatar'>🤖</div>"
                    f"<div class='chat-msg bot-bubble'>{msg['text']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                _, _, cc = st.columns([7, 2, 1])
                with cc:
                    if st.button("📋", key=f"cp_{msg_id}", help="Copy"):
                        try:
                            pyperclip.copy(msg["text"])
                        except Exception:
                            pass
                        st.toast("Copied! ✅")

    # ── Input form ──
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        chat_input = st.text_input(
            "", placeholder="Ask anything about Python, ML, DSA…",
            label_visibility="collapsed",
        )
        send = st.form_submit_button("Send →", use_container_width=True)

    if send and chat_input.strip():
        with st.spinner("Thinking…"):
            ans, sentiment = get_chat_response(chat_input, active_chat)
        if sentiment["compound"] >= 0.05:  st.toast("Positive vibes! 😊")
        elif sentiment["compound"] <= -0.05: st.toast("You seem stressed. Take it easy! 💙")
        active_chat.append({"role": "user",      "text": chat_input})
        active_chat.append({"role": "assistant", "text": ans})
        st.session_state["all_chats"][active_chat_id] = active_chat
        save_chat_immediately(active_chat_id, active_chat, st.session_state["username"])
        st.rerun()


# ============================================================
# SUMMARY VIEW
# ============================================================

def render_summary_view():
    st.markdown(
        "<h2 class='view-title'>📝 Smart Summarizer</h2>"
        "<p class='view-subtitle'>Transform lengthy notes into concise, structured study material</p>",
        unsafe_allow_html=True,
    )

    if not st.session_state["all_summaries"]:
        nid = f"summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state["all_summaries"][nid] = {
            "text": "", "summary": "", "word_count": 80,
            "format_style": "Plain Text", "title": "Untitled Summary",
        }
        st.session_state["active_summary_id"] = nid
        save_data()
    elif not st.session_state["active_summary_id"]:
        st.session_state["active_summary_id"] = list(st.session_state["all_summaries"].keys())[0]

    node = st.session_state["all_summaries"].get(st.session_state["active_summary_id"])

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
                formatted, engine = get_summary(raw_text, target_words, fmt, st.session_state["username"])
                node["summary"]     = formatted
                node["raw_summary"] = formatted
                node["engine"]      = engine
                if node["title"].startswith("Untitled"):
                    node["title"] = raw_text[:18] + "..."
                st.session_state["all_summaries"][st.session_state["active_summary_id"]] = node
                save_data()
                st.rerun()

    if node["summary"]:
        st.markdown("<div class='content-card' style='margin-top:1.5rem;'>", unsafe_allow_html=True)
        st.markdown("<p class='card-label'>📝 Generated Summary</p>", unsafe_allow_html=True)
        st.markdown(node["summary"])
        c_copy, _ = st.columns([1, 3])
        with c_copy:
            if st.button("📋 Copy Summary", key="cp_sum", use_container_width=True):
                st.session_state["show_copy_summary"] = True
        if st.session_state.get("show_copy_summary", False):
            st.code(node.get("raw_summary", node["summary"]), language="text")
            if st.button("✕ Close", key="close_copy_sum"):
                st.session_state["show_copy_summary"] = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PLANNER VIEW
# ============================================================

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

            if mood_score <= -0.3:   work_mins, break_mins, mode = 20, 10, "gentle"
            elif mood_score <= -0.1: work_mins, break_mins, mode = 25, 10, "mellow"
            else:                    work_mins, break_mins, mode = 25, 5,  "classic"

            weighted = []
            for s in slist:
                weighted.append(s)
                if s.lower() == weak.strip().lower():
                    weighted.append(s)

            schedule, t, i, session_num = [], start_dt, 0, 1
            while t < end_dt:
                remaining = int((end_dt - t).total_seconds() / 60)
                if remaining < work_mins: break
                sub         = weighted[i % len(weighted)]
                actual_work = min(work_mins, remaining)
                end_session = t + datetime.timedelta(minutes=actual_work)
                actual_break = min(break_mins, int((end_dt - end_session).total_seconds() / 60))
                resume_at   = end_session + datetime.timedelta(minutes=actual_break)
                schedule.append({
                    "session": session_num,
                    "start":   t.strftime("%I:%M %p"),
                    "end":     end_session.strftime("%I:%M %p"),
                    "subject": sub,
                    "is_weak": sub.lower() == weak.strip().lower(),
                    "break_len": actual_break,
                    "resume":  resume_at.strftime("%I:%M %p"),
                    "mode":    mode,
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


# ============================================================
# ANALYTICS VIEW
# ============================================================

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
    for col, icon, num, label, color in [
        (c1, "⏱️", total_minutes,   "Study Minutes", "var(--accent)"),
        (c2, "📅", total_plans,     "Schedules",     "#10B981"),
        (c3, "💬", total_chats,     "Tutor Queries", "#6366F1"),
        (c4, "📝", total_summaries, "Summaries",     "#F59E0B"),
    ]:
        with col:
            st.markdown(
                f"""<div class='stat-card'>
                    <div class='stat-icon'>{icon}</div>
                    <div class='stat-num' style='color:{color};'>{num}</div>
                    <div class='stat-label'>{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )

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


# ============================================================
# PROFILE & SETTINGS VIEWS
# ============================================================

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


def render_settings_view():
    st.markdown(
        "<h2 class='view-title'>⚙️ Settings</h2>"
        "<p class='view-subtitle'>Manage your account and preferences</p>",
        unsafe_allow_html=True,
    )
    uid = st.session_state["username"]
    st.markdown("<div class='content-card'>", unsafe_allow_html=True)
    st.markdown("<p class='card-label'>🔒 Change Password</p>", unsafe_allow_html=True)
    with st.form("settings_form"):
        old_pwd  = st.text_input("Current Password", type="password")
        new_pwd  = st.text_input("New Password",     type="password")
        conf_pwd = st.text_input("Confirm Password", type="password")
        save_btn = st.form_submit_button("Update Password", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if save_btn:
        if not old_pwd or not new_pwd or not conf_pwd:
            st.error("Please fill all fields.")
        elif new_pwd != conf_pwd:
            st.error("Passwords don't match.")
        elif len(new_pwd) < 4:
            st.error("Password must be at least 4 characters.")
        else:
            with get_conn() as conn:
                row = conn.execute("SELECT password FROM users WHERE username=?", (uid,)).fetchone()
            if row and row["password"] == hash_password(old_pwd):
                new_hash = hash_password(new_pwd)
                with get_conn() as conn:
                    conn.execute("UPDATE users SET password=? WHERE username=?", (new_hash, uid))
                st.session_state["user_db"][uid]["password"] = new_hash
                st.success("Password updated!")
            else:
                st.error("Incorrect current password.")

    st.markdown(
        "<div class='content-card' style='border:1px solid rgba(239,68,68,0.3);margin-top:1.5rem;'>",
        unsafe_allow_html=True,
    )
    st.markdown("<p class='card-label' style='color:#EF4444;'>⚠️ Danger Zone</p>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:var(--text-muted);font-size:0.88rem;margin:0 0 1rem 0;'>"
        "Permanently delete all chats, summaries, and plans. Cannot be undone.</p>",
        unsafe_allow_html=True,
    )
    if st.button("🗑️ Clear All History", key="clear_all", use_container_width=True):
        with get_conn() as conn:
            conn.execute("DELETE FROM chats    WHERE username=?", (uid,))
            conn.execute("DELETE FROM summaries WHERE username=?", (uid,))
            conn.execute("DELETE FROM plans    WHERE username=?", (uid,))
        for k in ["all_chats", "all_summaries", "all_plans"]:
            st.session_state[k] = {}
        for k in ["active_chat_id", "active_summary_id", "active_planner_id"]:
            st.session_state[k] = ""
        st.toast("History cleared! 🧹")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# AUTH — login / register / forgot password
# ============================================================

def render_login_required_view():
    st.markdown("<div style='padding-top:4rem;'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        view_name = st.session_state.get("current_view", "").replace("_", " ").title()
        st.markdown(
            f"""<div class='content-card' style='text-align:center;padding:3rem;'>
                <div style='font-size:3rem;margin-bottom:1rem;'>🔒</div>
                <h3 style='font-weight:800;color:var(--text-primary);margin:0 0 0.5rem;'>Sign in to continue</h3>
                <p style='color:var(--text-muted);margin:0 0 2rem;'>Access <strong>{view_name}</strong> and save your progress</p>
            </div>""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sign In", key="req_login", use_container_width=True, type="primary"):
                st.session_state["page"]      = "login"
                st.session_state["auth_view"] = "login"
                st.rerun()
        with c2:
            if st.button("Create Account", key="req_reg", use_container_width=True):
                st.session_state["page"]      = "register"
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"]  = "input_email"
                st.rerun()


def render_login_page():
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            """<div style='text-align:center;margin-bottom:2rem;'>
                <div style='font-size:2.5rem;'>✈️</div>
                <h1 style='font-weight:900;font-size:2rem;margin:0.3rem 0 0;letter-spacing:-1px;
                    background:linear-gradient(135deg,#4F46E5,#7C3AED);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
                    StudyPilot
                </h1>
                <p style='color:var(--text-muted);font-size:0.88rem;margin:4px 0 0;'>Your AI Learning Companion</p>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='auth-card'>", unsafe_allow_html=True)

        av = st.session_state["auth_view"]

        if av == "welcome":
            if st.button("Sign In", use_container_width=True, type="primary"):
                st.session_state["auth_view"] = "login"; st.rerun()
            st.write("")
            if st.button("Create Account", use_container_width=True):
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"]  = "input_email"
                st.rerun()

        elif av == "login":
            st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Sign In</h3>", unsafe_allow_html=True)
            with st.form("login_form"):
                u   = st.text_input("Username")
                p   = st.text_input("Password", type="password")
                sub = st.form_submit_button("Sign In →", use_container_width=True)
            if sub:
                try:
                    with get_conn() as conn:
                        row = conn.execute("SELECT password FROM users WHERE username=?", (u.strip(),)).fetchone()
                    if row and row["password"] == hash_password(p.strip()):
                        st.session_state["logged_in"] = True
                        st.session_state["username"]  = u.strip()
                        load_data()
                        st.session_state["page"]         = "landing"
                        st.session_state["current_view"] = "home"
                        intended = st.session_state.pop("_intended_view", None)
                        if intended:
                            st.session_state["current_view"] = intended
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
                except Exception:
                    st.error("Database error. Please try again.")
            cl, cr = st.columns(2)
            with cl:
                if st.button("← Back", key="back_login"):
                    st.session_state["auth_view"] = "welcome"
                    st.session_state["page"]      = "landing"
                    st.rerun()
            with cr:
                if st.button("Forgot Password?", key="forgot_btn"):
                    st.session_state["auth_view"]   = "forgot_password"
                    st.session_state["forgot_step"] = "verify_email"
                    st.rerun()

        elif av == "register":
            st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Create Account</h3>", unsafe_allow_html=True)
            steps   = ["Email", "Verify", "Setup"]
            step_idx = {"input_email": 0, "verify_otp": 1, "set_credentials": 2}.get(st.session_state["reg_step"], 0)
            dots_html = ""
            for si, s_label in enumerate(steps):
                color  = "var(--accent)" if si <= step_idx else "var(--text-muted)"
                weight = "700" if si == step_idx else "400"
                dots_html += f"<span style='color:{color};font-weight:{weight};font-size:0.82rem;'>{s_label}</span>"
                if si < len(steps) - 1:
                    lc = "var(--accent)" if si < step_idx else "var(--border)"
                    dots_html += f"<span style='display:inline-block;width:30px;height:2px;background:{lc};vertical-align:middle;margin:0 8px;'></span>"
            st.markdown(f"<div style='text-align:center;margin-bottom:1.5rem;'>{dots_html}</div>", unsafe_allow_html=True)

            if st.session_state["reg_step"] == "input_email":
                with st.form("reg_email_form"):
                    ei   = st.text_input("Email Address", placeholder="name@gmail.com")
                    send = st.form_submit_button("Send Verification Code →", use_container_width=True)
                if send:
                    if not validate_email(ei.strip()):
                        st.error("Enter a valid email.")
                    else:
                        existing = [m["identity"] for m in st.session_state["user_db"].values()]
                        if ei.strip() in existing:
                            st.error("Account with this email already exists.")
                        else:
                            otp = str(random.randint(100000, 999999))
                            ok, err = send_otp_email(ei.strip(), otp)
                            if ok:
                                st.session_state.update({
                                    "generated_otp": otp, "otp_timestamp": datetime.datetime.now(),
                                    "temp_identity": ei.strip(), "reg_step": "verify_otp",
                                })
                                st.success(f"OTP sent to {ei.strip()}!")
                                st.rerun()
                            else:
                                st.error(f"Failed: {err}")
                if st.button("← Cancel"):
                    st.session_state["auth_view"] = "welcome"
                    st.session_state["page"]      = "landing"
                    st.rerun()

            elif st.session_state["reg_step"] == "verify_otp":
                st.info(f"📬 OTP sent to **{st.session_state['temp_identity']}**")
                if is_otp_expired():
                    st.error("⏰ OTP expired.")
                    if st.button("Resend OTP", use_container_width=True):
                        otp = str(random.randint(100000, 999999))
                        ok, _ = send_otp_email(st.session_state["temp_identity"], otp)
                        if ok:
                            st.session_state.update({"generated_otp": otp, "otp_timestamp": datetime.datetime.now()})
                            st.success("New OTP sent!")
                            st.rerun()
                else:
                    with st.form("otp_form"):
                        entered = st.text_input("6-Digit OTP", max_chars=6, placeholder="______")
                        verify  = st.form_submit_button("Verify →", use_container_width=True)
                    if verify:
                        if entered.strip() == st.session_state["generated_otp"]:
                            st.session_state["reg_step"] = "set_credentials"; st.rerun()
                        else:
                            st.error("Incorrect OTP.")
                    if st.button("← Back", key="back_otp"):
                        st.session_state["reg_step"] = "input_email"; st.rerun()

            elif st.session_state["reg_step"] == "set_credentials":
                st.success(f"✅ Email verified: {st.session_state['temp_identity']}")
                with st.form("cred_form"):
                    ru   = st.text_input("Choose a Username")
                    rp   = st.text_input("Choose a Password", type="password")
                    rc   = st.text_input("Confirm Password",  type="password")
                    done = st.form_submit_button("Create Account →", use_container_width=True)
                if done:
                    existing_emails = [m["identity"] for m in st.session_state["user_db"].values()]
                    if len(ru.strip()) < 3:      st.error("Username too short.")
                    elif ru.strip() in st.session_state["user_db"]: st.error("Username taken.")
                    elif st.session_state["temp_identity"] in existing_emails: st.error("Email already registered.")
                    elif rp != rc:               st.error("Passwords don't match.")
                    elif len(rp) < 4:            st.error("Password too short.")
                    else:
                        new_user = {"identity": st.session_state["temp_identity"], "password": hash_password(rp.strip())}
                        st.session_state["user_db"][ru.strip()] = new_user
                        try:
                            with get_conn() as conn:
                                conn.execute(
                                    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                                    (ru.strip(), new_user["identity"], new_user["password"]),
                                )
                        except Exception:
                            pass
                        st.session_state["logged_in"]    = True
                        st.session_state["username"]     = ru.strip()
                        load_data()
                        st.session_state["page"]         = "landing"
                        st.session_state["current_view"] = "home"
                        st.rerun()

        elif av == "forgot_password":
            st.markdown("<h3 style='font-weight:700;color:var(--text-primary);'>Reset Password</h3>", unsafe_allow_html=True)
            if st.session_state["forgot_step"] == "verify_email":
                with st.form("forgot_form"):
                    re_email = st.text_input("Registered Email")
                    lookup   = st.form_submit_button("Send Reset OTP →", use_container_width=True)
                if lookup:
                    found = next((u for u, m in st.session_state["user_db"].items() if m["identity"] == re_email.strip()), None)
                    if found:
                        otp = str(random.randint(100000, 999999))
                        ok, err = send_otp_email(re_email.strip(), otp)
                        if ok:
                            st.session_state.update({
                                "recovery_target_user": found, "generated_otp": otp,
                                "otp_timestamp": datetime.datetime.now(), "forgot_step": "verify_otp",
                            })
                            st.success("OTP sent!"); st.rerun()
                        else:
                            st.error(f"Failed: {err}")
                    else:
                        st.error("No account found.")
                if st.button("← Back", key="back_forgot"):
                    st.session_state["auth_view"] = "login"; st.rerun()

            elif st.session_state["forgot_step"] == "verify_otp":
                st.info("📬 OTP sent to your registered email.")
                if not is_otp_expired():
                    with st.form("forgot_otp_form"):
                        rotp = st.text_input("6-Digit OTP", max_chars=6)
                        vrfy = st.form_submit_button("Verify →", use_container_width=True)
                    if vrfy:
                        if rotp.strip() == st.session_state["generated_otp"]:
                            st.session_state["forgot_step"] = "reset_password"; st.rerun()
                        else:
                            st.error("Incorrect OTP.")
                else:
                    st.error("⏰ OTP expired.")

            elif st.session_state["forgot_step"] == "reset_password":
                with st.form("reset_form"):
                    np1  = st.text_input("New Password",     type="password")
                    np2  = st.text_input("Confirm Password", type="password")
                    save = st.form_submit_button("Update Password →", use_container_width=True)
                if save:
                    if np1 != np2:   st.error("Don't match.")
                    elif len(np1) < 4: st.error("Too short.")
                    else:
                        target   = st.session_state["recovery_target_user"]
                        new_hash = hash_password(np1.strip())
                        st.session_state["user_db"][target]["password"] = new_hash
                        try:
                            with get_conn() as conn:
                                conn.execute("UPDATE users SET password=? WHERE username=?", (new_hash, target))
                        except Exception:
                            pass
                        st.success("Password updated! Sign in now.")
                        st.session_state["auth_view"] = "login"; st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# CSS DESIGN SYSTEM
# ============================================================

def inject_css(theme="light"):
    if theme == "light":
        theme_vars = """
        :root {
            --bg-primary:    #F8FAFC;
            --bg-secondary:  #F1F5F9;
            --bg-card:       #FFFFFF;
            --text-primary:  #0F172A;
            --text-secondary:#475569;
            --text-muted:    #94A3B8;
            --border:        #E2E8F0;
            --accent:        #4F46E5;
            --accent-hover:  #4338CA;
            --accent-light:  rgba(79,70,229,0.06);
            --accent-gradient: linear-gradient(135deg,#4F46E5,#7C3AED);
            --shadow-sm:  0 1px 2px rgba(0,0,0,0.04);
            --shadow-md:  0 4px 12px rgba(0,0,0,0.06);
            --shadow-lg:  0 12px 32px rgba(0,0,0,0.08);
            --radius-sm:  8px;
            --radius-md:  12px;
            --radius-lg:  16px;
            --sidebar-bg: #FFFFFF;
            --sidebar-border: #E2E8F0;
            --navbar-bg:  rgba(248,250,252,0.88);
        }"""
    else:
        theme_vars = """
        :root {
            --bg-primary:    #0B1120;
            --bg-secondary:  #1E293B;
            --bg-card:       #151D2E;
            --text-primary:  #F1F5F9;
            --text-secondary:#94A3B8;
            --text-muted:    #64748B;
            --border:        rgba(255,255,255,0.08);
            --accent:        #818CF8;
            --accent-hover:  #6366F1;
            --accent-light:  rgba(129,140,248,0.1);
            --accent-gradient: linear-gradient(135deg,#6366F1,#8B5CF6);
            --shadow-sm:  0 1px 2px rgba(0,0,0,0.2);
            --shadow-md:  0 4px 12px rgba(0,0,0,0.3);
            --shadow-lg:  0 12px 32px rgba(0,0,0,0.4);
            --radius-sm:  8px;
            --radius-md:  12px;
            --radius-lg:  16px;
            --sidebar-bg: #111827;
            --sidebar-border: rgba(255,255,255,0.06);
            --navbar-bg:  rgba(11,17,32,0.88);
        }"""

    st.markdown(f"<style>{theme_vars}</style>", unsafe_allow_html=True)

    # Sidebar visibility control
    if not st.session_state.get("sidebar_open", True):
        st.markdown("""<style>
        section[data-testid="stSidebar"] {
            transform: translateX(-110%) !important;
            transition: transform 0.3s ease !important;
            position: fixed !important;
            z-index: 999 !important;
        }
        </style>""", unsafe_allow_html=True)
    else:
        st.markdown("""<style>
        section[data-testid="stSidebar"] {
            transform: translateX(0) !important;
            transition: transform 0.3s ease !important;
        }
        </style>""", unsafe_allow_html=True)

    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

/* ── Reset Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="collapsedControl"],
.viewerBadge_container__1QSob { display:none !important; }

/* ── Global ── */
* { font-family: 'Inter', -apple-system, sans-serif !important; }
.stApp { background: var(--bg-primary) !important; color: var(--text-primary) !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--sidebar-bg) !important;
    border-right: 1px solid var(--sidebar-border) !important;
    width: 260px !important;
    min-width: 260px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding: 1.2rem 1rem !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 100vh !important;
}

/* Sidebar logo */
.sb-logo {
    font-size: 1.2rem; font-weight: 800;
    color: var(--text-primary);
    display: flex; align-items: center; gap: 6px;
    margin-bottom: 2px;
}
.sb-logo span { background: var(--accent-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sb-tagline { font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0; }

/* Sidebar divider */
.sb-divider {
    border: none; border-top: 1px solid var(--border);
    margin: 0.8rem 0;
}

/* Sidebar profile */
.sb-profile {
    display: flex; align-items: center; gap: 10px; padding: 8px 0;
}
.sb-profile-compact {
    display: flex; align-items: center; gap: 8px; padding: 6px 0; margin-bottom: 6px;
}
.sb-avatar {
    width: 38px; height: 38px; border-radius: 50%;
    background: var(--accent-gradient);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 800; flex-shrink: 0;
}
.sb-avatar-sm {
    width: 28px; height: 28px; border-radius: 50%;
    background: var(--accent-gradient);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 800; flex-shrink: 0;
}
.sb-avatar-lg {
    width: 56px; height: 56px; border-radius: 50%;
    background: var(--accent-gradient);
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; font-weight: 800; flex-shrink: 0;
}
.sb-uname { font-size: 0.88rem; font-weight: 700; color: var(--text-primary); }
.sb-email { font-size: 0.75rem; color: var(--text-muted); }

/* Sidebar section label */
.sb-section-label {
    font-size: 0.7rem; font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 0 0 6px 0;
    padding: 0;
}

/* Sidebar buttons */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    color: var(--text-secondary) !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    height: 38px !important;
    border-radius: var(--radius-sm) !important;
    padding: 0 10px !important;
    margin-bottom: 2px !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--accent-light) !important;
    color: var(--text-primary) !important;
}

/* Active nav item */
.nav-item-active {
    background: var(--accent-light);
    color: var(--accent) !important;
    font-weight: 700;
    font-size: 0.88rem;
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    border-left: 3px solid var(--accent);
    margin-bottom: 2px;
}

/* History panel inside sidebar */
.sb-empty {
    text-align: center; color: var(--text-muted);
    font-size: 0.8rem; padding: 1.5rem 0.5rem;
}

/* Sidebar spacer (pushes logout to bottom) */
.sb-spacer { flex-grow: 1 !important; }

/* Pinned logout styling */
section[data-testid="stSidebar"] button[kind="secondary"][key*="logout"],
section[data-testid="stSidebar"] .stButton > button[data-testid*="logout"] {
    color: #F87171 !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] .stButton > button[data-testid*="logout"]:hover {
    background: rgba(239,68,68,0.1) !important;
    color: #F87171 !important;
}

/* History list items in sidebar */
section[data-testid="stSidebar"] .stButton > button[key^="sel_"],
section[data-testid="stSidebar"] .stButton > button[key^="sib_back"] {
    font-size: 0.82rem !important; height: 32px !important;
}
section[data-testid="stSidebar"] .stButton > button[key^="dots_"] {
    font-size: 1rem !important; height: 32px !important;
    padding: 0 4px !important; width: 28px !important;
}
section[data-testid="stSidebar"] .stButton > button[key^="new_"] {
    color: var(--accent) !important;
    border: 1px dashed var(--accent) !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    margin-bottom: 8px !important;
}
section[data-testid="stSidebar"] .stButton > button[key^="new_"]:hover {
    background: var(--accent) !important;
    color: #fff !important;
    border-style: solid !important;
}
section[data-testid="stSidebar"] .stButton > button[key^="ren_"],
section[data-testid="stSidebar"] .stButton > button[key^="del_"] {
    font-size: 0.75rem !important; height: 26px !important;
}

/* ── Navbar ── */
.navbar-divider {
    border: none; border-top: 1px solid var(--border);
    margin: 0 0 1.2rem 0;
}

/* Logo button in navbar */
.stButton > button[key="nav_logo"] {
    background: transparent !important;
    border: none !important;
    font-weight: 800 !important;
    font-size: 1.1rem !important;
    color: var(--text-primary) !important;
    padding: 0 !important;
    box-shadow: none !important;
    height: auto !important;
}
.stButton > button[key="nav_logo"]:hover {
    color: var(--accent) !important;
    background: transparent !important;
}

/* Toggle button */
.stButton > button[key="nav_toggle"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    width: 38px !important; height: 38px !important;
    border-radius: var(--radius-sm) !important;
    font-size: 1rem !important; padding: 0 !important;
    box-shadow: none !important;
}
.stButton > button[key="nav_toggle"]:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Global buttons ── */
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
    color: #fff !important; border: none !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(79,70,229,0.35) !important;
}

/* Form submit */
[data-testid="stFormSubmitButton"] button {
    background: var(--accent-gradient) !important;
    color: #fff !important; border: none !important;
    border-radius: var(--radius-md) !important;
    height: 42px !important; font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.2) !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(79,70,229,0.3) !important;
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
[data-testid="stForm"] { border: none !important; background: transparent !important; padding: 0 !important; }
.stAlert { border-radius: var(--radius-sm) !important; }

/* ── Typography ── */
.view-title {
    font-weight: 800; font-size: 1.6rem;
    color: var(--text-primary); margin: 0 0 4px 0; letter-spacing: -0.5px;
}
.view-subtitle {
    color: var(--text-muted); font-size: 0.92rem; margin: 0 0 1.5rem 0;
}
.section-label {
    font-weight: 700; font-size: 0.78rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 10px 0;
}
.card-label {
    font-weight: 700; font-size: 0.75rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 10px 0;
}

/* ── Cards ── */
.content-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.5rem; box-shadow: var(--shadow-sm);
    margin-bottom: 0;
    animation: fadeIn 0.3s ease;
}
.auth-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 2rem; box-shadow: var(--shadow-md);
}

/* Stat card */
.stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.1rem; text-align: center;
    box-shadow: var(--shadow-sm);
    transition: transform 0.2s, box-shadow 0.2s;
    animation: fadeIn 0.3s ease;
}
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stat-icon { font-size: 1.1rem; margin-bottom: 4px; }
.stat-num  { font-size: 1.7rem; font-weight: 800; }
.stat-label{ font-size: 0.72rem; color: var(--text-muted); margin-top: 2px; }

/* Feature card */
.feature-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.6rem; height: 180px;
    box-shadow: var(--shadow-sm);
    transition: all 0.25s cubic-bezier(0.16,1,0.3,1);
    animation: fadeIn 0.3s ease;
}
.feature-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); border-color: var(--accent); }
.fc-icon  { font-size: 1.8rem; margin-bottom: 0.5rem; }
.fc-title { font-weight: 700; font-size: 1rem; color: var(--text-primary); margin-bottom: 0.3rem; }
.fc-desc  { font-size: 0.82rem; color: var(--text-muted); line-height: 1.45; }

/* ── Hero (logged out) ── */
.hero-section {
    text-align: center; max-width: 720px;
    margin: 1rem auto 2.5rem auto; padding: 0 1rem;
}
.hero-badge {
    display: inline-block;
    background: var(--accent-light);
    color: var(--accent);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.78rem; font-weight: 600;
    letter-spacing: 0.04em;
    margin-bottom: 1rem;
}
.hero-title {
    font-size: 3rem; font-weight: 900;
    background: var(--accent-gradient);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.15; margin-bottom: 1rem; letter-spacing: -2px;
}
.hero-sub {
    font-size: 1.1rem; color: var(--text-muted);
    line-height: 1.6; margin: 0 auto; max-width: 540px;
}

/* ── Home welcome ── */
.home-welcome { margin-bottom: 1.5rem; }
.home-greeting {
    font-size: 1.8rem; font-weight: 800;
    color: var(--text-primary); margin: 0 0 4px 0; letter-spacing: -0.5px;
}
.home-subtext { color: var(--text-muted); font-size: 0.95rem; margin: 0 0 1.5rem 0; }
.section-gap { margin-top: 2rem; }

/* Recent activity item */
.recent-item {
    padding: 8px 12px;
    background: var(--bg-secondary);
    border-radius: var(--radius-sm);
    font-size: 0.88rem; color: var(--text-secondary);
    display: flex; align-items: center; gap: 8px;
}

/* ── Activity / Timeline ── */
.timeline-dot {
    width: 10px; height: 10px; border-radius: 50%;
    margin-top: 16px;
}
.timeline-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.85rem 1.1rem;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.2s;
}
.timeline-card:hover { box-shadow: var(--shadow-md); }
.timeline-header {
    display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
}
.timeline-badge {
    font-size: 0.7rem; font-weight: 700;
    padding: 2px 8px; border-radius: 6px;
    text-transform: uppercase; letter-spacing: 0.03em;
}
.timeline-date {
    font-size: 0.75rem; color: var(--text-muted);
}
.timeline-label {
    font-size: 0.9rem; color: var(--text-primary); font-weight: 500;
}

/* ── Chat ── */
.chat-empty { text-align: center; padding: 3rem 2rem; }
.chat-empty-title {
    font-weight: 800; color: var(--text-primary);
    font-size: 1.5rem; margin: 0 0 0.5rem 0;
}
.chat-empty-sub { color: var(--text-muted); font-size: 0.95rem; margin: 0; }

.chat-row { display: flex; margin-bottom: 8px; align-items: flex-start; gap: 8px; }
.user-row  { justify-content: flex-end; }
.bot-row   { justify-content: flex-start; }
.bot-avatar {
    width: 30px; height: 30px; border-radius: 50%;
    background: var(--bg-secondary); border: 1px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; flex-shrink: 0; margin-top: 4px;
}
.chat-msg {
    padding: 0.8rem 1.1rem; border-radius: 16px;
    font-size: 0.92rem; line-height: 1.6; max-width: 75%;
    word-wrap: break-word; overflow-wrap: break-word;
}
.user-bubble {
    background: var(--accent-gradient) !important; color: #fff !important;
    border-bottom-right-radius: 4px !important;
}
.bot-bubble {
    background: var(--bg-card) !important; color: var(--text-primary) !important;
    border: 1px solid var(--border) !important; border-bottom-left-radius: 4px !important;
}
.bot-bubble p      { color: var(--text-primary) !important; margin: 0.3rem 0 !important; }
.bot-bubble strong { color: var(--accent) !important; font-weight: 700 !important; }
.bot-bubble code   { background: var(--bg-secondary) !important; color: #10B981 !important; padding: 1px 5px !important; border-radius: 4px !important; font-size: 0.88em !important; }
.bot-bubble pre    { background: var(--bg-secondary) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; padding: 0.6rem 1rem !important; overflow-x: auto !important; }
.bot-bubble pre code { background: transparent !important; padding: 0 !important; }
.bot-bubble blockquote { border-left: 3px solid var(--accent) !important; padding: 0.4rem 0.8rem !important; border-radius: 0 6px 6px 0 !important; }

/* Suggestion chips */
.stButton > button[key^="suggest_"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important; font-weight: 500 !important;
    height: auto !important; padding: 10px 14px !important;
    text-align: left !important; justify-content: flex-start !important;
    border-radius: var(--radius-md) !important; line-height: 1.4 !important;
}
.stButton > button[key^="suggest_"]:hover {
    border-color: var(--accent) !important;
    background: var(--accent-light) !important;
    color: var(--accent) !important;
}

/* ── Table ── */
.th { padding: 10px 12px; text-align: left; color: var(--text-muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.td { padding: 10px 12px; color: var(--text-primary); font-size: 0.88rem; }
.badge-weak { background: #F59E0B; color: #000; font-size: 0.65rem; padding: 1px 6px; border-radius: 4px; font-weight: 700; margin-left: 6px; }

/* ── Empty state ── */
.empty-state {
    text-align: center; padding: 4rem 2rem;
    color: var(--text-muted);
}

/* ── Popover styling ── */
div[data-testid="stPopover"] div[data-testid="stVerticalBlock"] .stButton > button {
    background: transparent !important;
    border: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    height: 36px !important;
    border-radius: 6px !important;
}
div[data-testid="stPopover"] div[data-testid="stVerticalBlock"] .stButton > button:hover {
    background: var(--accent-light) !important;
    color: var(--accent) !important;
}

/* ── Animations ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Responsive ── */
@media (max-width: 768px) {
    .hero-title { font-size: 2rem; }
    .feature-card { height: auto; }
    .chat-msg { max-width: 90%; }
    .stat-num { font-size: 1.3rem; }
}

</style>""", unsafe_allow_html=True)


# ============================================================
# APP SHELL
# ============================================================

def render_main_content():
    """Routes to the correct view."""
    # Auth routing
    if not st.session_state["logged_in"] and st.session_state["page"] in ("login", "register"):
        render_login_page()
        return

    protected = {"chat", "summary", "planner", "analytics", "activity", "history", "profile", "settings"}
    view = st.session_state["current_view"]

    if view in protected and not st.session_state["logged_in"]:
        render_login_required_view()
        return

    if   view == "home":      render_home_view()
    elif view == "chat":      render_chat_view()
    elif view == "summary":   render_summary_view()
    elif view == "planner":   render_planner_view()
    elif view == "analytics": render_analytics_view()
    elif view == "activity":  render_activity_view()
    elif view == "profile":   render_profile_view()
    elif view == "settings":  render_settings_view()
    else:
        render_home_view()


def render_app_shell():
    """Top-level shell: sidebar + navbar + content."""
    # Render sidebar (always, for all users — hidden via CSS when collapsed)
    with st.sidebar:
        render_sidebar()

    # Navbar
    render_navbar()

    # Main content
    render_main_content()


# ============================================================
# CSS INJECTION + ENTRY POINT
# ============================================================

st.set_page_config(page_title="StudyPilot", page_icon="✈️", layout="wide")

init_db()

defaults = {
    "theme": "light",
    "page": "landing",
    "logged_in": False, "username": "", "message_history": {},
    "current_view": "home", "auth_view": "welcome",
    "reg_step": "input_email", "forgot_step": "verify_email",
    "generated_otp": None, "otp_timestamp": None,
    "temp_identity": "", "recovery_target_user": "",
    "editing_item_id": "", "rename_feature_target": "",
    "active_menu_item_id": "", "active_bubble_menu_id": "",
    "show_copy_summary": False, "user_db": {},
    "all_chats": {}, "active_chat_id": "",
    "all_summaries": {}, "active_summary_id": "",
    "all_plans": {}, "active_planner_id": "",
    "nav_history_stack": [],
    "sidebar_open": True,
    "activity_filter": "All",
    "_intended_view": None,
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
