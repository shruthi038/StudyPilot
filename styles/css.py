import os
import streamlit as st
from styles.theme import get_theme_css

def inject_css(theme="light"):
    theme_vars = get_theme_css(theme)
    st.markdown(f"<style>{theme_vars}</style>", unsafe_allow_html=True)

    # Sidebar visibility control
    sidebar_open = st.session_state.get("sidebar_open", True)
    toggle_left = "210px" if sidebar_open else "12px"

    if not sidebar_open:
        st.markdown("""<style>
        section[data-testid="stSidebar"] {
            transform: translateX(-110%) !important;
        }
        /* When sidebar hidden, let main content use full width */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
        }
        </style>""", unsafe_allow_html=True)
    else:
        st.markdown("""<style>
        section[data-testid="stSidebar"] {
            transform: translateX(0) !important;
        }
        </style>""", unsafe_allow_html=True)

    st.markdown(f"""<style>
    /* Fixed nav toggle button positioning */
    .main [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:first-child button {{
        position: fixed !important;
        top: 12px !important;
        left: {toggle_left} !important;
        z-index: 9999 !important;
        transition: left 0.28s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    </style>""", unsafe_allow_html=True)

    # Load static style.css
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                static_css = f.read()
            st.markdown(f"<style>{static_css}</style>", unsafe_allow_html=True)
        except Exception:
            pass
