import datetime
import streamlit as st
import pyperclip
from controllers.chat_controller import init_chat_state, send_message

def render_chat_view():
    init_chat_state()

    active_chat_id = st.session_state["active_chat_id"]
    active_chat    = st.session_state["all_chats"].get(active_chat_id, [])

    # Handle suggestion chip auto-send
    prefill = st.session_state.pop("_chat_prefill", None)
    if prefill:
        with st.spinner("Thinking…"):
            send_message(active_chat_id, prefill)
        st.rerun()

    # ── Empty state with suggestion chips ──
    if not active_chat:
        from utils.helpers import get_base64_logo
        theme = st.session_state.get("theme", "light")
        logo_b64 = get_base64_logo(theme)
        img_html = f"<img src='data:image/png;base64,{logo_b64}' style='height: 64px; margin-bottom: 1rem; opacity: 0.9;'>" if logo_b64 else ""
        st.markdown(
            f"""<div class='chat-empty'>
                <div style='text-align:center;'>{img_html}</div>
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
                with st.chat_message("assistant"):
                    st.markdown(msg['text'])
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
            send_message(active_chat_id, chat_input.strip())
        st.rerun()
