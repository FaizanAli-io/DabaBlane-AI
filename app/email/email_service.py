import os
import asyncio
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.chatbot.models import Session


def send_email(user_number: str, user_message: str):
    gmail_host = "smtp.gmail.com"
    gmail_user = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_PASSWORD")

    if not gmail_user or not gmail_password:
        raise RuntimeError("GMAIL_ADDRESS or GMAIL_PASSWORD not set")

    subject = "New Message to DabaBlane-AI Chatbot"
    message = f"You have received a new message to DabaBlane-AI Chatbot!\n\nFrom: {user_number}\n\nMessage: {user_message}"

    msg = EmailMessage()
    msg["To"] = gmail_user
    msg["From"] = gmail_user
    msg["Subject"] = subject
    msg.set_content(message)

    with smtplib.SMTP(gmail_host, 587, timeout=15) as server:
        server.starttls()

        server.login(gmail_user, gmail_password)
        server.send_message(msg)


def send_new_chat_email_sync(session_id, user_message):
    db = SessionLocal()

    try:
        session = db.query(Session).filter_by(id=session_id).first()
        if not session:
            return

        current_time = datetime.utcnow()
        last_interaction = session.last_interaction

        should_send = (
            last_interaction is None
            or current_time - last_interaction > timedelta(hours=0)
        )

        if should_send:
            send_email(session.whatsapp_number, user_message)
            session.last_interaction = current_time
            db.commit()

    finally:
        db.close()


async def send_new_chat_email_async(session_id: str, user_message: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        send_new_chat_email_sync,
        session_id,
        user_message,
    )
