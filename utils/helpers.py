import re
import datetime
import hashlib
import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.constants import GMAIL_ADDRESS, GMAIL_APP_PASSWORD

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))

def get_time_greeting():
    h = datetime.datetime.now().hour
    return "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")

def is_otp_expired():
    if not st.session_state.get("otp_timestamp"):
        return True
    return (datetime.datetime.now() - st.session_state["otp_timestamp"]).seconds > 600

def send_otp_email(recipient_email, otp_code):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "StudyPilot — Your Verification Code"
        msg["From"] = f"StudyPilot <{GMAIL_ADDRESS}>"
        msg["To"] = recipient_email
        html_body = f"""<html><body style="margin:0;padding:0;background:#0B0F19;font-family:'Segoe UI',sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#0B0F19;padding:40px 0;">
                <tr><td align="center">
                    <table width="480" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:16px;overflow:hidden;border:1px solid #1F2937;">
                        <tr><td style="background:linear-gradient(135deg,#1D4ED8,#2563EB);padding:32px;text-align:center;">
                            <h1 style="margin:0;color:#fff;font-size:26px;font-weight:800;">✈️ StudyPilot</h1>
                            <p style="margin:6px 0 0;color:#BFDBFE;font-size:13px;">Your Learning Assistant</p>
                        </td></tr>
                        <tr><td style="padding:36px 40px;">
                            <p style="color:#9CA3AF;font-size:14px;margin:0 0 8px;">Your verification code is:</p>
                            <div style="background:#0B0F19;border:1px solid #374151;border-radius:12px;padding:24px;text-align:center;margin:16px 0;">
                                <span style="font-size:42px;font-weight:900;color:#60A5FA;letter-spacing:10px;">{otp_code}</span>
                            </div>
                            <p style="color:#6B7280;font-size:13px;margin:16px 0 0;">Expires in <b style="color:#F59E0B;">10 minutes</b>. Do not share it.</p>
                        </td></tr>
                        <tr><td style="padding:20px 40px;border-top:1px solid #1F2937;">
                            <p style="color:#4B5563;font-size:12px;margin:0;text-align:center;">If you didn't request this, ignore this email.</p>
                        </td></tr>
                    </table>
                </td></tr>
            </table>
        </body></html>"""
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)
