import re
import difflib
import requests
import nltk
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.constants import GROQ_API_KEY, GROQ_MODEL, GROQ_URL

_GROQ_EXHAUSTED = False

def _groq_available() -> bool:
    global _GROQ_EXHAUSTED
    return bool(GROQ_API_KEY) and not _GROQ_EXHAUSTED

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
            global _GROQ_EXHAUSTED
            _GROQ_EXHAUSTED = True
        return "", False
    except Exception:
        return "", False

import functools

@functools.lru_cache(maxsize=1)
def load_offline_models():
    nltk.download("vader_lexicon", quiet=True)
    nltk.download("punkt",         quiet=True)
    nltk.download("punkt_tab",     quiet=True)
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    sia        = SentimentIntensityAnalyzer()
    from transformers import pipeline
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

def get_chat_response(user_query: str, chat_history: list) -> tuple[str, dict]:
    sia, _, df, vectorizer, tfidf_matrix = load_offline_models()
    sentiment = sia.polarity_scores(user_query)
    if _groq_available():
        messages = [
            {"role": "system", "content": (
                "You are StudyPilot's tutor for students studying Python, Machine Learning, "
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
