import os
import asyncio
import logging
import requests
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.chatbot.models import Session

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def send_email(user_number: str, user_message: str):
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("BREVO_FROM_EMAIL")

    if not api_key or not from_email:
        raise RuntimeError("BREVO_API_KEY or BREVO_FROM_EMAIL not set")

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {"api-key": api_key, "Content-Type": "application/json"}

    data = {
        "subject": "New Message to DabaBlane-AI Chatbot",
        "sender": {"email": from_email, "name": "DabaBlane AI"},
        "to": [{"email": from_email, "name": "DabaBlane Admin"}],
        "textContent": f"You have received a new message to DabaBlane-AI Chatbot!\n\nFrom: {user_number}\n\nMessage: {user_message}",
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)

        if response.status_code == 201:
            logger.info("[EMAIL SERVICE] Email sent via Brevo API")
        else:
            logger.error(f"[EMAIL SERVICE] Brevo failed: {response.text}")

    except Exception as e:
        logger.error(f"[EMAIL SERVICE] Error: {e}")


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
