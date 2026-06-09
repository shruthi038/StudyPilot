import datetime
import streamlit as st
import pyperclip
from services.chatbot import get_chat_response
from database.database import save_chat_immediately

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
