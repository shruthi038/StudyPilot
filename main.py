import streamlit as st
import pandas as pd
import numpy as np
import nltk
import datetime
import hashlib
import random
import re
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from transformers import pipeline

load_dotenv()
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

def send_otp_email(recipient_email, otp_code):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "StudyPilot — Your Verification Code"
        msg["From"] = f"StudyPilot <{GMAIL_ADDRESS}>"
        msg["To"] = recipient_email
        html_body = f"""<html><body style="margin:0;padding:0;background:#0B0F19;font-family:'Segoe UI',sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#0B0F19;padding:40px 0;">
                <tr><td align="center">
                    <table width="480" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:16px;overflow:hidden;border:1px solid #1F2937;">
                        <tr><td style="background:linear-gradient(135deg,#1D4ED8,#2563EB);padding:32px;text-align:center;">
                            <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;">✈️ StudyPilot</h1>
                            <p style="margin:6px 0 0;color:#BFDBFE;font-size:13px;">Your AI-Powered Learning Assistant</p>
                        </td></tr>
                        <tr><td style="padding:36px 40px;">
                            <p style="color:#9CA3AF;font-size:14px;margin:0 0 8px;">Your verification code is:</p>
                            <div style="background:#0B0F19;border:1px solid #374151;border-radius:12px;padding:24px;text-align:center;margin:16px 0;">
                                <span style="font-size:42px;font-weight:900;color:#60A5FA;letter-spacing:10px;">{otp_code}</span>
                            </div>
                            <p style="color:#6B7280;font-size:13px;margin:16px 0 0;">Expires in <b style="color:#F59E0B;">10 minutes</b>. Do not share it.</p>
                        </td></tr>
                        <tr><td style="padding:20px 40px;border-top:1px solid #1F2937;">
                            <p style="color:#4B5563;font-size:12px;margin:0;text-align:center;">If you didn't request this, ignore this email.</p>
                        </td></tr>
                    </table>
                </td></tr>
            </table>
        </body></html>"""
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))

def is_otp_expired():
    if not st.session_state.get('otp_timestamp'):
        return True
    return (datetime.datetime.now() - st.session_state['otp_timestamp']).seconds > 600

@st.cache_resource
def load_resources():
    nltk.download("vader_lexicon", quiet=True)
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    sia = SentimentIntensityAnalyzer()
    summarizer = pipeline("summarization", model="t5-small")
    return sia, summarizer

sia, summarizer = load_resources()

@st.cache_data
def prepare_data():
    try:
        df = pd.read_csv("chatbot_data.csv")
    except:
        data = {
            "question": ["what is python","what is ml","what is dsa","what is a list"],
            "answer": [
                "Python is a high-level interpreted programming language known for its simple readable syntax.",
                "Machine Learning is a field of AI that enables systems to learn from data automatically.",
                "DSA stands for Data Structures and Algorithms — the foundation of efficient programming.",
                "A list is an ordered mutable collection. Example: my_list = [1 2 3]"
            ]
        }
        df = pd.DataFrame(data)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(df["question"].values.astype("U"))
    return df, vectorizer, tfidf_matrix

df, vectorizer, tfidf_matrix = prepare_data()

def get_smart_response(user_query):
    score = sia.polarity_scores(user_query)
    user_vec = vectorizer.transform([user_query])
    similarity = cosine_similarity(user_vec, tfidf_matrix)
    idx = similarity.argmax()
    if similarity[0][idx] < 0.2:
        return "I'm not sure about that. Try asking about Python concepts like functions classes lists recursion sorting algorithms etc.", score
    return df.iloc[idx]["answer"], score

MOTIVATIONAL_BANK = {
    "positive": [
        "Incredible energy! You are absolutely paving your way to a high-paying role right now.",
        "Your focus is top-tier today! Keep riding this momentum.",
        "Logic and momentum are on your side. Let's conquer these code structures!",
        "Brilliant mindset. Consistent efforts like this pay off massively in technical interviews."
    ],
    "neutral": [
        "Clear steady execution wins the race. Let's make this session count.",
        "One step at a time one line of code at a time. Consistency is key.",
        "Progress is built on quiet focus days. You're doing the hard work right now.",
        "Lock in your focus. Building mastery takes steady rhythm."
    ],
    "negative": [
        "Take a deep breath. Even small steps on exhausting days count toward your grand goals.",
        "Be gentle with your mind right now. Learning hard concepts when tired is true dedication.",
        "Burnout is the enemy of progress. We adapted this timeline specifically to support you.",
        "You don't have to be perfect — just try. Let's break this down into micro-wins."
    ]
}

def get_motivational_message(sentiment_score):
    cat = "positive" if sentiment_score >= 0.1 else ("negative" if sentiment_score <= -0.1 else "neutral")
    opts = MOTIVATIONAL_BANK[cat]
    avail = [m for m in opts if st.session_state['message_history'].get(m, 0) < 2] or opts
    chosen = random.choice(avail)
    st.session_state['message_history'][chosen] = st.session_state['message_history'].get(chosen, 0) + 1
    return chosen

def smart_summarize(text, target_words):
    if len(text.split()) <= target_words:
        return text.strip()
    max_tok = min(int(target_words * 1.4), 512)
    min_tok = max(10, int(target_words * 0.7))
    raw = summarizer(text, max_length=max_tok, min_length=min_tok, do_sample=False)
    summary = raw[0]['summary_text']
    words = summary.split()
    if len(words) > target_words:
        words = words[:target_words]
        summary = " ".join(words)
        for p in ['.','!','?']:
            last = summary.rfind(p)
            if last > len(summary) * 0.6:
                summary = summary[:last+1]; break
    return summary.strip()

def apply_summary_formatting(raw_text, fmt):
    today = datetime.date.today().strftime("%B %d, %Y")
    sentences = nltk.sent_tokenize(raw_text)
    wc = len(raw_text.split())
    out = f"### Summary ({fmt}) — ~{wc} words\n\n"
    if fmt == "Bullet Points":
        out += "#### Core Takeaways\n"
        for s in sentences:
            if s.strip(): out += f"- {s.strip()}\n"
    elif fmt == "Essay":
        out += f"**Introduction:**\n{raw_text}\n\n"
        if len(sentences) > 1:
            out += "**Core Discussion:**\n" + " ".join(sentences[1:]) + "\n\n"
        out += "**Conclusion:** Consistent notes analysis builds better concept recall."
    elif fmt == "Letter":
        out += f"**Date:** {today}  \n**To:** Study Group Peers  \n\nDear Student,  \n\n{raw_text}\n\nBest regards,  \n*{st.session_state['username']}*"
    elif fmt == "Email":
        out += f"**Subject:** Lecture Summary — {today}  \n---  \nHi Team,  \n\n> {raw_text}\n\nThanks,  \n**{st.session_state['username']}**"
    else:
        out += raw_text
    return out

# ---------------------- SIDEBAR ----------------------
def render_sidebar_section(feature_key, friendly_name):
    if feature_key == "chat":
        history_dict = st.session_state['all_chats']
        active_id = st.session_state['active_chat_id']
    elif feature_key == "summary":
        history_dict = st.session_state['all_summaries']
        active_id = st.session_state['active_summary_id']
    else:
        history_dict = st.session_state['all_plans']
        active_id = st.session_state['active_planner_id']

    st.markdown(f"<p style='font-weight:700;font-size:0.85rem;color:#64748B;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 8px 0;'>{friendly_name} History</p>", unsafe_allow_html=True)

    if st.button(f"＋  New {friendly_name}", use_container_width=True, key=f"new_{feature_key}"):
        nid = f"{feature_key}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if feature_key == "chat":
            st.session_state['all_chats'][nid] = []
            st.session_state['active_chat_id'] = nid
        elif feature_key == "summary":
            st.session_state['all_summaries'][nid] = {"text":"","summary":"","word_count":80,"format_style":"Plain Text","title":"Untitled Summary"}
            st.session_state['active_summary_id'] = nid
        else:
            st.session_state['all_plans'][nid] = {"subjects":"","weak":"","mood":"","schedule":[],"title":"Untitled Plan"}
            st.session_state['active_planner_id'] = nid
        st.rerun()

    st.write("")

    if not history_dict:
        st.caption("No history yet.")
        return

    for item_id in list(history_dict.keys()):
        if feature_key == "chat":
            msgs = history_dict[item_id]
            label = msgs[0]['text'][:22]+"..." if msgs else "New Chat"
        else:
            label = history_dict[item_id].get('title','Untitled')

        is_active = item_id == active_id
        col_sel, col_dot = st.columns([8.5, 1.5])

        with col_sel:
            btn_lbl = f"▸ {label}" if is_active else label
            if st.button(btn_lbl, key=f"sel_{item_id}_{feature_key}", use_container_width=True):
                if feature_key == "chat": st.session_state['active_chat_id'] = item_id
                elif feature_key == "summary": st.session_state['active_summary_id'] = item_id
                else: st.session_state['active_planner_id'] = item_id
                st.rerun()

        with col_dot:
            if st.button("⋮", key=f"dots_{item_id}_{feature_key}", use_container_width=True):
                cur = st.session_state.get('active_menu_item_id',"")
                st.session_state['active_menu_item_id'] = item_id if cur != item_id else ""
                st.rerun()

        if st.session_state.get('active_menu_item_id',"") == item_id:
            st.markdown("""<div style='background:#1A2234;border:1px solid #2D3748;border-radius:12px;
                padding:6px 6px;margin:2px 0 8px 0;box-shadow:0 8px 24px rgba(0,0,0,0.6);'>""", unsafe_allow_html=True)
            if st.button("↗  Share", key=f"share_{item_id}_{feature_key}", use_container_width=True):
                st.toast("Link copied!"); st.session_state['active_menu_item_id'] = ""; st.rerun()
            if st.button("✏️  Rename", key=f"ren_{item_id}_{feature_key}", use_container_width=True):
                st.session_state['editing_item_id'] = item_id
                st.session_state['rename_feature_target'] = feature_key
                st.session_state['active_menu_item_id'] = ""; st.rerun()
            st.markdown("<hr style='margin:4px 2px;border:none;border-top:1px solid #2D3748;'>", unsafe_allow_html=True)
            if st.button("🗑️  Delete", key=f"del_{item_id}_{feature_key}", use_container_width=True):
                del history_dict[item_id]
                st.session_state['active_menu_item_id'] = ""
                if active_id == item_id:
                    remaining = list(history_dict.keys())
                    fallback = remaining[0] if remaining else ""
                    if feature_key == "chat": st.session_state['active_chat_id'] = fallback
                    elif feature_key == "summary": st.session_state['active_summary_id'] = fallback
                    else: st.session_state['active_planner_id'] = fallback
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    eid = st.session_state.get('editing_item_id',"")
    if eid in history_dict and st.session_state.get('rename_feature_target') == feature_key:
        st.write("---")
        with st.form(f"rename_form_{feature_key}"):
            new_title = st.text_input("New name", placeholder="Enter title...", label_visibility="collapsed")
            if st.form_submit_button("Save →", use_container_width=True):
                if new_title.strip():
                    if feature_key == "chat":
                        msgs = st.session_state['all_chats'][eid]
                        if not msgs: msgs.append({"role":"assistant","text":new_title.strip()})
                        else: msgs[0]['text'] = new_title.strip()
                    else:
                        history_dict[eid]['title'] = new_title.strip()
                    st.session_state['editing_item_id'] = ""; st.rerun()

# ---------------------- MAIN APP ----------------------
def render_main_app():
    with st.sidebar:
        if st.button(f"🧑‍🎓  {st.session_state['username']}", use_container_width=True, key="profile_btn"):
            st.session_state['show_profile_tray'] = not st.session_state.get('show_profile_tray', False)
            st.rerun()

        if st.session_state.get('show_profile_tray', False):
            uid = st.session_state['username']
            email = st.session_state['user_db'].get(uid, {}).get('identity', 'N/A')
            st.markdown(f"""<div style='background:#0D1117;border:1px solid #1E2533;border-radius:10px;
                padding:10px 14px;margin:4px 0 8px 0;font-size:0.88rem;line-height:2;'>
                <span style='color:#64748B;'>Username</span><br>
                <span style='color:#F1F5F9;font-weight:600;'>{uid}</span><br>
                <span style='color:#64748B;'>Email</span><br>
                <span style='color:#F1F5F9;font-weight:600;'>{email}</span>
            </div>""", unsafe_allow_html=True)

        st.write("---")

        view = st.session_state['current_view']
        if view == "chat": render_sidebar_section("chat", "Chat")
        elif view == "summary": render_sidebar_section("summary", "Summary")
        elif view == "planner": render_sidebar_section("planner", "Planner")
        else: st.caption("Select a module above to begin.")

        st.write("")
        if st.button("🚪  Log Out", use_container_width=True, key="logout_btn"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.session_state['auth_view'] = "welcome"
            st.session_state['current_view'] = "welcome_hub"
            st.rerun()

    # NAVBAR
    st.markdown("<div class='navbar-wrapper'>", unsafe_allow_html=True)
    n1,n2,n3,n4 = st.columns([1,1.2,1.2,1.2])
    with n1:
        if st.button("🏠 Home", key="nav_home", use_container_width=True):
            st.session_state['current_view'] = "welcome_hub"; st.rerun()
    with n2:
        if st.button("💬 Ask Anything", key="nav_chat", use_container_width=True):
            st.session_state['current_view'] = "chat"; st.rerun()
    with n3:
        if st.button("📝 Summarize", key="nav_summary", use_container_width=True):
            st.session_state['current_view'] = "summary"; st.rerun()
    with n4:
        if st.button("📅 Planner", key="nav_planner", use_container_width=True):
            st.session_state['current_view'] = "planner"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    tab_pos = {"welcome_hub":("22%","0%"),"chat":("25%","24%"),"summary":("25%","50%"),"planner":("25%","75%")}
    w,ml = tab_pos.get(st.session_state['current_view'],("22%","0%"))
    st.markdown(f"<div style='height:3px;background:#3B82F6;width:{w};margin-left:{ml};margin-bottom:2rem;border-radius:2px;'></div>", unsafe_allow_html=True)

    # HOME
    if st.session_state['current_view'] == "welcome_hub":
        st.markdown(f"<h2 style='margin-bottom:4px;'>Welcome back, {st.session_state['username']}! 👋</h2>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:1.1rem;color:#64748B;margin-top:0;'>Ready to fly through your studies today?</p>", unsafe_allow_html=True)
        st.write("---")
        st.markdown("""
        <div style='display:flex;flex-direction:column;gap:12px;'>
            <div style='background:#0D1117;border:1px solid #1E2533;border-radius:12px;padding:1rem 1.25rem;'>
                <span style='color:#60A5FA;font-weight:700;'>💬 Ask Anything</span>
                <p style='color:#64748B;font-size:0.88rem;margin:4px 0 0;'>Ask any Python ML or DSA question and get instant answers.</p>
            </div>
            <div style='background:#0D1117;border:1px solid #1E2533;border-radius:12px;padding:1rem 1.25rem;'>
                <span style='color:#34D399;font-weight:700;'>📝 Summarize Notes</span>
                <p style='color:#64748B;font-size:0.88rem;margin:4px 0 0;'>Paste lecture notes and get a clean summary in your preferred format.</p>
            </div>
            <div style='background:#0D1117;border:1px solid #1E2533;border-radius:12px;padding:1rem 1.25rem;'>
                <span style='color:#F59E0B;font-weight:700;'>📅 Study Planner</span>
                <p style='color:#64748B;font-size:0.88rem;margin:4px 0 0;'>Generate an adaptive Pomodoro schedule based on your mood and subjects.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # CHATBOT
    elif st.session_state['current_view'] == "chat":
        st.markdown("### 💬 Ask your Technical Questions")
        if not st.session_state['all_chats']:
            st.session_state['all_chats']["chat_default"] = []
            st.session_state['active_chat_id'] = "chat_default"
        elif not st.session_state['active_chat_id']:
            st.session_state['active_chat_id'] = list(st.session_state['all_chats'].keys())[0]

        active_chat = st.session_state['all_chats'].get(st.session_state['active_chat_id'], [])

        for idx, msg in enumerate(active_chat):
            msg_id = f"msg_{st.session_state['active_chat_id']}_{idx}"
            if msg['role'] == "user":
                _, cb, cd = st.columns([3.5, 6, 0.5])
                with cb: st.markdown(f"<div class='chat-msg user-bubble'>{msg['text']}</div>", unsafe_allow_html=True)
                with cd:
                    if st.button("⋮", key=f"dots_chat_{msg_id}"):
                        st.session_state['active_bubble_menu_id'] = msg_id if st.session_state.get('active_bubble_menu_id') != msg_id else ""
                        st.rerun()
            else:
                cb, cd, _ = st.columns([6, 0.5, 3.5])
                with cb: st.markdown(f"<div class='chat-msg bot-bubble'>{msg['text']}</div>", unsafe_allow_html=True)
                with cd:
                    if st.button("⋮", key=f"dots_chat_{msg_id}"):
                        st.session_state['active_bubble_menu_id'] = msg_id if st.session_state.get('active_bubble_menu_id') != msg_id else ""
                        st.rerun()

            if st.session_state.get('active_bubble_menu_id') == msg_id:
                _, mc, _ = st.columns([4, 2.5, 3.5])
                with mc:
                    st.markdown("""<div style='background:#1A2234;border:1px solid #2D3748;border-radius:12px;
                        padding:6px;box-shadow:0 8px 24px rgba(0,0,0,0.6);'>""", unsafe_allow_html=True)
                    if st.button("📋  Copy", key=f"cp_{msg_id}", use_container_width=True):
                        st.toast("Copied!"); st.code(msg['text'], language="text")
                        st.session_state['active_bubble_menu_id'] = ""; st.rerun()
                    if st.button("↗  Share", key=f"sh_{msg_id}", use_container_width=True):
                        st.toast("Link copied!")
                        st.session_state['active_bubble_menu_id'] = ""; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        with st.form("chat_form", clear_on_submit=True):
            chat_input = st.text_input("", placeholder="e.g. What is recursion in Python?", label_visibility="collapsed")
            send = st.form_submit_button("Send →", use_container_width=True)

        if send and chat_input.strip():
            ans, sentiment = get_smart_response(chat_input)
            if sentiment['compound'] >= 0.05: st.toast("Positive vibes! 😊")
            elif sentiment['compound'] <= -0.05: st.toast("You seem stressed. Take it easy! 💙")
            active_chat.append({"role":"user","text":chat_input})
            active_chat.append({"role":"assistant","text":ans})
            st.session_state['all_chats'][st.session_state['active_chat_id']] = active_chat
            st.rerun()

    # SUMMARIZER
    elif st.session_state['current_view'] == "summary":
        st.markdown("### 📝 Notes Summarizer")
        if not st.session_state['all_summaries']:
            st.session_state['all_summaries']["summary_default"] = {"text":"","summary":"","word_count":80,"format_style":"Plain Text","title":"Untitled Summary"}
            st.session_state['active_summary_id'] = "summary_default"
        elif not st.session_state['active_summary_id']:
            st.session_state['active_summary_id'] = list(st.session_state['all_summaries'].keys())[0]

        node = st.session_state['all_summaries'].get(st.session_state['active_summary_id'])
        raw_text = st.text_area("", value=node['text'], height=220, placeholder="Paste your lecture notes here...", label_visibility="collapsed")
        if raw_text.strip():
            st.caption(f"📄 Input: {len(raw_text.split())} words")

        cc, cf = st.columns(2)
        with cc:
            target_words = st.number_input("Target word count:", min_value=10, max_value=500, value=int(node.get('word_count',80)), step=10)
        with cf:
            fmt = st.selectbox("Output format:", ["Plain Text","Bullet Points","Essay","Letter","Email"],
                index=["Plain Text","Bullet Points","Essay","Letter","Email"].index(node.get('format_style',"Plain Text")))

        node['text'] = raw_text; node['word_count'] = target_words; node['format_style'] = fmt

        if st.button("✨  Generate Summary", use_container_width=True, key="gen_sum_btn"):
            if len(raw_text.strip()) < 20:
                st.warning("Please paste more text first.")
            else:
                with st.spinner(f"Generating ~{target_words} word summary..."):
                    summary_text = smart_summarize(raw_text, target_words)
                    formatted = apply_summary_formatting(summary_text, fmt)
                    node['summary'] = formatted
                    if node['title'].startswith("Untitled"):
                        node['title'] = raw_text[:18]+"..."
                    st.session_state['all_summaries'][st.session_state['active_summary_id']] = node
                    st.rerun()

        if node['summary']:
            st.write("---")
            ct, cd = st.columns([9.5, 0.5])
            with ct: st.markdown(node['summary'])
            with cd:
                if st.button("⋮", key="dots_sum_main"):
                    st.session_state['active_bubble_menu_id'] = "sum_menu" if st.session_state.get('active_bubble_menu_id') != "sum_menu" else ""
                    st.rerun()
            if st.session_state.get('active_bubble_menu_id') == "sum_menu":
                _, mc, _ = st.columns([6, 3, 1])
                with mc:
                    st.markdown("""<div style='background:#1A2234;border:1px solid #2D3748;border-radius:12px;padding:6px;box-shadow:0 8px 24px rgba(0,0,0,0.6);'>""", unsafe_allow_html=True)
                    if st.button("📋  Copy", key="cp_sum", use_container_width=True):
                        st.toast("Copied!"); st.code(node['summary'], language="markdown")
                        st.session_state['active_bubble_menu_id'] = ""; st.rerun()
                    if st.button("↗  Share", key="sh_sum", use_container_width=True):
                        st.toast("Link copied!")
                        st.session_state['active_bubble_menu_id'] = ""; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

    # PLANNER
    elif st.session_state['current_view'] == "planner":
        st.markdown("### 📅 Adaptive Study Planner")
        st.caption("Customizes Pomodoro intervals based on your current emotional state.")
        if not st.session_state['all_plans']:
            st.session_state['all_plans']["planner_default"] = {"subjects":"","weak":"","mood":"","schedule":[],"title":"Untitled Plan"}
            st.session_state['active_planner_id'] = "planner_default"
        elif not st.session_state['active_planner_id']:
            st.session_state['active_planner_id'] = list(st.session_state['all_plans'].keys())[0]

        plan = st.session_state['all_plans'].get(st.session_state['active_planner_id'])
        with st.form("planner_form"):
            c1,c2 = st.columns(2)
            with c1:
                subj = st.text_input("Subjects (comma separated):", value=plan['subjects'], placeholder="e.g. Python ML DSA")
                start_time = st.time_input("Start Time:", datetime.time(9,0))
            with c2:
                weak = st.text_input("Your Weak Subject:", value=plan['weak'], placeholder="e.g. Python")
                mood = st.text_input("How are you feeling?", value=plan['mood'], placeholder="e.g. Tired happy stressed")
            gen = st.form_submit_button("🗓️  Generate Schedule", use_container_width=True)

        if gen:
            slist = [s.strip() for s in subj.split(",") if s.strip()]
            if not slist: st.error("Enter at least one subject.")
            else:
                mood_score = sia.polarity_scores(mood)['compound']
                boost = get_motivational_message(mood_score)
                plan.update({'subjects':subj,'weak':weak,'mood':mood})
                if plan['title'].startswith("Untitled") and slist:
                    plan['title'] = f"Plan: {slist[0]}"
                short_break = 10 if mood_score < -0.1 else 5
                schedule = []
                t = datetime.datetime.combine(datetime.date.today(), start_time)
                for sub in slist:
                    for _ in range(2 if sub.lower()==weak.strip().lower() else 1):
                        end = t + datetime.timedelta(minutes=25)
                        schedule.append({"range":f"{t.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}",
                            "subject":sub,"break_len":short_break,
                            "next_resume":(end+datetime.timedelta(minutes=short_break)).strftime('%I:%M %p'),
                            "is_mellow":mood_score < -0.1})
                        t = end + datetime.timedelta(minutes=short_break)
                plan['schedule'] = schedule; plan['boost'] = boost
                st.session_state['all_plans'][st.session_state['active_planner_id']] = plan
                st.rerun()

        if plan.get('schedule'):
            st.write("---")
            st.info(plan['boost'])
            if plan['schedule'][0]['is_mellow']:
                st.warning("🌙 Mellow Mode: 25 min focus + 10 min recovery breaks.")
            else:
                st.success("⚡ Classic Mode: 25 min focus + 5 min breaks.")
            st.markdown("#### Your Schedule")
            for s in plan['schedule']:
                st.markdown(f"""<div style='background:#0D1117;padding:1rem;border-radius:10px;
                    margin-bottom:0.6rem;border:1px solid #1E2533;border-left:4px solid #F59E0B;'>
                    <span style='color:#60A5FA;font-weight:700;'>⏱️ {s["range"]}</span> &nbsp;|&nbsp;
                    Focus: <b style='color:#F1F5F9;'>{s["subject"]}</b>
                    <br><span style='color:#9CA3AF;font-size:0.85rem;'>☕ {s["break_len"]} min break → Resume at {s["next_resume"]}</span>
                </div>""", unsafe_allow_html=True)

# ---------------------- AUTH ----------------------
def render_login_page():
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown("""<div style='text-align:center;margin:2rem 0 1.5rem;'>
            <div style='font-size:3rem;'>✈️</div>
            <h1 style='font-weight:900;font-size:2.4rem;margin:0;letter-spacing:-1px;'>StudyPilot</h1>
            <p style='color:#6B7280;font-size:0.95rem;margin:6px 0 0;'>Your AI-Powered Learning Assistant</p>
        </div>""", unsafe_allow_html=True)

        if st.session_state['auth_view'] == "welcome":
            st.write("")
            if st.button("🔐  Sign In", use_container_width=True):
                st.session_state['auth_view'] = "login"; st.rerun()
            st.write("")
            if st.button("📝  Create Account", use_container_width=True):
                st.session_state['auth_view'] = "register"
                st.session_state['reg_step'] = "input_email"; st.rerun()

        elif st.session_state['auth_view'] == "login":
            st.markdown("### Sign In")
            with st.form("login_form"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                sub = st.form_submit_button("Sign In →", use_container_width=True)
            if sub:
                if u.strip() in st.session_state['user_db'] and \
                        st.session_state['user_db'][u.strip()]['password'] == hash_password(p.strip()):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u.strip(); st.rerun()
                else:
                    st.error("❌ Invalid username or password.")
            cl,cr = st.columns(2)
            with cl:
                if st.button("⬅ Back", key="back_login", use_container_width=True):
                    st.session_state['auth_view'] = "welcome"; st.rerun()
            with cr:
                if st.button("Forgot Password?", key="forgot_btn", use_container_width=True):
                    st.session_state['auth_view'] = "forgot_password"
                    st.session_state['forgot_step'] = "verify_email"; st.rerun()

        elif st.session_state['auth_view'] == "register":
            st.markdown("### Create Account")

            if st.session_state['reg_step'] == "input_email":
                with st.form("reg_email_form"):
                    ei = st.text_input("Your Email Address", placeholder="name@gmail.com")
                    send = st.form_submit_button("Send Verification Code →", use_container_width=True)
                if send:
                    if not validate_email(ei.strip()):
                        st.error("❌ Enter a valid email.")
                    else:
                        otp = str(random.randint(100000,999999))
                        ok,err = send_otp_email(ei.strip(), otp)
                        if ok:
                            st.session_state.update({'generated_otp':otp,'otp_timestamp':datetime.datetime.now(),
                                                     'temp_identity':ei.strip(),'reg_step':"verify_otp"})
                            st.success(f"✅ OTP sent to {ei.strip()}!"); st.rerun()
                        else:
                            st.error(f"❌ Failed: {err}")
                if st.button("⬅ Cancel", use_container_width=True):
                    st.session_state['auth_view'] = "welcome"; st.rerun()

            elif st.session_state['reg_step'] == "verify_otp":
                st.info(f"📬 OTP sent to **{st.session_state['temp_identity']}**")
                if is_otp_expired():
                    st.error("⏰ OTP expired.")
                    if st.button("Resend OTP", use_container_width=True):
                        otp = str(random.randint(100000,999999))
                        ok,_ = send_otp_email(st.session_state['temp_identity'], otp)
                        if ok:
                            st.session_state.update({'generated_otp':otp,'otp_timestamp':datetime.datetime.now()})
                            st.success("New OTP sent!"); st.rerun()
                else:
                    with st.form("otp_form"):
                        entered = st.text_input("Enter 6-Digit OTP", max_chars=6, placeholder="______")
                        verify = st.form_submit_button("Verify →", use_container_width=True)
                    if verify:
                        if entered.strip() == st.session_state['generated_otp']:
                            st.session_state['reg_step'] = "set_credentials"; st.rerun()
                        else:
                            st.error("❌ Incorrect OTP.")
                    if st.button("⬅ Back", key="back_otp"):
                        st.session_state['reg_step'] = "input_email"; st.rerun()

            elif st.session_state['reg_step'] == "set_credentials":
                st.success(f"✅ Email verified: {st.session_state['temp_identity']}")
                with st.form("cred_form"):
                    ru = st.text_input("Choose a Username")
                    rp = st.text_input("Choose a Password", type="password")
                    rc = st.text_input("Confirm Password", type="password")
                    done = st.form_submit_button("Create Account →", use_container_width=True)
                if done:
                    if len(ru.strip()) < 3: st.error("❌ Username too short.")
                    elif ru.strip() in st.session_state['user_db']: st.error("❌ Username taken.")
                    elif rp != rc: st.error("❌ Passwords don't match.")
                    elif len(rp) < 4: st.error("❌ Password too short.")
                    else:
                        st.session_state['user_db'][ru.strip()] = {
                            "identity": st.session_state['temp_identity'],
                            "password": hash_password(rp.strip())
                        }
                        # AUTO LOGIN after registration
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = ru.strip()
                        st.success("🎉 Welcome to StudyPilot!")
                        st.rerun()

        elif st.session_state['auth_view'] == "forgot_password":
            st.markdown("### Reset Password")
            if st.session_state['forgot_step'] == "verify_email":
                with st.form("forgot_form"):
                    re_email = st.text_input("Registered Email")
                    lookup = st.form_submit_button("Send Reset OTP →", use_container_width=True)
                if lookup:
                    found = next((u for u,m in st.session_state['user_db'].items() if m['identity']==re_email.strip()), None)
                    if found:
                        otp = str(random.randint(100000,999999))
                        ok,err = send_otp_email(re_email.strip(), otp)
                        if ok:
                            st.session_state.update({'recovery_target_user':found,'generated_otp':otp,
                                                     'otp_timestamp':datetime.datetime.now(),'forgot_step':"verify_otp"})
                            st.success("✅ OTP sent!"); st.rerun()
                        else: st.error(f"❌ {err}")
                    else: st.error("❌ No account found.")
                if st.button("⬅ Back", key="back_forgot", use_container_width=True):
                    st.session_state['auth_view'] = "login"; st.rerun()

            elif st.session_state['forgot_step'] == "verify_otp":
                st.info("📬 OTP sent to your registered email.")
                st.caption(f"Account: **{st.session_state['recovery_target_user']}**")
                if not is_otp_expired():
                    with st.form("forgot_otp_form"):
                        rotp = st.text_input("6-Digit OTP", max_chars=6)
                        vrfy = st.form_submit_button("Verify →", use_container_width=True)
                    if vrfy:
                        if rotp.strip() == st.session_state['generated_otp']:
                            st.session_state['forgot_step'] = "reset_password"; st.rerun()
                        else: st.error("❌ Incorrect OTP.")
                else: st.error("⏰ OTP expired.")

            elif st.session_state['forgot_step'] == "reset_password":
                st.write(f"Reset for: **{st.session_state['recovery_target_user']}**")
                with st.form("reset_form"):
                    np1 = st.text_input("New Password", type="password")
                    np2 = st.text_input("Confirm", type="password")
                    save = st.form_submit_button("Update Password →", use_container_width=True)
                if save:
                    if np1 != np2: st.error("❌ Don't match.")
                    elif len(np1) < 4: st.error("❌ Too short.")
                    else:
                        st.session_state['user_db'][st.session_state['recovery_target_user']]['password'] = hash_password(np1.strip())
                        st.success("🔒 Updated! Sign in now.")
                        st.session_state['auth_view'] = "login"; st.rerun()

# ---------------------- ENTRY POINT ----------------------
st.set_page_config(page_title="StudyPilot", page_icon="✈️", layout="wide")

if 'app_theme' not in st.session_state:
    st.session_state['app_theme'] = "dark"

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');

/* ===== HIDE ALL STREAMLIT CHROME ===== */
#MainMenu { display:none !important; }
footer { display:none !important; }
header { display:none !important; }
[data-testid="stToolbar"] { display:none !important; }
[data-testid="stDecoration"] { display:none !important; }
[data-testid="stStatusWidget"] { display:none !important; }
[data-testid="collapsedControl"] { display:none !important; }
.viewerBadge_container__1QSob { display:none !important; }
div[data-testid="stSidebarNav"] { display:none !important; }
[data-testid="stSidebarHeader"] { display:none !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top:1rem !important; }

* { font-family:'Plus Jakarta Sans',sans-serif !important; }
.stApp { background:#080C14 !important; color:#F1F5F9 !important; }
[data-testid="stSidebar"] { background:#0D1117 !important; border-right:1px solid #1E2533 !important; }

.stTextInput>div>div>input, .stTextArea>div>div>textarea,
.stSelectbox>div>div>div, .stNumberInput>div>div>input {
    background:#0D1117 !important; color:#F1F5F9 !important;
    border:1px solid #1E2533 !important; border-radius:10px !important;
}

.chat-msg { padding:0.85rem 1.25rem; border-radius:16px; font-size:0.95rem; line-height:1.5; word-wrap:break-word !important; }
.user-bubble { background:linear-gradient(135deg,#1D4ED8,#2563EB) !important; color:#fff !important; border-bottom-right-radius:2px !important; }
.bot-bubble { background:#0D1117 !important; color:#E2E8F0 !important; border-bottom-left-radius:2px !important; border:1px solid #1E2533; }

.navbar-wrapper { padding:0.2rem; margin-bottom:0.5rem; }
.navbar-wrapper button { background:#0D1117 !important; border:1px solid #1E2533 !important; color:#94A3B8 !important; font-weight:600 !important; }
.navbar-wrapper button:hover { background:#1E2533 !important; color:#F1F5F9 !important; }

.stButton>button { background:#0D1117 !important; color:#CBD5E1 !important; border-radius:10px !important; border:1px solid #1E2533 !important; font-weight:600 !important; height:2.6em !important; transition:all 0.15s !important; }
.stButton>button:hover { background:#2563EB !important; color:#fff !important; border-color:#2563EB !important; }

button[key="profile_btn"] { color:#60A5FA !important; font-weight:700 !important; text-align:left !important; }
button[key="logout_btn"] { color:#F87171 !important; border-color:#3B1F1F !important; background:#1A0F0F !important; }
button[key="logout_btn"]:hover { background:#DC2626 !important; color:#fff !important; border-color:#DC2626 !important; }

button[key^="dots_"] { background:transparent !important; color:#475569 !important; border:none !important; font-size:1.4rem !important; height:auto !important; padding:0 !important; box-shadow:none !important; }
button[key^="dots_"]:hover { color:#F1F5F9 !important; }

button[key^="sel_"] { background:#0D1117 !important; text-align:left !important; justify-content:flex-start !important; color:#CBD5E1 !important; font-size:0.88rem !important; }

button[key^="share_"], button[key^="ren_"], button[key^="cp_"], button[key^="sh_"] {
    background:#243040 !important; border:none !important; color:#E2E8F0 !important;
    font-size:0.9rem !important; height:2.4em !important; border-radius:8px !important;
    text-align:left !important; justify-content:flex-start !important; font-weight:500 !important;
}
button[key^="share_"]:hover, button[key^="ren_"]:hover, button[key^="cp_"]:hover, button[key^="sh_"]:hover {
    background:#2563EB !important; color:#fff !important;
}
button[key^="del_"] {
    background:#2A1515 !important; border:none !important; color:#F87171 !important;
    font-size:0.9rem !important; height:2.4em !important; border-radius:8px !important;
    text-align:left !important; justify-content:flex-start !important; font-weight:500 !important;
}
button[key^="del_"]:hover { background:#DC2626 !important; color:#fff !important; }

button[key^="new_"] { background:#0F1E38 !important; color:#60A5FA !important; border:1px dashed #3B82F6 !important; font-weight:700 !important; }
button[key^="new_"]:hover { background:#2563EB !important; color:#fff !important; border-color:#2563EB !important; }

[data-testid="stForm"] { border:none !important; background:transparent !important; padding:0 !important; }
.stAlert { border-radius:10px !important; }
</style>""", unsafe_allow_html=True)

# SESSION STATE
defaults = {
    'logged_in':False,'username':'','message_history':{},
    'show_profile_tray':False,'active_menu_item_id':'','active_bubble_menu_id':'',
    'current_view':'welcome_hub','auth_view':'welcome',
    'reg_step':'input_email','forgot_step':'verify_email',
    'generated_otp':None,'otp_timestamp':None,'temp_identity':'',
    'recovery_target_user':'','editing_item_id':'','rename_feature_target':'',
    'user_db':{"admin":{"identity":"admin@studypilot.com","password":hash_password("student123")}},
    'all_chats':{},'active_chat_id':'',
    'all_summaries':{},'active_summary_id':'',
    'all_plans':{},'active_planner_id':''
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state['logged_in']:
    render_main_app()
else:
    render_login_page()