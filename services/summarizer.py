import re
import datetime
import nltk
import streamlit as st
from services.chatbot import _groq_available, call_groq, load_offline_models

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
