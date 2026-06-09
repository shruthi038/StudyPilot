import os
import json
from utils.constants import THEME_FILE

def get_user_theme(username):
    if not username:
        return "light"
    if os.path.exists(THEME_FILE):
        try:
            with open(THEME_FILE, "r") as f:
                prefs = json.load(f)
                return prefs.get(username, "light")
        except Exception:
            pass
    return "light"

def save_user_theme(username, theme):
    if not username:
        return
    prefs = {}
    if os.path.exists(THEME_FILE):
        try:
            with open(THEME_FILE, "r") as f:
                prefs = json.load(f)
        except Exception:
            pass
    prefs[username] = theme
    try:
        with open(THEME_FILE, "w") as f:
            json.dump(prefs, f)
    except Exception:
        pass

def get_theme_css(theme="light"):
    if theme == "light":
        return """
        :root {
            --bg-primary:    #EEF2F7;
            --bg-secondary:  #E2E8F0;
            --bg-card:       #FFFFFF;
            --text-primary:  #0A0F1E;
            --text-secondary:#1E293B;
            --text-muted:    #64748B;
            --border:        #CBD5E1;
            --accent:        #4338CA;
            --accent-hover:  #3730A3;
            --accent-light:  rgba(67,56,202,0.06);
            --accent-gradient: linear-gradient(135deg,#4338CA,#6D28D9);
            --shadow-sm:  0 1px 2px rgba(0,0,0,0.04);
            --shadow-md:  0 4px 12px rgba(0,0,0,0.06);
            --shadow-lg:  0 12px 32px rgba(0,0,0,0.08);
            --radius-sm:  8px;
            --radius-md:  12px;
            --radius-lg:  16px;
            --sidebar-bg: #FFFFFF;
            --sidebar-border: #CBD5E1;
            --navbar-bg:  rgba(238,242,247,0.95);
        }
        /* Light mode specific sidebar button styling */
        section[data-testid="stSidebar"] .stButton > button {
            color: #1E293B !important;
            font-weight: 600 !important;
        }
        """
    else:
        return """
        :root {
            --bg-primary:    #0B1120;
            --bg-secondary:  #1E293B;
            --bg-card:       #151D2E;
            --text-primary:  #F1F5F9;
            --text-secondary:#94A3B8;
            --text-muted:    #64748B;
            --border:        rgba(255,255,255,0.15);
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
        }
        /* Dark mode specific button enhancements */
        .stButton > button,
        [data-testid="stPopover"] > button {
            border: 1px solid rgba(255,255,255,0.15) !important;
            color: var(--text-primary) !important;
            background: rgba(255,255,255,0.06) !important;
        }
        .stButton > button:hover,
        [data-testid="stPopover"] > button:hover {
            background: var(--accent) !important;
            color: #FFFFFF !important;
            border-color: var(--accent) !important;
        }
        """
