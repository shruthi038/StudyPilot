import streamlit as st
import datetime
from models.chat_model import upsert_chat, delete_chat
from services.chatbot import get_chat_response

def init_chat_state():
    if not st.session_state.get("all_chats"):
        default_id = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state["all_chats"] = {default_id: []}
        st.session_state["active_chat_id"] = default_id
        save_current_chat(default_id, [])
    elif not st.session_state.get("active_chat_id"):
        st.session_state["active_chat_id"] = list(st.session_state["all_chats"].keys())[0]

def send_message(chat_id: str, message: str):
    active_chat = st.session_state["all_chats"].get(chat_id, [])
    
    ans, sentiment = get_chat_response(message, active_chat)
    
    if sentiment["compound"] >= 0.05:
        st.toast("Positive vibes! 😊")
    elif sentiment["compound"] <= -0.05:
        st.toast("You seem stressed. Take it easy! 💙")
        
    active_chat.append({"role": "user", "text": message})
    active_chat.append({"role": "assistant", "text": ans})
    
    st.session_state["all_chats"][chat_id] = active_chat
    save_current_chat(chat_id, active_chat)

def save_current_chat(chat_id: str, messages: list):
    username = st.session_state.get("username")
    if username:
        upsert_chat(chat_id, username, messages)

def remove_chat(chat_id: str):
    username = st.session_state.get("username")
    if username:
        delete_chat(chat_id)
    if chat_id in st.session_state.get("all_chats", {}):
        del st.session_state["all_chats"][chat_id]
