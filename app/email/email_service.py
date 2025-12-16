import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta


def send_email(user_number: str, user_message: str):
    gmail_user = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        raise RuntimeError("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set")

    subject = "New Message to DabaBlane-AI Chatbot"
    message = "You have received a new message to DabaBlane-AI Chatbot!\n\n"
    message += f"From: {user_number}\n\nMessage:{user_message}"

    msg = EmailMessage()
    msg["To"] = gmail_user
    msg["From"] = gmail_user
    msg["Subject"] = subject
    msg.set_content(message)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)


def send_new_chat_email(session, user_message, db):
    current_time = datetime.utcnow()
    last_interaction = session.last_interaction

    should_send = (
        last_interaction is None
        or current_time - last_interaction > timedelta(hours=24)
    )

    if should_send:
        send_email(session.whatsapp_number, user_message)
        session.last_interaction = current_time
        db.commit()
