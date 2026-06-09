import datetime
import streamlit as st
from services.summarizer import get_summary
from database.database import save_data

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
