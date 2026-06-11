import random
import datetime
from services.chatbot import get_sia
from utils.constants import MOTIVATIONAL_BANK, CHECKIN_MESSAGES

def get_motivational_message(sentiment_score, msg_history):
    cat   = "positive" if sentiment_score >= 0.1 else ("negative" if sentiment_score <= -0.1 else "neutral")
    opts  = MOTIVATIONAL_BANK[cat]
    avail = [m for m in opts if msg_history.get(m, 0) < 2] or opts
    chosen = random.choice(avail)
    msg_history[chosen] = msg_history.get(chosen, 0) + 1
    return chosen, cat, CHECKIN_MESSAGES[cat], msg_history

def generate_schedule(subj, weak, mood, start_time, end_time, plan, msg_history):
    slist = [s.strip() for s in subj.split(",") if s.strip()]
    if not slist:
        raise ValueError("Please enter at least one subject.")
    if end_time <= start_time:
        raise ValueError("End time must be after start time.")

    sia        = get_sia()
    mood_score = sia.polarity_scores(mood)["compound"]
    boost, mood_cat, checkin, updated_history = get_motivational_message(mood_score, msg_history)
    plan.update({"subjects": subj, "weak": weak, "mood": mood})
    if plan.get("title", "Untitled Plan").startswith("Untitled") and slist:
        plan["title"] = f"Plan: {slist[0]}"

    start_dt      = datetime.datetime.combine(datetime.date.today(), start_time)
    end_dt        = datetime.datetime.combine(datetime.date.today(), end_time)
    total_minutes = int((end_dt - start_dt).total_seconds() / 60)

    if mood_score <= -0.3:   work_mins, break_mins, mode = 20, 10, "gentle"
    elif mood_score <= -0.1: work_mins, break_mins, mode = 25, 10, "mellow"
    else:                    work_mins, break_mins, mode = 25, 5,  "classic"

    weighted = []
    for s in slist:
        weighted.append(s)
        if s.lower() == weak.strip().lower():
            weighted.append(s)

    schedule, t, i, session_num = [], start_dt, 0, 1
    while t < end_dt:
        remaining = int((end_dt - t).total_seconds() / 60)
        if remaining < work_mins: break
        sub         = weighted[i % len(weighted)]
        actual_work = min(work_mins, remaining)
        end_session = t + datetime.timedelta(minutes=actual_work)
        actual_break = min(break_mins, int((end_dt - end_session).total_seconds() / 60))
        resume_at   = end_session + datetime.timedelta(minutes=actual_break)
        schedule.append({
            "session": session_num,
            "start":   t.strftime("%I:%M %p"),
            "end":     end_session.strftime("%I:%M %p"),
            "subject": sub,
            "is_weak": sub.lower() == weak.strip().lower(),
            "break_len": actual_break,
            "resume":  resume_at.strftime("%I:%M %p"),
            "mode":    mode,
        })
        t = resume_at
        i += 1
        session_num += 1

    plan.update({
        "schedule": schedule, "boost": boost, "checkin": checkin,
        "mood_cat": mood_cat, "mode": mode, "total_minutes": total_minutes,
    })
    return plan, updated_history
