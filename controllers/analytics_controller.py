import streamlit as st

def get_analytics_data():
    total_chats     = len(st.session_state.get("all_chats",     {}))
    total_summaries = len(st.session_state.get("all_summaries", {}))
    total_plans     = len(st.session_state.get("all_plans",     {}))
    total_minutes   = sum(p.get("total_minutes", 0) for p in st.session_state.get("all_plans", {}).values())
    modes = {"classic": 0, "mellow": 0, "gentle": 0}
    moods = {"positive": 0, "neutral": 0, "negative": 0}
    for plan in st.session_state.get("all_plans", {}).values():
        modes[plan.get("mode", "classic")] = modes.get(plan.get("mode", "classic"), 0) + 1
        moods[plan.get("mood_cat", "neutral")] = moods.get(plan.get("mood_cat", "neutral"), 0) + 1
    return {
        "chats": total_chats,
        "summaries": total_summaries,
        "plans": total_plans,
        "minutes": total_minutes,
        "modes": modes,
        "moods": moods
    }
