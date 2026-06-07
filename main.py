import streamlit as st
import sqlite3
import json
import os
import re
import datetime
import hashlib
import random
import smtplib
import difflib
import requests
import pyperclip
import nltk
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline

load_dotenv()
GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
GROQ_MODEL         = "llama-3.3-70b-versatile"
GROQ_URL           = "https://api.groq.com/openai/v1/chat/completions"

def _groq_available() -> bool:
    return bool(GROQ_API_KEY) and not st.session_state.get("groq_exhausted", False)

def call_groq(messages: list, max_tokens: int = 1024) -> tuple[str, bool]:
    if not GROQ_API_KEY:
        return "", False
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip(), True
    except requests.exceptions.HTTPError:
        code = resp.status_code
        if code in (401, 429):
            st.session_state["groq_exhausted"] = True
        return "", False
    except Exception:
        return "", False

@st.cache_resource(show_spinner="Loading offline AI models (first run only)…")
def load_offline_models():
    nltk.download("vader_lexicon", quiet=True)
    nltk.download("punkt",         quiet=True)
    nltk.download("punkt_tab",     quiet=True)
    sia        = SentimentIntensityAnalyzer()
    summarizer = pipeline("summarization", model="t5-small")
    try:
        df = pd.read_csv("chatbot_data.csv")
    except Exception:
        df = pd.DataFrame({
            "question": ["what is python", "what is ml", "what is dsa", "what is a list"],
            "answer": [
                "Python is a high-level interpreted programming language known for its simple readable syntax.",
                "Machine Learning is a field of AI that enables systems to learn from data automatically.",
                "DSA stands for Data Structures and Algorithms — the foundation of efficient programming.",
                "A list is an ordered mutable collection. Example: my_list = [1, 2, 3]",
            ],
        })
    vectorizer   = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(df["question"].values.astype("U"))
    return sia, summarizer, df, vectorizer, tfidf_matrix

def get_sia():
    sia, *_ = load_offline_models()
    return sia

def _correct_spelling(text: str, df) -> tuple[str, dict]:
    vocab   = list(set(" ".join(df["question"].values).lower().split()))
    words   = text.lower().split()
    out, fixes = [], {}
    for w in words:
        if len(w) <= 2:
            out.append(w); continue
        m = difflib.get_close_matches(w, vocab, n=1, cutoff=0.75)
        if m and m[0] != w:
            fixes[w] = m[0]; out.append(m[0])
        else:
            out.append(w)
    return " ".join(out), fixes

def _t5_chat_response(user_query: str, df, vectorizer, tfidf_matrix) -> str:
    corrected, corrections = _correct_spelling(user_query, df)
    uv  = vectorizer.transform([corrected])
    sim = cosine_similarity(uv, tfidf_matrix)
    idx = sim.argmax()
    note = ""
    if corrections:
        note = "📝 *Spell check: " + ", ".join(f"'{k}' → '{v}'" for k, v in corrections.items()) + "*\n\n"
    if sim[0][idx] < 0.2:
        return note + "I'm not sure about that. Try asking about Python, ML, DSA, or algorithms."
    return note + df.iloc[idx]["answer"]

def _clean_t5(text: str) -> str:
    text = re.sub(r'\s+([.,!?;:])', r'\1', text).strip()
    sentences, out = nltk.sent_tokenize(text), []
    for s in sentences:
        s = s.strip()
        if not s or len(s.split()) < 4: continue
        if s.startswith(("'", '"', '.', ',', '&')): continue
        if s.count('.') > 4 or re.search(r'\b(\w+)\s+\1\b', s): continue
        out.append(s[0].upper() + s[1:])
    return " ".join(out)

def _t5_summarize(text: str, target_words: int, summarizer) -> str:
    if len(text.split()) <= target_words:
        return text.strip()
    words  = text.split()
    chunks = [" ".join(words[i:i+400]) for i in range(0, len(words), 400)]
    chunks = [c for c in chunks if len(c.split()) >= 20]
    if not chunks: return text.strip()
    per   = max(50, target_words // len(chunks))
    parts = []
    for chunk in chunks:
        try:
            raw = summarizer(chunk, max_length=min(int(per*1.4), 512),
                             min_length=max(30, per), do_sample=False)
            parts.append(raw[0]["summary_text"])
        except Exception:
            parts.append(" ".join(chunk.split()[:per]))
    combined = _clean_t5(" ".join(parts))
    result, wc = [], 0
    for sent in nltk.sent_tokenize(combined):
        sw = len(sent.split())
        if wc + sw <= target_words + 25:
            result.append(sent); wc += sw
        else:
            break
    final = " ".join(result) if result else combined
    fw = final.split()
    if len(fw) > target_words + 35:
        final = " ".join(fw[:target_words+15])
        dot = final.rfind('.')
        if dot > len(final) * 0.5: final = final[:dot+1]
    return final.strip() or combined

def _apply_t5_format(raw: str, fmt: str, username: str) -> str:
    today = datetime.date.today().strftime("%B %d, %Y")
    sents = nltk.sent_tokenize(raw)
    wc    = len(raw.split())
    out   = f"### Summary ({fmt}) — ~{wc} words\n\n"
    if fmt == "Bullet Points":
        out += "#### Core Takeaways\n"
        for s in sents:
            s = s.strip()
            if s: out += f"- {s[0].upper()+s[1:]}\n"
    elif fmt == "Essay":
        intro = " ".join(sents[:2]) if len(sents) >= 2 else raw
        body  = " ".join(sents[2:-2]) if len(sents) > 4 else ""
        concl = " ".join(sents[-2:]) if len(sents) >= 2 else sents[-1]
        out  += f"**Introduction:** {intro[0].upper()+intro[1:]}\n\n"
        if body: out += f"**Core Discussion:** {body[0].upper()+body[1:]}\n\n"
        out  += f"**Conclusion:** {concl[0].upper()+concl[1:]}"
    elif fmt == "Letter":
        out += f"**Date:** {today}  \n**To:** Study Group Peers  \n\nDear Student,\n\n{raw}\n\nBest regards,  \n*{username}*"
    elif fmt == "Email":
        out += f"**Subject:** Lecture Summary — {today}  \n---  \nHi Team,\n\n{raw}\n\nThanks,  \n**{username}**"
    else:
        out += raw[0].upper() + raw[1:]
    return out

def get_chat_response(user_query: str, chat_history: list) -> tuple[str, dict]:
    sia, _, df, vectorizer, tfidf_matrix = load_offline_models()
    sentiment = sia.polarity_scores(user_query)
    if _groq_available():
        messages = [
            {"role": "system", "content": (
                "You are StudyPilot's AI tutor for students studying Python, Machine Learning, "
                "Data Science, DSA, and related CS topics. "
                "IMPORTANT FORMATTING RULES — always follow these:\n"
                "- Use **bold** for key terms and important concepts\n"
                "- Use bullet points (- item) or numbered lists (1. item) when listing multiple things\n"
                "- Use `inline code` for variable names, functions, and short snippets\n"
                "- Use ```python\\n...\\n``` code blocks for multi-line code examples\n"
                "- Use ### headings for major sections when the answer is long\n"
                "- Add 💡 tip callouts with > 💡 **Tip:** text for key insights\n"
                "- Separate sections with blank lines for readability\n\n"
                "RESPONSE LENGTH:\n"
                "- Simple factual questions: 2-4 sentences with key term bolded\n"
                "- Moderate questions: structured response with bullets or short code\n"
                "- Complex questions: full explanation with headings, bullets, code blocks\n"
                "Never pad. Never over-explain simple questions. Always format cleanly."
            )},
        ]
        for msg in chat_history[-10:]:
            messages.append({"role": "user" if msg["role"] == "user" else "assistant", "content": msg["text"]})
        messages.append({"role": "user", "content": user_query})
        answer, ok = call_groq(messages, max_tokens=1500)
        if ok:
            return answer, sentiment
    answer = _t5_chat_response(user_query, df, vectorizer, tfidf_matrix)
    return answer, sentiment

def get_summary(text: str, target_words: int, fmt: str, username: str) -> tuple[str, str]:
    if _groq_available():
        today = datetime.date.today().strftime("%B %d, %Y")
        fmt_map = {
            "Plain Text":   "Write a clear, flowing paragraph summary with no headers.",
            "Bullet Points":"Format as a markdown bullet list with a '#### Core Takeaways' heading. Each bullet is a complete, informative sentence. Include as many bullets as needed to hit the word count.",
            "Essay":        "Structure as an essay with **Introduction:**, **Core Discussion:**, and **Conclusion:** sections. Each section should be a substantial paragraph.",
            "Letter":       f"Format as a letter: start with 'Date: {today}', 'To: Study Group Peers', then 'Dear Student,' paragraph(s), then 'Best regards, *{username}*'",
            "Email":        f"Format as an email: start with 'Subject: Lecture Summary — {today}', 'Hi Team,' paragraph(s), then 'Thanks, **{username}**'",
        }
        prompt = (
            f"You are an expert academic summariser. Your task is to write a summary of EXACTLY approximately {target_words} words.\n\n"
            f"FORMAT INSTRUCTION: {fmt_map.get(fmt, fmt_map['Plain Text'])}\n\n"
            f"STRICT WORD COUNT RULES:\n"
            f"- Target: {target_words} words\n"
            f"- Acceptable range: {max(10, target_words - 15)} to {target_words + 15} words\n"
            f"- Count your words carefully before finalizing\n"
            f"- If too short, expand with more detail, examples, or explanation from the text\n"
            f"- If too long, trim without losing key ideas\n"
            f"- Do NOT add new information not in the text\n"
            f"- Do NOT start with 'Summary:' or 'Here is a summary'\n\n"
            f"TEXT TO SUMMARISE:\n\"\"\"\n{text}\n\"\"\"\n\n"
            f"Write the {target_words}-word summary now:"
        )
        raw, ok = call_groq(
            [{"role": "user", "content": prompt}],
            max_tokens=max(int(target_words * 3), 512)
        )
        if ok:
            wc = len(raw.split())
            return f"### Summary ({fmt}) — ~{wc} words\n\n{raw}", "groq"
    _, summarizer, *_ = load_offline_models()
    raw = _t5_summarize(text, target_words, summarizer)
    return _apply_t5_format(raw, fmt, username), "t5"

# ---------------------- DATABASE ----------------------
DB_FILE = "studypilot.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                email    TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id       TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                messages TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id       TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                data     TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id       TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                data     TEXT NOT NULL DEFAULT '{}'
            )
        """)
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing == 0:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                ("admin", "admin@studypilot.com", hash_password("student123")),
            )

def save_data():
    try:
        username = st.session_state.get("username", "")
        if not username:
            return
        with get_conn() as conn:
            for uname, meta in st.session_state.get("user_db", {}).items():
                conn.execute(
                    """INSERT INTO users (username, email, password) VALUES (?, ?, ?)
                       ON CONFLICT(username) DO UPDATE SET
                           email=excluded.email, password=excluded.password""",
                    (uname, meta["identity"], meta["password"]),
                )
            for cid, msgs in st.session_state.get("all_chats", {}).items():
                conn.execute(
                    """INSERT INTO chats (id, username, messages) VALUES (?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET messages=excluded.messages""",
                    (cid, username, json.dumps(msgs, ensure_ascii=False)),
                )
            for sid, data in st.session_state.get("all_summaries", {}).items():
                conn.execute(
                    """INSERT INTO summaries (id, username, data) VALUES (?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET data=excluded.data""",
                    (sid, username, json.dumps(data, ensure_ascii=False)),
                )
            for pid, data in st.session_state.get("all_plans", {}).items():
                conn.execute(
                    """INSERT INTO plans (id, username, data) VALUES (?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET data=excluded.data""",
                    (pid, username, json.dumps(data, ensure_ascii=False)),
                )
    except Exception as e:
        st.toast(f"⚠️ Save warning: {e}", icon="⚠️")

def save_chat_immediately(chat_id: str, messages: list, username: str):
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO chats (id, username, messages) VALUES (?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET messages=excluded.messages""",
                (chat_id, username, json.dumps(messages, ensure_ascii=False)),
            )
    except Exception:
        pass

def delete_item_from_db(feature_key, item_id):
    table_map = {"chat": "chats", "summary": "summaries", "planner": "plans"}
    table = table_map.get(feature_key)
    if not table:
        return
    try:
        with get_conn() as conn:
            conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    except Exception:
        pass

def load_data():
    try:
        username = st.session_state.get("username", "")
        if not username:
            return
        with get_conn() as conn:
            rows = conn.execute("SELECT username, email, password FROM users").fetchall()
            st.session_state["user_db"] = {
                r["username"]: {"identity": r["email"], "password": r["password"]}
                for r in rows
            }
            rows = conn.execute(
                "SELECT id, messages FROM chats WHERE username=?", (username,)
            ).fetchall()
            st.session_state["all_chats"] = {
                r["id"]: json.loads(r["messages"]) for r in rows
            } if rows else {}
            rows = conn.execute(
                "SELECT id, data FROM summaries WHERE username=?", (username,)
            ).fetchall()
            st.session_state["all_summaries"] = {
                r["id"]: json.loads(r["data"]) for r in rows
            } if rows else {}
            rows = conn.execute(
                "SELECT id, data FROM plans WHERE username=?", (username,)
            ).fetchall()
            st.session_state["all_plans"] = {
                r["id"]: json.loads(r["data"]) for r in rows
            } if rows else {}
            if st.session_state["all_chats"]:
                st.session_state["active_chat_id"] = list(st.session_state["all_chats"].keys())[0]
            if st.session_state["all_summaries"]:
                st.session_state["active_summary_id"] = list(st.session_state["all_summaries"].keys())[0]
            if st.session_state["all_plans"]:
                st.session_state["active_planner_id"] = list(st.session_state["all_plans"].keys())[0]
    except Exception:
        pass

# ---------------------- EMAIL / AUTH HELPERS ----------------------
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
    if not st.session_state.get("otp_timestamp"):
        return True
    return (datetime.datetime.now() - st.session_state["otp_timestamp"]).seconds > 600

# ---------------------- MOTIVATIONAL ENGINE ----------------------
MOTIVATIONAL_BANK = {
    "positive": [
        "You're absolutely crushing it today! This kind of energy is exactly what separates good students from great engineers. Keep going!",
        "Your focus is top-tier right now! Every problem you solve today is building the foundation of your future career.",
        "Love the positive energy! You're in the zone — this is when the best learning happens. Don't stop now!",
        "Brilliant mindset! Consistent sessions like this compound over time into real mastery. You're on the right path.",
    ],
    "neutral": [
        "Steady focus is underrated. Most breakthroughs happen not in bursts of excitement but in quiet sessions like this one.",
        "One concept at a time, one session at a time. You're building something that will last a lifetime.",
        "Even on average days, showing up is the most powerful thing you can do. You're already ahead of most.",
        "Calm and consistent beats intense and irregular every single time. Trust the process.",
    ],
    "negative": [
        "Hey — it's okay to be tired. Even studying for 20 minutes today when you're exhausted shows real character. I've got you.",
        "Be kind to your mind right now. Rest is not the opposite of progress — it's part of it. Let's take this gently.",
        "You're here even when you don't feel like it. That's not weakness — that's discipline. Let's take it slow today.",
        "Hard days build the strongest students. Take a deep breath. We'll break this into the smallest possible steps together.",
        "I see you pushing through. That matters more than you know. Let's make even this tough session count.",
    ],
}

CHECKIN_MESSAGES = {
    "positive": "You seem to be in great spirits today! Let's channel that energy into a powerful session.",
    "neutral":  "You're in a steady, focused state. Perfect for deep learning.",
    "negative": "It sounds like you're having a tough time right now. That's completely okay — we'll build a gentler schedule for you today. You're not alone in this.",
}

def get_motivational_message(sentiment_score):
    cat   = "positive" if sentiment_score >= 0.1 else ("negative" if sentiment_score <= -0.1 else "neutral")
    opts  = MOTIVATIONAL_BANK[cat]
    avail = [m for m in opts if st.session_state["message_history"].get(m, 0) < 2] or opts
    chosen = random.choice(avail)
    st.session_state["message_history"][chosen] = st.session_state["message_history"].get(chosen, 0) + 1
    return chosen, cat, CHECKIN_MESSAGES[cat]

# ---------------------- SIDEBAR ----------------------
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
        f"<p style='font-weight:700;font-size:0.8rem;color:#64748B;text-transform:uppercase;"
        f"letter-spacing:0.08em;margin:0 0 6px 0;'>{friendly_name} History</p>",
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

    st.write("")

    if not history_dict:
        st.caption("No history yet.")
        return

    open_menu = st.session_state.get("active_menu_item_id", "")

    for item_id in list(history_dict.keys()):
        if feature_key == "chat":
            msgs  = history_dict[item_id]
            label = msgs[0]["text"][:22] + "…" if msgs else "New Chat"
        else:
            label = history_dict[item_id].get("title", "Untitled")[:22]

        is_active = item_id == active_id
        is_open   = open_menu == item_id

        col_sel, col_dot = st.columns([8, 2])

        with col_sel:
            prefix = "▸ " if is_active else ""
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
            st.markdown(
                """<div style='
                    background:#1C2333;
                    border:1px solid #2D3748;
                    border-radius:8px;
                    padding:3px 4px;
                    margin:-4px 0 4px 0;
                    box-shadow:0 6px 18px rgba(0,0,0,0.6);
                '></div>""",
                unsafe_allow_html=True,
            )
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("✏️ Rename", key=f"ren_{item_id}_{feature_key}", use_container_width=True):
                    st.session_state["editing_item_id"]       = item_id
                    st.session_state["rename_feature_target"] = feature_key
                    st.session_state["active_menu_item_id"]   = ""
                    st.rerun()
            with dc2:
                if st.button("🗑️ Delete", key=f"del_{item_id}_{feature_key}", use_container_width=True):
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
        st.write("")
        with st.form(f"rename_form_{feature_key}"):
            new_title = st.text_input("New name", placeholder="Enter title…", label_visibility="collapsed")
            if st.form_submit_button("Save →", use_container_width=True):
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


# ---------------------- MAIN APP ----------------------
def render_main_app():
    with st.sidebar:
        if st.button(f"🧑‍🎓  {st.session_state['username']}", use_container_width=True, key="profile_btn"):
            st.session_state["show_profile_tray"] = not st.session_state.get("show_profile_tray", False)
            st.rerun()

        if st.session_state.get("show_profile_tray", False):
            uid   = st.session_state["username"]
            email = st.session_state["user_db"].get(uid, {}).get("identity", "N/A")
            st.markdown(
                f"""<div style='background:#0D1117;border:1px solid #1E2533;border-radius:10px;
                padding:10px 14px;margin:4px 0 8px 0;font-size:0.88rem;line-height:2;'>
                <span style='color:#64748B;'>Username</span><br>
                <span style='color:#F1F5F9;font-weight:600;'>{uid}</span><br>
                <span style='color:#64748B;'>Email</span><br>
                <span style='color:#F1F5F9;font-weight:600;'>{email}</span>
            </div>""",
                unsafe_allow_html=True,
            )

        st.write("---")
        view = st.session_state["current_view"]
        if view == "chat":
            render_sidebar_section("chat", "Chat")
        elif view == "summary":
            render_sidebar_section("summary", "Summary")
        elif view == "planner":
            render_sidebar_section("planner", "Planner")
        else:
            st.caption("Select a module above to begin.")

        st.write("")
        if st.button("🚪  Log Out", use_container_width=True, key="logout_btn"):
            save_data()
            st.session_state["logged_in"]         = False
            st.session_state["username"]           = ""
            st.session_state["auth_view"]          = "welcome"
            st.session_state["current_view"]       = "welcome_hub"
            st.session_state["all_chats"]          = {}
            st.session_state["all_summaries"]      = {}
            st.session_state["all_plans"]          = {}
            st.session_state["active_chat_id"]     = ""
            st.session_state["active_summary_id"]  = ""
            st.session_state["active_planner_id"]  = ""
            st.session_state["nav_history_stack"]  = []
            st.rerun()

    # ── Navigation helper ──────────────────────────────────────────────────────
    # NAVBAR
    st.markdown("<div class='navbar-wrapper'>", unsafe_allow_html=True)
    n1, n2, n3, n4 = st.columns([1, 1.2, 1.2, 1.2])
    with n1:
        if st.button("🏠 Home", key="nav_home", use_container_width=True):
            st.session_state["current_view"] = "welcome_hub"
            st.rerun()
    with n2:
        if st.button("💬 Ask Anything", key="nav_chat", use_container_width=True):
            st.session_state["current_view"] = "chat"
            st.rerun()
    with n3:
        if st.button("📝 Summarize", key="nav_summary", use_container_width=True):
            st.session_state["current_view"] = "summary"
            st.rerun()
    with n4:
        if st.button("📅 Planner", key="nav_planner", use_container_width=True):
            st.session_state["current_view"] = "planner"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    tab_pos = {
        "welcome_hub": ("22%", "0%"),
        "chat":        ("25%", "24%"),
        "summary":     ("25%", "50%"),
        "planner":     ("25%", "75%"),
    }
    w, ml = tab_pos.get(st.session_state["current_view"], ("22%", "0%"))
    st.markdown(
        f"<div style='height:3px;background:#3B82F6;width:{w};margin-left:{ml};"
        f"margin-bottom:2rem;border-radius:2px;'></div>",
        unsafe_allow_html=True,
    )

    # ── HOME ──────────────────────────────────────────────────────────────────
    if st.session_state["current_view"] == "welcome_hub":
        st.markdown(
            f"<h2 style='margin-bottom:4px;'>Welcome back, {st.session_state['username']}! 👋</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:1.1rem;color:#64748B;margin-top:0;'>Ready to fly through your studies today?</p>",
            unsafe_allow_html=True,
        )

    # ── CHATBOT ───────────────────────────────────────────────────────────────
    elif st.session_state["current_view"] == "chat":
        st.markdown("### 💬 Ask your Technical Questions")

        if not st.session_state["all_chats"]:
            default_id = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state["all_chats"][default_id] = []
            st.session_state["active_chat_id"] = default_id
            save_chat_immediately(default_id, [], st.session_state["username"])
        elif not st.session_state["active_chat_id"]:
            st.session_state["active_chat_id"] = list(st.session_state["all_chats"].keys())[0]

        active_chat_id = st.session_state["active_chat_id"]
        active_chat = st.session_state["all_chats"].get(active_chat_id, [])

        for idx, msg in enumerate(active_chat):
            msg_id = f"msg_{active_chat_id}_{idx}"
            if msg["role"] == "user":
                _, cb, cd = st.columns([3.5, 6, 0.5])
                with cb:
                    st.markdown(
                        f"<div class='chat-msg user-bubble'>{msg['text']}</div>",
                        unsafe_allow_html=True,
                    )
                with cd:
                    if st.button("⋮", key=f"dots_chat_{msg_id}"):
                        st.session_state["active_bubble_menu_id"] = (
                            msg_id if st.session_state.get("active_bubble_menu_id") != msg_id else ""
                        )
                        st.rerun()
            else:
                cb, cd, _ = st.columns([6, 0.5, 3.5])
                with cb:
                    st.markdown(
                        f"<div class='chat-msg bot-bubble'>{msg['text']}</div>",
                        unsafe_allow_html=True,
                    )
                with cd:
                    if st.button("⋮", key=f"dots_chat_{msg_id}"):
                        st.session_state["active_bubble_menu_id"] = (
                            msg_id if st.session_state.get("active_bubble_menu_id") != msg_id else ""
                        )
                        st.rerun()

            if st.session_state.get("active_bubble_menu_id") == msg_id:
                if msg["role"] == "user":
                    _, mc = st.columns([7.5, 2.5])
                else:
                    mc, _ = st.columns([2.5, 7.5])
                with mc:
                    if st.button("📋  Copy", key=f"cp_{msg_id}", use_container_width=True):
                        try:
                            pyperclip.copy(msg["text"])
                        except Exception:
                            pass
                        st.toast("Copied! ✅")
                        st.session_state["active_bubble_menu_id"] = ""
                        st.rerun()
                    if st.button("↗  Share", key=f"sh_{msg_id}", use_container_width=True):
                        st.toast("Link copied!")
                        st.session_state["active_bubble_menu_id"] = ""
                        st.rerun()

        st.write("")
        with st.form("chat_form", clear_on_submit=True):
            chat_input = st.text_input(
                "", placeholder="Ask anything about Python, ML, DSA…", label_visibility="collapsed"
            )
            send = st.form_submit_button("Send →", use_container_width=True)

        if send and chat_input.strip():
            with st.spinner("Thinking..."):
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

    # ── SUMMARIZER ────────────────────────────────────────────────────────────
    elif st.session_state["current_view"] == "summary":
        st.markdown("### 📝 Notes Summarizer")

        if not st.session_state["all_summaries"]:
            st.session_state["all_summaries"]["summary_default"] = {
                "text": "", "summary": "", "word_count": 80,
                "format_style": "Plain Text", "title": "Untitled Summary",
            }
            st.session_state["active_summary_id"] = "summary_default"
            save_data()
        elif not st.session_state["active_summary_id"]:
            st.session_state["active_summary_id"] = list(st.session_state["all_summaries"].keys())[0]

        node     = st.session_state["all_summaries"].get(st.session_state["active_summary_id"])
        raw_text = st.text_area(
            "", value=node["text"], height=220,
            placeholder="Paste your lecture notes here...", label_visibility="collapsed",
        )
        if raw_text.strip():
            st.caption(f"📄 Input: {len(raw_text.split())} words")

        cc, cf = st.columns(2)
        with cc:
            target_words = st.number_input(
                "Target word count:", min_value=10, max_value=1000,
                value=int(node.get("word_count", 80)), step=10,
            )
        with cf:
            fmt_options = ["Plain Text", "Bullet Points", "Essay", "Letter", "Email"]
            fmt = st.selectbox(
                "Output format:", fmt_options,
                index=fmt_options.index(node.get("format_style", "Plain Text")),
            )

        node["text"]         = raw_text
        node["word_count"]   = target_words
        node["format_style"] = fmt

        if st.button("✨  Generate Summary", use_container_width=True, key="gen_sum_btn"):
            if len(raw_text.strip()) < 20:
                st.warning("Please paste more text first.")
            else:
                with st.spinner(f"Generating ~{target_words} word {fmt} summary..."):
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

        if node["summary"]:
            st.write("---")
            ct, cd = st.columns([9.5, 0.5])
            with ct:
                st.markdown(node["summary"])
            with cd:
                if st.button("⋮", key="dots_sum_main"):
                    st.session_state["active_bubble_menu_id"] = (
                        "sum_menu" if st.session_state.get("active_bubble_menu_id") != "sum_menu" else ""
                    )
                    st.rerun()
            if st.session_state.get("active_bubble_menu_id") == "sum_menu":
                _, mc = st.columns([7, 3])
                with mc:
                    if st.button("📋  Copy", key="cp_sum", use_container_width=True):
                        st.session_state["show_copy_summary"] = True
                        st.session_state["active_bubble_menu_id"] = ""
                        st.rerun()
                    if st.button("↗  Share", key="sh_sum", use_container_width=True):
                        st.toast("Link copied!")
                        st.session_state["active_bubble_menu_id"] = ""
                        st.rerun()

            if st.session_state.get("show_copy_summary", False):
                st.code(node.get("raw_summary", node["summary"]), language="text")
                if st.button("✕ Close", key="close_copy_sum"):
                    st.session_state["show_copy_summary"] = False
                    st.rerun()

    # ── PLANNER ───────────────────────────────────────────────────────────────
    elif st.session_state["current_view"] == "planner":
        st.markdown("### 📅 Adaptive Study Planner")
        st.caption("Your schedule adapts based on how you feel — because your wellbeing matters as much as your grades.")

        if not st.session_state["all_plans"]:
            st.session_state["all_plans"]["planner_default"] = {
                "subjects": "", "weak": "", "mood": "", "schedule": [], "title": "Untitled Plan",
            }
            st.session_state["active_planner_id"] = "planner_default"
            save_data()
        elif not st.session_state["active_planner_id"]:
            st.session_state["active_planner_id"] = list(st.session_state["all_plans"].keys())[0]

        plan = st.session_state["all_plans"].get(st.session_state["active_planner_id"])

        with st.form("planner_form"):
            c1, c2 = st.columns(2)
            with c1:
                subj       = st.text_input("Subjects (comma separated):", value=plan["subjects"],
                                           placeholder="e.g. Python, ML, DSA")
                start_time = st.time_input("Start Time:", datetime.time(9, 0))
            with c2:
                weak     = st.text_input("Your Weak Subject:", value=plan["weak"],
                                         placeholder="e.g. Python")
                end_time = st.time_input("End Time:", datetime.time(12, 0))

            mood = st.text_input("How are you feeling right now?", value=plan["mood"],
                                 placeholder="e.g. tired, stressed, excited, motivated, anxious...")
            gen  = st.form_submit_button("🗓️  Generate My Schedule", use_container_width=True)

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

        if plan.get("schedule"):
            st.write("---")
            mood_cat       = plan.get("mood_cat", "neutral")
            checkin        = plan.get("checkin", "")
            checkin_colors = {"positive": "#064E3B", "neutral": "#1E3A5F", "negative": "#3B1F1F"}
            checkin_border = {"positive": "#34D399", "neutral": "#60A5FA", "negative": "#F87171"}
            checkin_icon   = {"positive": "🌟", "neutral": "🎯", "negative": "💙"}

            st.markdown(
                f"""<div style='background:{checkin_colors[mood_cat]};border:1px solid {checkin_border[mood_cat]};
                border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>
                <span style='font-size:1.1rem;font-weight:700;color:{checkin_border[mood_cat]};'>{checkin_icon[mood_cat]} Mood Check-in</span>
                <p style='color:#E2E8F0;margin:6px 0 0;font-size:0.95rem;'>{checkin}</p>
            </div>""",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""<div style='background:#0D1117;border:1px solid #1E2533;border-left:4px solid #F59E0B;
                border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;'>
                <span style='color:#F59E0B;font-weight:700;'>✨ Your Motivation</span>
                <p style='color:#CBD5E1;margin:6px 0 0;font-size:0.95rem;font-style:italic;'>"{plan['boost']}"</p>
            </div>""",
                unsafe_allow_html=True,
            )

            mode = plan.get("mode", "classic")
            if mode == "gentle":
                st.warning("🌙 Gentle Mode: 20 min focus + 10 min recovery. You've got this, one small step at a time.")
            elif mode == "mellow":
                st.warning("🌙 Mellow Mode: 25 min focus + 10 min recovery. Taking care of yourself is part of studying.")
            else:
                st.success("⚡ Classic Mode: 25 min focus + 5 min breaks. You're sharp — let's make every session count!")

            total    = plan.get("total_minutes", 0)
            sessions = len(plan["schedule"])
            st.markdown(
                f"""<div style='display:flex;gap:12px;margin:1rem 0;'>
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
            </div>""",
                unsafe_allow_html=True,
            )

            st.markdown("#### 📋 Your Schedule")
            table_rows = ""
            for s in plan["schedule"]:
                highlight = "#1A2F1A" if s["is_weak"] else "#0D1117"
                badge = (
                    " <span style='background:#F59E0B;color:#000;font-size:0.7rem;padding:1px 6px;"
                    "border-radius:4px;font-weight:700;'>WEAK</span>"
                    if s["is_weak"] else ""
                )
                table_rows += (
                    f"<tr style='border-bottom:1px solid #1E2533;background:{highlight};'>"
                    f"<td style='padding:10px 12px;color:#64748B;font-size:0.85rem;'>#{s['session']}</td>"
                    f"<td style='padding:10px 12px;color:#60A5FA;font-weight:700;white-space:nowrap;'>{s['start']}</td>"
                    f"<td style='padding:10px 12px;color:#60A5FA;font-weight:700;white-space:nowrap;'>{s['end']}</td>"
                    f"<td style='padding:10px 12px;color:#F1F5F9;font-weight:600;'>{s['subject']}{badge}</td>"
                    f"<td style='padding:10px 12px;color:#9CA3AF;font-size:0.88rem;'>☕ {s['break_len']} min → {s['resume']}</td>"
                    f"</tr>"
                )
            st.markdown(
                f"""<div style='overflow-x:auto;border-radius:12px;border:1px solid #1E2533;margin-top:0.5rem;'>
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
            </div>""",
                unsafe_allow_html=True,
            )

            if mood_cat == "negative":
                st.markdown(
                    """<div style='background:#1A0F0F;border:1px solid #7F1D1D;border-radius:12px;padding:1rem 1.25rem;margin-top:1rem;'>
                    <span style='color:#F87171;font-weight:700;'>💙 A Note For You</span>
                    <p style='color:#FCA5A5;margin:6px 0 0;font-size:0.9rem;'>
                    Remember — it's okay to not be okay. If at any point you feel overwhelmed,
                    step away from studying. Your mental health always comes first.
                    Even completing just one session today is a win. I'm proud of you for showing up. 🤍
                    </p>
                </div>""",
                    unsafe_allow_html=True,
                )


# ---------------------- AUTH ----------------------
def render_login_page():
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown(
            """<div style='text-align:center;margin:2rem 0 1.5rem;'>
            <div style='font-size:3rem;'>✈️</div>
            <h1 style='font-weight:900;font-size:2.4rem;margin:0;letter-spacing:-1px;'>StudyPilot</h1>
            <p style='color:#6B7280;font-size:0.95rem;margin:6px 0 0;'>Your Learning Assistant</p>
        </div>""",
            unsafe_allow_html=True,
        )

        if st.session_state["auth_view"] == "welcome":
            st.write("")
            if st.button("🔐  Sign In", use_container_width=True):
                st.session_state["auth_view"] = "login"
                st.rerun()
            st.write("")
            if st.button("📝  Create Account", use_container_width=True):
                st.session_state["auth_view"] = "register"
                st.session_state["reg_step"]  = "input_email"
                st.rerun()

        elif st.session_state["auth_view"] == "login":
            st.markdown("### Sign In")
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
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password.")
                except Exception:
                    st.error("❌ Database error. Please try again.")
            cl, cr = st.columns(2)
            with cl:
                if st.button("⬅ Back", key="back_login", use_container_width=True):
                    st.session_state["auth_view"] = "welcome"
                    st.rerun()
            with cr:
                if st.button("Forgot Password?", key="forgot_btn", use_container_width=True):
                    st.session_state["auth_view"]   = "forgot_password"
                    st.session_state["forgot_step"] = "verify_email"
                    st.rerun()

        elif st.session_state["auth_view"] == "register":
            st.markdown("### Create Account")
            if st.session_state["reg_step"] == "input_email":
                with st.form("reg_email_form"):
                    ei   = st.text_input("Your Email Address", placeholder="name@gmail.com")
                    send = st.form_submit_button("Send Verification Code →", use_container_width=True)
                if send:
                    if not validate_email(ei.strip()):
                        st.error("❌ Enter a valid email.")
                    else:
                        # ── ONE ACCOUNT PER EMAIL CHECK ──
                        existing_emails = [m["identity"] for m in st.session_state["user_db"].values()]
                        if ei.strip() in existing_emails:
                            st.error("❌ An account with this email already exists. Please sign in instead.")
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
                                st.success(f"✅ OTP sent to {ei.strip()}!")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed: {err}")
                if st.button("⬅ Cancel", use_container_width=True):
                    st.session_state["auth_view"] = "welcome"
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
                            st.error("❌ Incorrect OTP.")
                    if st.button("⬅ Back", key="back_otp"):
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
                        st.error("❌ Username too short.")
                    elif ru.strip() in st.session_state["user_db"]:
                        st.error("❌ Username taken.")
                    elif st.session_state["temp_identity"] in existing_emails:
                        st.error("❌ An account with this email already exists. Please sign in instead.")
                    elif rp != rc:
                        st.error("❌ Passwords don't match.")
                    elif len(rp) < 4:
                        st.error("❌ Password too short.")
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
                        st.rerun()

        elif st.session_state["auth_view"] == "forgot_password":
            st.markdown("### Reset Password")
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
                            st.success("✅ OTP sent!")
                            st.rerun()
                        else:
                            st.error(f"❌ {err}")
                    else:
                        st.error("❌ No account found.")
                if st.button("⬅ Back", key="back_forgot", use_container_width=True):
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
                            st.error("❌ Incorrect OTP.")
                else:
                    st.error("⏰ OTP expired.")

            elif st.session_state["forgot_step"] == "reset_password":
                with st.form("reset_form"):
                    np1  = st.text_input("New Password", type="password")
                    np2  = st.text_input("Confirm", type="password")
                    save = st.form_submit_button("Update Password →", use_container_width=True)
                if save:
                    if np1 != np2:
                        st.error("❌ Don't match.")
                    elif len(np1) < 4:
                        st.error("❌ Too short.")
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
                        st.success("🔒 Updated! Sign in now.")
                        st.session_state["auth_view"] = "login"
                        st.rerun()


# ---------------------- ENTRY POINT ----------------------
st.set_page_config(page_title="StudyPilot", page_icon="✈️", layout="wide")

init_db()
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

.chat-msg {
    padding:0.85rem 1.25rem;
    border-radius:16px;
    font-size:0.95rem;
    line-height:1.6;
    word-wrap:break-word !important;
    overflow-wrap:break-word !important;
}
.user-bubble {
    background:linear-gradient(135deg,#1D4ED8,#2563EB) !important;
    color:#fff !important;
    border-bottom-right-radius:2px !important;
}
.bot-bubble {
    background:#0D1117 !important;
    color:#E2E8F0 !important;
    border-bottom-left-radius:2px !important;
    border:1px solid #1E2533 !important;
}
.bot-bubble p  { color:#E2E8F0 !important; margin:0.3rem 0 !important; }
.bot-bubble strong { color:#93C5FD !important; font-weight:700 !important; }
.bot-bubble em { color:#C4B5FD !important; }
.bot-bubble h1,.bot-bubble h2,.bot-bubble h3,.bot-bubble h4 { color:#60A5FA !important; margin:0.5rem 0 0.2rem !important; }
.bot-bubble ul, .bot-bubble ol { padding-left:1.3rem !important; margin:0.3rem 0 !important; }
.bot-bubble li { color:#E2E8F0 !important; margin:0.2rem 0 !important; }
.bot-bubble code { background:#1E2533 !important; color:#34D399 !important; padding:1px 5px !important; border-radius:4px !important; font-size:0.88em !important; }
.bot-bubble pre { background:#0A0F1A !important; border:1px solid #1E2533 !important; border-radius:8px !important; padding:0.6rem 1rem !important; overflow-x:auto !important; margin:0.4rem 0 !important; }
.bot-bubble pre code { background:transparent !important; color:#86EFAC !important; padding:0 !important; }
.bot-bubble blockquote { border-left:3px solid #3B82F6 !important; background:#111827 !important; padding:0.4rem 0.8rem !important; border-radius:0 6px 6px 0 !important; margin:0.4rem 0 !important; color:#93C5FD !important; }

.navbar-wrapper { padding:0.2rem; margin-bottom:0.5rem; }
.navbar-wrapper button { background:#0D1117 !important; border:1px solid #1E2533 !important; color:#94A3B8 !important; font-weight:600 !important; }
.navbar-wrapper button:hover { background:#1E2533 !important; color:#F1F5F9 !important; }

.stButton>button {
    background:#0D1117 !important; color:#CBD5E1 !important;
    border-radius:10px !important; border:1px solid #1E2533 !important;
    font-weight:600 !important; height:2.4em !important;
    transition:all 0.15s !important;
}
.stButton>button:hover { background:#2563EB !important; color:#fff !important; border-color:#2563EB !important; }

button[key="nav_back"] {
    background:#0D1117 !important;
    border:1px solid #1E2533 !important;
    color:#60A5FA !important;
    font-weight:700 !important;
    font-size:0.9rem !important;
    border-radius:10px !important;
}
button[key="nav_back"]:hover {
    background:#1E2533 !important;
    color:#93C5FD !important;
    border-color:#3B82F6 !important;
}

button[key="profile_btn"] { color:#60A5FA !important; font-weight:700 !important; text-align:left !important; }
button[key="logout_btn"] { color:#F87171 !important; border-color:#3B1F1F !important; background:#1A0F0F !important; }
button[key="logout_btn"]:hover { background:#DC2626 !important; color:#fff !important; border-color:#DC2626 !important; }

button[key^="sel_"] {
    background:transparent !important;
    border:none !important;
    color:#CBD5E1 !important;
    font-size:0.82rem !important;
    font-weight:400 !important;
    height:2em !important;
    min-height:0 !important;
    padding:4px 8px !important;
    text-align:left !important;
    justify-content:flex-start !important;
    box-shadow:none !important;
    border-radius:7px !important;
}
button[key^="sel_"]:hover { background:#1E2533 !important; color:#F1F5F9 !important; }

button[key^="dots_"] {
    background:transparent !important; color:#475569 !important;
    border:none !important; font-size:1.1rem !important;
    height:2em !important; padding:0 4px !important;
    box-shadow:none !important; min-height:0 !important;
}
button[key^="dots_"]:hover { color:#94A3B8 !important; background:#1E2533 !important; border-radius:5px !important; }

button[key^="ren_"] {
    background:#1C2333 !important; border:1px solid #2D3748 !important;
    color:#CBD5E1 !important; font-size:0.75rem !important;
    height:1.6em !important; min-height:0 !important;
    border-radius:6px !important; font-weight:500 !important;
    padding:0 6px !important; box-shadow:none !important;
}
button[key^="ren_"]:hover { background:#1E2D45 !important; color:#60A5FA !important; border-color:#3B82F6 !important; }

button[key^="del_"] {
    background:#1C2333 !important; border:1px solid #2D3748 !important;
    color:#F87171 !important; font-size:0.75rem !important;
    height:1.6em !important; min-height:0 !important;
    border-radius:6px !important; font-weight:500 !important;
    padding:0 6px !important; box-shadow:none !important;
}
button[key^="del_"]:hover { background:#3B1F1F !important; color:#FCA5A5 !important; border-color:#7F1D1D !important; }

button[key^="cp_"], button[key^="sh_"] {
    background:#1C2333 !important; border:1px solid #2D3748 !important;
    color:#CBD5E1 !important; font-size:0.8rem !important;
    height:1.8em !important; min-height:0 !important;
    border-radius:6px !important; font-weight:500 !important;
    padding:0 10px !important; box-shadow:0 4px 16px rgba(0,0,0,0.5) !important;
    margin-bottom:2px !important;
}
button[key^="cp_"]:hover, button[key^="sh_"]:hover { background:#2563EB !important; color:#fff !important; border-color:#2563EB !important; }

button[key^="new_"] {
    background:#0F1E38 !important; color:#60A5FA !important;
    border:1px dashed #3B82F6 !important; font-weight:700 !important;
    font-size:0.82rem !important; height:2em !important;
}
button[key^="new_"]:hover { background:#2563EB !important; color:#fff !important; border-color:#2563EB !important; border-style:solid !important; }

[data-testid="stForm"] { border:none !important; background:transparent !important; padding:0 !important; }
.stAlert { border-radius:10px !important; }
</style>""", unsafe_allow_html=True)

defaults = {
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

if st.session_state["logged_in"]:
    render_main_app()
else:
    render_login_page()