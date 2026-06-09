import os
from dotenv import load_dotenv

load_dotenv()

THEME_FILE = "theme_preferences.json"
DB_FILE = "studypilot.db"

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

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
