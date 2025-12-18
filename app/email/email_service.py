import os
import asyncio
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.chatbot.models import Session


def send_email(user_number: str, user_message: str):
    brevo_host = "smtp-relay.brevo.com"
    brevo_user = os.getenv("BREVO_SMTP_USER")
    brevo_password = os.getenv("BREVO_SMTP_PASSWORD")

    if not brevo_user or not brevo_password:
        raise RuntimeError("BREVO_SMTP_USER or BREVO_SMTP_PASSWORD not set")

    subject = "New Message to DabaBlane-AI Chatbot"
    message = f"You have received a new message to DabaBlane-AI Chatbot!\n\nFrom: {user_number}\n\nMessage: {user_message}"

    msg = EmailMessage()
    msg["To"] = brevo_user
    msg["From"] = brevo_user
    msg["Subject"] = subject
    msg.set_content(message)

    with smtplib.SMTP_SSL(brevo_host, 465, timeout=30) as server:
        server.login(brevo_user, brevo_password)
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
            or current_time - last_interaction > timedelta(hours=24)
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
