import streamlit as st
import json
import os
import pandas as pd
import numpy as np
import nltk
import datetime
import hashlib
import random
import re
import smtplib
import os
import difflib
import pyperclip
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
                            <p style="margin:6px 0 0;color:#BFDBFE;font-size:13px;">Your Learning Assistant</p>
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
                "A list is an ordered mutable collection. Example: my_list = [1, 2, 3]"
            ]
        }
        df = pd.DataFrame(data)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(df["question"].values.astype("U"))
    return df, vectorizer, tfidf_matrix

df, vectorizer, tfidf_matrix = prepare_data()

# ---------------------- SPELL CORRECTION ----------------------
def correct_spelling(text):
    """Correct spelling using difflib against known question vocabulary."""
    all_questions = " ".join(df["question"].values).lower()
    vocab = list(set(all_questions.split()))
    words = text.lower().split()
    corrected = []
    corrections = {}
    for word in words:
        if len(word) <= 2:
            corrected.append(word)
            continue
        matches = difflib.get_close_matches(word, vocab, n=1, cutoff=0.75)
        if matches and matches[0] != word:
            corrections[word] = matches[0]
            corrected.append(matches[0])
        else:
            corrected.append(word)
    return " ".join(corrected), corrections

def get_smart_response(user_query):
    score = sia.polarity_scores(user_query)
    corrected_query, corrections = correct_spelling(user_query)
    user_vec = vectorizer.transform([corrected_query])
    similarity = cosine_similarity(user_vec, tfidf_matrix)
    idx = similarity.argmax()
    spell_note = ""
    if corrections:
        fixes = ", ".join([f"'{k}' → '{v}'" for k, v in corrections.items()])
        spell_note = f"📝 *Spell check: {fixes}*\n\n"
    if similarity[0][idx] < 0.2:
        return spell_note + "I'm not sure about that. Try asking about Python concepts like functions, classes, lists, recursion, or sorting algorithms.", score, corrected_query
    return spell_note + df.iloc[idx]["answer"], score, corrected_query

# ---------------------- MOTIVATIONAL ENGINE ----------------------
MOTIVATIONAL_BANK = {
    "positive": [
        "You're absolutely crushing it today! This kind of energy is exactly what separates good students from great engineers. Keep going!",
        "Your focus is top-tier right now! Every problem you solve today is building the foundation of your future career.",
        "Love the positive energy! You're in the zone — this is when the best learning happens. Don't stop now!",
        "Brilliant mindset! Consistent sessions like this compound over time into real mastery. You're on the right path."
    ],
    "neutral": [
        "Steady focus is underrated. Most breakthroughs happen not in bursts of excitement but in quiet sessions like this one.",
        "One concept at a time, one session at a time. You're building something that will last a lifetime.",
        "Even on average days, showing up is the most powerful thing you can do. You're already ahead of most.",
        "Calm and consistent beats intense and irregular every single time. Trust the process."
    ],
    "negative": [
        "Hey — it's okay to be tired. Even studying for 20 minutes today when you're exhausted shows real character. I've got you.",
        "Be kind to your mind right now. Rest is not the opposite of progress — it's part of it. Let's take this gently.",
        "You're here even when you don't feel like it. That's not weakness — that's discipline. Let's take it slow today.",
        "Hard days build the strongest students. Take a deep breath. We'll break this into the smallest possible steps together.",
        "I see you pushing through. That matters more than you know. Let's make even this tough session count."
    ]
}

CHECKIN_MESSAGES = {
    "positive": "You seem to be in great spirits today! Let's channel that energy into a powerful session.",
    "neutral": "You're in a steady, focused state. Perfect for deep learning.",
    "negative": "It sounds like you're having a tough time right now. That's completely okay — we'll build a gentler schedule for you today. You're not alone in this."
}

def get_motivational_message(sentiment_score):
    cat = "positive" if sentiment_score >= 0.1 else ("negative" if sentiment_score <= -0.1 else "neutral")
    opts = MOTIVATIONAL_BANK[cat]
    avail = [m for m in opts if st.session_state['message_history'].get(m, 0) < 2] or opts
    chosen = random.choice(avail)
    st.session_state['message_history'][chosen] = st.session_state['message_history'].get(chosen, 0) + 1
    return chosen, cat, CHECKIN_MESSAGES[cat]

# ---------------------- SUMMARIZER ----------------------
def clean_summary(text):
    """Clean T5 output: fix spacing, capitalisation, remove garbage sentences."""
    # Fix "word ." → "word." and "word , " → "word, "
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    # Remove stray markdown headings (# Heading) anywhere in the text
    text = re.sub(r'#+\s+[^\n]+', '', text)
    text = text.strip()

    sentences = nltk.sent_tokenize(text)
    clean = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # Skip garbage: too short, starts with punctuation, repeated words
        if len(s.split()) < 4:
            continue
        if s.startswith(("'", '"', '.', ',', '&')):
            continue
        if s.count('.') > 4:
            continue
        if re.search(r'\b(\w+)\s+\1\b', s):  # repeated words like "com com"
            continue
        # Capitalise first letter of every sentence
        s = s[0].upper() + s[1:]
        clean.append(s)

    # Drop the last sentence if it sounds like a non-sequitur filler
    filler_patterns = [
        r"^(but|however|although|yet)\b.*\b(difficult|achieve|goals|wealth)\b",
        r"^(it|this) (can|could|may) be (a |an )?(good|bad|difficult)",
    ]
    if clean:
        last = clean[-1].lower()
        for pat in filler_patterns:
            if re.search(pat, last):
                clean = clean[:-1]
                break

    return " ".join(clean)

def smart_summarize(text, target_words):
    input_words = len(text.split())
    if input_words <= target_words:
        return text.strip()

    # Split into ~400-word chunks for T5
    words = text.split()
    chunk_size = 400
    chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
    chunks = [c for c in chunks if len(c.split()) >= 20]
    if not chunks:
        return text.strip()

    # T5 tokens ≈ 0.75 words. To get `target_words` words out, ask for ~1.4x tokens.
    # Distribute evenly across chunks, cap at T5's max (512).
    words_per_chunk = max(50, target_words // len(chunks))
    max_tok = min(int(words_per_chunk * 1.4), 512)
    min_tok = max(30, int(words_per_chunk * 1.0))   # min = 100% of target per chunk

    all_summaries = []
    for chunk in chunks:
        try:
            raw = summarizer(chunk, max_length=max_tok, min_length=min_tok, do_sample=False)
            all_summaries.append(raw[0]['summary_text'])
        except:
            all_summaries.append(" ".join(chunk.split()[:words_per_chunk]))

    combined = " ".join(all_summaries)
    combined = clean_summary(combined)

    # If T5 still produced fewer words than target, pad from the original text
    combined_words = len(combined.split())
    if combined_words < target_words:
        orig_sentences = nltk.sent_tokenize(text)
        used = set(combined.lower().split()[:20])
        for s in orig_sentences:
            if len(combined.split()) >= target_words:
                break
            # Add sentences not already captured
            if s.strip() not in combined:
                combined = combined + " " + s.strip()

    # Trim to target at a clean sentence boundary
    sentences = nltk.sent_tokenize(combined)
    result = []
    word_count = 0
    for sent in sentences:
        sent_words = len(sent.split())
        if word_count + sent_words <= target_words + 25:
            result.append(sent)
            word_count += sent_words
        else:
            break

    # If we're still under (T5 just didn't produce enough), keep everything we have
    if word_count < target_words - 20 and not result:
        result = sentences

    final = " ".join(result) if result else combined

    # Hard trim only if well over
    final_words = final.split()
    if len(final_words) > target_words + 35:
        final = " ".join(final_words[:target_words + 15])
        last_dot = final.rfind('.')
        if last_dot > len(final) * 0.5:
            final = final[:last_dot + 1]

    return final.strip() if final.strip() else combined

def apply_summary_formatting(raw_text, fmt):
    today = datetime.date.today().strftime("%B %d, %Y")
    sentences = nltk.sent_tokenize(raw_text)
    wc = len(raw_text.split())
    out = f"### Summary ({fmt}) — ~{wc} words\n\n"

    if fmt == "Bullet Points":
        out += "#### Core Takeaways\n"
        for s in sentences:
            s = s.strip()
            if s:
                # Ensure capital + no trailing space before period
                s = s[0].upper() + s[1:]
                out += f"- {s}\n"

    elif fmt == "Essay":
        # Split into intro (first 2 sentences), body (middle), conclusion (last 1–2)
        intro = " ".join(sentences[:2]) if len(sentences) >= 2 else raw_text
        body  = " ".join(sentences[2:-2]) if len(sentences) > 4 else ""
        concl = " ".join(sentences[-2:]) if len(sentences) >= 2 else sentences[-1]
        intro = intro[0].upper() + intro[1:]
        out += f"**Introduction:** {intro}\n\n"
        if body:
            body = body[0].upper() + body[1:]
            out += f"**Core Discussion:** {body}\n\n"
        concl = concl[0].upper() + concl[1:]
        out += f"**Conclusion:** {concl}"

    elif fmt == "Letter":
        body = raw_text[0].upper() + raw_text[1:]
        out += (
            f"**Date:** {today}  \n"
            f"**To:** Study Group Peers  \n\n"
            f"Dear Student,\n\n"
            f"{body}\n\n"
            f"Best regards,  \n"
            f"*{st.session_state['username']}*"
        )

    elif fmt == "Email":
        body = raw_text[0].upper() + raw_text[1:]
        out += (
            f"**Subject:** Lecture Summary — {today}  \n"
            f"---  \n"
            f"Hi Team,\n\n"
            f"{body}\n\n"
            f"Thanks,  \n"
            f"**{st.session_state['username']}**"
        )

    else:
        out += raw_text[0].upper() + raw_text[1:]

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
            st.markdown("""<div style='background:#161D2E;border:1px solid #2D3748;border-radius:10px;
                padding:4px 0;margin:2px 0 6px 0;box-shadow:0 4px 20px rgba(0,0,0,0.6);overflow:hidden;'>""", unsafe_allow_html=True)
            if st.button("↗  Share", key=f"share_{item_id}_{feature_key}", use_container_width=True):
                st.toast("Link copied!"); st.session_state['active_menu_item_id'] = ""; st.rerun()
            if st.button("✏️  Rename", key=f"ren_{item_id}_{feature_key}", use_container_width=True):
                st.session_state['editing_item_id'] = item_id
                st.session_state['rename_feature_target'] = feature_key
                st.session_state['active_menu_item_id'] = ""; st.rerun()
            st.markdown("<div style='height:1px;background:#2D3748;margin:2px 8px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️  Delete", key=f"del_{item_id}_{feature_key}", use_container_width=True):
                del history_dict[item_id]
                save_data()
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
                    save_data()
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
                with cb:
                    st.markdown(f"<div class='chat-msg user-bubble'>{msg['text']}</div>", unsafe_allow_html=True)
                with cd:
                    if st.button("⋮", key=f"dots_chat_{msg_id}"):
                        st.session_state['active_bubble_menu_id'] = msg_id if st.session_state.get('active_bubble_menu_id') != msg_id else ""
                        st.rerun()
            else:
                cb, cd, _ = st.columns([6, 0.5, 3.5])
                with cb:
                    st.markdown(f"<div class='chat-msg bot-bubble'>{msg['text']}</div>", unsafe_allow_html=True)
                with cd:
                    if st.button("⋮", key=f"dots_chat_{msg_id}"):
                        st.session_state['active_bubble_menu_id'] = msg_id if st.session_state.get('active_bubble_menu_id') != msg_id else ""
                        st.rerun()

            if st.session_state.get('active_bubble_menu_id') == msg_id:
                if msg['role'] == "user":
                    _, mc, _ = st.columns([3.5, 2.2, 4.3])
                else:
                    mc_col, _, _ = st.columns([2.2, 4.3, 3.5])
                    mc = mc_col
                with mc:
                    st.markdown("""<div style='background:#161D2E;border:1px solid #2D3748;border-radius:8px;
                        padding:2px 0;box-shadow:0 4px 16px rgba(0,0,0,0.5);overflow:hidden;'>""", unsafe_allow_html=True)
                    if st.button("📋 Copy", key=f"cp_{msg_id}", use_container_width=True):
                        try:
                            pyperclip.copy(msg['text'])
                        except Exception:
                            pass
                        st.toast("Copied! ✅")
                        st.session_state['active_bubble_menu_id'] = ""
                        st.rerun()
                    if st.button("↗ Share", key=f"sh_{msg_id}", use_container_width=True):
                        st.toast("Link copied!")
                        st.session_state['active_bubble_menu_id'] = ""; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)



        st.write("")
        with st.form("chat_form", clear_on_submit=True):
            chat_input = st.text_input("", placeholder="e.g. What is recursion in Python?", label_visibility="collapsed")
            send = st.form_submit_button("Send →", use_container_width=True)

        if send and chat_input.strip():
            ans, sentiment, corrected = get_smart_response(chat_input)
            if sentiment['compound'] >= 0.05: st.toast("Positive vibes! 😊")
            elif sentiment['compound'] <= -0.05: st.toast("You seem stressed. Take it easy! 💙")
            active_chat.append({"role":"user","text":chat_input})
            active_chat.append({"role":"assistant","text":ans})
            st.session_state['all_chats'][st.session_state['active_chat_id']] = active_chat
            save_data()
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
        raw_text = st.text_area("", value=node['text'], height=220,
                                placeholder="Paste your lecture notes here...", label_visibility="collapsed")
        if raw_text.strip():
            input_wc = len(raw_text.split())
            st.caption(f"📄 Input: {input_wc} words")

        cc, cf = st.columns(2)
        with cc:
            target_words = st.number_input("Target word count:", min_value=10, max_value=500,
                                           value=int(node.get('word_count',80)), step=10)
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
                    node['raw_summary'] = summary_text
                    if node['title'].startswith("Untitled"):
                        node['title'] = raw_text[:18]+"..."
                    st.session_state['all_summaries'][st.session_state['active_summary_id']] = node
                    save_data()
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
                        st.session_state['show_copy_summary'] = True
                        st.session_state['active_bubble_menu_id'] = ""; st.rerun()
                    if st.button("↗  Share", key="sh_sum", use_container_width=True):
                        st.toast("Link copied!")
                        st.session_state['active_bubble_menu_id'] = ""; st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get('show_copy_summary', False):
                st.code(node.get('raw_summary', node['summary']), language="text")
                if st.button("✕ Close", key="close_copy_sum"):
                    st.session_state['show_copy_summary'] = False; st.rerun()

    # PLANNER
    elif st.session_state['current_view'] == "planner":
        st.markdown("### 📅 Adaptive Study Planner")
        st.caption("Your schedule adapts based on how you feel — because your wellbeing matters as much as your grades.")

        if not st.session_state['all_plans']:
            st.session_state['all_plans']["planner_default"] = {"subjects":"","weak":"","mood":"","schedule":[],"title":"Untitled Plan"}
            st.session_state['active_planner_id'] = "planner_default"
        elif not st.session_state['active_planner_id']:
            st.session_state['active_planner_id'] = list(st.session_state['all_plans'].keys())[0]

        plan = st.session_state['all_plans'].get(st.session_state['active_planner_id'])

        with st.form("planner_form"):
            c1, c2 = st.columns(2)
            with c1:
                subj = st.text_input("Subjects (comma separated):", value=plan['subjects'],
                                     placeholder="e.g. Python, ML, DSA")
                start_time = st.time_input("Start Time:", datetime.time(9, 0))
            with c2:
                weak = st.text_input("Your Weak Subject:", value=plan['weak'],
                                     placeholder="e.g. Python")
                end_time = st.time_input("End Time:", datetime.time(12, 0))

            mood = st.text_input("How are you feeling right now?", value=plan['mood'],
                                 placeholder="e.g. tired, stressed, excited, motivated, anxious...")
            gen = st.form_submit_button("🗓️  Generate My Schedule", use_container_width=True)

        if gen:
            slist = [s.strip() for s in subj.split(",") if s.strip()]
            if not slist:
                st.error("Please enter at least one subject.")
            elif end_time <= start_time:
                st.error("End time must be after start time.")
            else:
                mood_score = sia.polarity_scores(mood)['compound']
                boost, mood_cat, checkin = get_motivational_message(mood_score)
                plan.update({'subjects': subj, 'weak': weak, 'mood': mood})
                if plan['title'].startswith("Untitled") and slist:
                    plan['title'] = f"Plan: {slist[0]}"

                # Calculate available time
                start_dt = datetime.datetime.combine(datetime.date.today(), start_time)
                end_dt = datetime.datetime.combine(datetime.date.today(), end_time)
                total_minutes = int((end_dt - start_dt).total_seconds() / 60)

                # Adapt intervals based on mood
                if mood_score <= -0.3:
                    work_mins = 20
                    break_mins = 10
                    mode = "gentle"
                elif mood_score <= -0.1:
                    work_mins = 25
                    break_mins = 10
                    mode = "mellow"
                else:
                    work_mins = 25
                    break_mins = 5
                    mode = "classic"

                # Build schedule fitting within available time
                schedule = []
                t = start_dt
                # Weight weak subject double
                weighted = []
                for s in slist:
                    weighted.append(s)
                    if s.lower() == weak.strip().lower():
                        weighted.append(s)

                i = 0
                session_num = 1
                while t < end_dt:
                    remaining = int((end_dt - t).total_seconds() / 60)
                    if remaining < work_mins:
                        break
                    sub = weighted[i % len(weighted)]
                    actual_work = min(work_mins, remaining)
                    end_session = t + datetime.timedelta(minutes=actual_work)
                    actual_break = min(break_mins, int((end_dt - end_session).total_seconds() / 60))
                    resume_at = end_session + datetime.timedelta(minutes=actual_break)

                    schedule.append({
                        "session": session_num,
                        "start": t.strftime('%I:%M %p'),
                        "end": end_session.strftime('%I:%M %p'),
                        "subject": sub,
                        "is_weak": sub.lower() == weak.strip().lower(),
                        "break_len": actual_break,
                        "resume": resume_at.strftime('%I:%M %p'),
                        "mode": mode
                    })
                    t = resume_at
                    i += 1
                    session_num += 1

                plan['schedule'] = schedule
                plan['boost'] = boost
                plan['checkin'] = checkin
                plan['mood_cat'] = mood_cat
                plan['mode'] = mode
                plan['total_minutes'] = total_minutes
                st.session_state['all_plans'][st.session_state['active_planner_id']] = plan
                save_data()
                st.rerun()

        if plan.get('schedule'):
            st.write("---")

            # Emotional check-in card
            mood_cat = plan.get('mood_cat', 'neutral')
            checkin = plan.get('checkin', '')
            checkin_colors = {"positive": "#064E3B", "neutral": "#1E3A5F", "negative": "#3B1F1F"}
            checkin_border = {"positive": "#34D399", "neutral": "#60A5FA", "negative": "#F87171"}
            checkin_icon = {"positive": "🌟", "neutral": "🎯", "negative": "💙"}

            st.markdown(f"""
            <div style='background:{checkin_colors[mood_cat]};border:1px solid {checkin_border[mood_cat]};
                border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>
                <span style='font-size:1.1rem;font-weight:700;color:{checkin_border[mood_cat]};'>{checkin_icon[mood_cat]} Mood Check-in</span>
                <p style='color:#E2E8F0;margin:6px 0 0;font-size:0.95rem;'>{checkin}</p>
            </div>
            """, unsafe_allow_html=True)

            # Motivational message
            st.markdown(f"""
            <div style='background:#0D1117;border:1px solid #1E2533;border-left:4px solid #F59E0B;
                border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>
                <span style='color:#F59E0B;font-weight:700;'>✨ Your Motivation</span>
                <p style='color:#CBD5E1;margin:6px 0 0;font-size:0.95rem;font-style:italic;'>"{plan['boost']}"</p>
            </div>
            """, unsafe_allow_html=True)

            # Mode banner
            mode = plan.get('mode', 'classic')
            if mode == "gentle":
                st.warning("🌙 Gentle Mode: 20 min focus + 10 min recovery. You've got this, one small step at a time.")
            elif mode == "mellow":
                st.warning("🌙 Mellow Mode: 25 min focus + 10 min recovery. Taking care of yourself is part of studying.")
            else:
                st.success("⚡ Classic Mode: 25 min focus + 5 min breaks. You're sharp — let's make every session count!")

            # Schedule stats
            total = plan.get('total_minutes', 0)
            sessions = len(plan['schedule'])
            st.markdown(f"""
            <div style='display:flex;gap:12px;margin:1rem 0;'>
                <div style='background:#0D1117;border:1px solid #1E2533;border-radius:10px;padding:0.75rem 1rem;flex:1;text-align:center;'>
                    <div style='color:#60A5FA;font-size:1.4rem;font-weight:800;'>{sessions}</div>
                    <div style='color:#64748B;font-size:0.8rem;'>Sessions</div>
                </div>
                <div style='background:#0D1117;border:1px solid #1E2533;border-radius:10px;padding:0.75rem 1rem;flex:1;text-align:center;'>
                    <div style='color:#34D399;font-size:1.4rem;font-weight:800;'>{total}</div>
                    <div style='color:#64748B;font-size:0.8rem;'>Total Minutes</div>
                </div>
                <div style='background:#0D1117;border:1px solid #1E2533;border-radius:10px;padding:0.75rem 1rem;flex:1;text-align:center;'>
                    <div style='color:#F59E0B;font-size:1.4rem;font-weight:800;'>{plan["schedule"][0]["break_len"]}</div>
                    <div style='color:#64748B;font-size:0.8rem;'>Break Mins</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Clean table
            st.markdown("#### 📋 Your Schedule")
            table_rows = ""
            for s in plan['schedule']:
                highlight = "#1A2F1A" if s['is_weak'] else "#0D1117"
                badge = " <span style='background:#F59E0B;color:#000;font-size:0.7rem;padding:1px 6px;border-radius:4px;font-weight:700;'>WEAK</span>" if s['is_weak'] else ""
                table_rows += f"""
                <tr style='border-bottom:1px solid #1E2533;background:{highlight};'>
                    <td style='padding:10px 12px;color:#64748B;font-size:0.85rem;'>#{s['session']}</td>
                    <td style='padding:10px 12px;color:#60A5FA;font-weight:700;white-space:nowrap;'>{s['start']}</td>
                    <td style='padding:10px 12px;color:#60A5FA;font-weight:700;white-space:nowrap;'>{s['end']}</td>
                    <td style='padding:10px 12px;color:#F1F5F9;font-weight:600;'>{s['subject']}{badge}</td>
                    <td style='padding:10px 12px;color:#9CA3AF;font-size:0.88rem;'>☕ {s['break_len']} min → {s['resume']}</td>
                </tr>"""

            st.markdown(f"""
            <div style='overflow-x:auto;border-radius:12px;border:1px solid #1E2533;margin-top:0.5rem;'>
                <table style='width:100%;border-collapse:collapse;font-family:inherit;'>
                    <thead>
                        <tr style='background:#111827;border-bottom:2px solid #1E2533;'>
                            <th style='padding:10px 12px;text-align:left;color:#64748B;font-size:0.8rem;font-weight:600;text-transform:uppercase;'>#</th>
                            <th style='padding:10px 12px;text-align:left;color:#64748B;font-size:0.8rem;font-weight:600;text-transform:uppercase;'>Start</th>
                            <th style='padding:10px 12px;text-align:left;color:#64748B;font-size:0.8rem;font-weight:600;text-transform:uppercase;'>End</th>
                            <th style='padding:10px 12px;text-align:left;color:#64748B;font-size:0.8rem;font-weight:600;text-transform:uppercase;'>Subject</th>
                            <th style='padding:10px 12px;text-align:left;color:#64748B;font-size:0.8rem;font-weight:600;text-transform:uppercase;'>Break</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)

            # Closing emotional note
            if mood_cat == "negative":
                st.markdown("""
                <div style='background:#1A0F0F;border:1px solid #7F1D1D;border-radius:12px;padding:1rem 1.25rem;margin-top:1rem;'>
                    <span style='color:#F87171;font-weight:700;'>💙 A Note For You</span>
                    <p style='color:#FCA5A5;margin:6px 0 0;font-size:0.9rem;'>
                    Remember — it's okay to not be okay. If at any point you feel overwhelmed, 
                    step away from studying. Your mental health always comes first. 
                    Even completing just one session today is a win. I'm proud of you for showing up. 🤍
                    </p>
                </div>
                """, unsafe_allow_html=True)

# ---------------------- AUTH ----------------------
def render_login_page():
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown("""<div style='text-align:center;margin:2rem 0 1.5rem;'>
            <div style='font-size:3rem;'>✈️</div>
            <h1 style='font-weight:900;font-size:2.4rem;margin:0;letter-spacing:-1px;'>StudyPilot</h1>
            <p style='color:#6B7280;font-size:0.95rem;margin:6px 0 0;'>Your Learning Assistant</p>
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
            cl, cr = st.columns(2)
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
                        otp = str(random.randint(100000, 999999))
                        ok, err = send_otp_email(ei.strip(), otp)
                        if ok:
                            st.session_state.update({'generated_otp': otp, 'otp_timestamp': datetime.datetime.now(),
                                                     'temp_identity': ei.strip(), 'reg_step': "verify_otp"})
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
                        otp = str(random.randint(100000, 999999))
                        ok, _ = send_otp_email(st.session_state['temp_identity'], otp)
                        if ok:
                            st.session_state.update({'generated_otp': otp, 'otp_timestamp': datetime.datetime.now()})
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
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = ru.strip()
                        st.rerun()

        elif st.session_state['auth_view'] == "forgot_password":
            st.markdown("### Reset Password")
            if st.session_state['forgot_step'] == "verify_email":
                with st.form("forgot_form"):
                    re_email = st.text_input("Registered Email")
                    lookup = st.form_submit_button("Send Reset OTP →", use_container_width=True)
                if lookup:
                    found = next((u for u, m in st.session_state['user_db'].items() if m['identity'] == re_email.strip()), None)
                    if found:
                        otp = str(random.randint(100000, 999999))
                        ok, err = send_otp_email(re_email.strip(), otp)
                        if ok:
                            st.session_state.update({'recovery_target_user': found, 'generated_otp': otp,
                                                     'otp_timestamp': datetime.datetime.now(), 'forgot_step': "verify_otp"})
                            st.success("✅ OTP sent!"); st.rerun()
                        else: st.error(f"❌ {err}")
                    else: st.error("❌ No account found.")
                if st.button("⬅ Back", key="back_forgot", use_container_width=True):
                    st.session_state['auth_view'] = "login"; st.rerun()

            elif st.session_state['forgot_step'] == "verify_otp":
                st.info("📬 OTP sent to your registered email.")
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
                with st.form("reset_form"):
                    np1 = st.text_input("New Password", type="password")
                    np2 = st.text_input("Confirm", type="password")
                    save = st.form_submit_button("Update Password →", use_container_width=True)
                if save:
                    if np1 != np2: st.error("❌ Don't match.")
                    elif len(np1) < 4: st.error("❌ Too short.")
                    else:
                        st.session_state['user_db'][st.session_state['recovery_target_user']]['password'] = hash_password(np1.strip())
                        save_data()
                        st.success("🔒 Updated! Sign in now.")
                        st.session_state['auth_view'] = "login"; st.rerun()

# ---------------------- PERSISTENCE ----------------------
DATA_FILE = "studypilot_data.json"

def load_data():
    """Load persisted data from JSON file into session state."""
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Only load if not already populated this session
        if data.get('user_db'):
            st.session_state['user_db'] = data['user_db']
        if data.get('all_chats'):
            st.session_state['all_chats'] = data['all_chats']
        if data.get('all_summaries'):
            st.session_state['all_summaries'] = data['all_summaries']
        if data.get('all_plans'):
            st.session_state['all_plans'] = data['all_plans']
    except Exception:
        pass  # Corrupt file — start fresh

def save_data():
    """Persist current session data to JSON file."""
    try:
        data = {
            'user_db':       st.session_state.get('user_db', {}),
            'all_chats':     st.session_state.get('all_chats', {}),
            'all_summaries': st.session_state.get('all_summaries', {}),
            'all_plans':     st.session_state.get('all_plans', {}),
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ---------------------- ENTRY POINT ----------------------
st.set_page_config(page_title="StudyPilot", page_icon="✈️", layout="wide")

if 'app_theme' not in st.session_state:
    st.session_state['app_theme'] = "dark"

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');

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

button[key^="share_"], button[key^="ren_"], button[key^="cp_"], button[key^="sh_"], button[key^="close_"] {
    background:transparent !important; border:none !important; color:#CBD5E1 !important;
    font-size:0.8rem !important; height:1.9em !important; border-radius:6px !important;
    text-align:left !important; justify-content:flex-start !important; font-weight:500 !important;
    padding:0 10px !important; box-shadow:none !important;
}
button[key^="share_"]:hover, button[key^="ren_"]:hover, button[key^="cp_"]:hover, button[key^="sh_"]:hover {
    background:#1E2D45 !important; color:#fff !important;
}
button[key^="del_"] {
    background:transparent !important; border:none !important; color:#F87171 !important;
    font-size:0.8rem !important; height:1.9em !important; border-radius:6px !important;
    text-align:left !important; justify-content:flex-start !important; font-weight:500 !important;
    padding:0 10px !important; box-shadow:none !important;
}
button[key^="del_"]:hover { background:#3B1F1F !important; color:#FCA5A5 !important; }
button[key^="new_"] { background:#0F1E38 !important; color:#60A5FA !important; border:1px dashed #3B82F6 !important; font-weight:700 !important; }
button[key^="new_"]:hover { background:#2563EB !important; color:#fff !important; border-color:#2563EB !important; }

[data-testid="stForm"] { border:none !important; background:transparent !important; padding:0 !important; }
.stAlert { border-radius:10px !important; }
</style>""", unsafe_allow_html=True)

defaults = {
    'logged_in': False, 'username': '', 'message_history': {},
    'show_profile_tray': False, 'active_menu_item_id': '', 'active_bubble_menu_id': '',
    'current_view': 'welcome_hub', 'auth_view': 'welcome',
    'reg_step': 'input_email', 'forgot_step': 'verify_email',
    'generated_otp': None, 'otp_timestamp': None, 'temp_identity': '',
    'recovery_target_user': '', 'editing_item_id': '', 'rename_feature_target': '',
    'show_copy_summary': False,
    'user_db': {"admin": {"identity": "admin@studypilot.com", "password": hash_password("student123")}},
    'all_chats': {}, 'active_chat_id': '',
    'all_summaries': {}, 'active_summary_id': '',
    'all_plans': {}, 'active_planner_id': ''
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Load persisted data once per session (only when keys are freshly initialized)
if 'data_loaded' not in st.session_state:
    load_data()
    st.session_state['data_loaded'] = True

if st.session_state['logged_in']:
    render_main_app()
else:
    render_login_page()