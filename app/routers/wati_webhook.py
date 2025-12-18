import re
import os
import time
import httpx
import asyncio
import logging
import traceback
from dotenv import load_dotenv
from datetime import datetime, timezone
from sqlalchemy.exc import OperationalError
from fastapi.responses import PlainTextResponse
from fastapi import APIRouter, Request, BackgroundTasks

from app.database import SessionLocal
from app.agent.booking_agent import BookingToolAgent
from app.email.email_service import send_new_chat_email
from app.chatbot.models import Session as SessionModel, Message

# Load environment variables
load_dotenv()

router = APIRouter()
agent = BookingToolAgent()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
WHATSAPP_API_VERSION = "v19.0"


def formatting(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    text = re.sub(r"<[^>]*>", "", text)
    return text


def db_operation_with_retry(operation_func, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return operation_func()
        except OperationalError as e:
            error_msg = str(e).lower()
            if (
                "ssl connection has been closed" in error_msg
                or "connection" in error_msg
            ) and attempt < max_retries - 1:
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{max_retries}), retrying in {delay} seconds..."
                )
                time.sleep(delay)
                delay *= 2  # Exponential backoff
                continue
            else:
                logger.error(
                    f"Database operation failed after {max_retries} attempts: {e}"
                )
                raise e
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise e


@router.get("/meta-webhook")
def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Invalid token", status_code=403)


async def background_whatsapp_flow(message: dict):
    db = None
    try:
        session_id = message["from"]
        text = message["text"]["body"]

        # 1️⃣ Typing indicator
        try:
            await send_typing_indicator(message["id"])
        except Exception as e:
            logger.warning(f"Failed to send typing indicator: {e}")

        # 2️⃣ Create DB session
        def create_db_session():
            return SessionLocal()

        db = db_operation_with_retry(create_db_session)

        # 3️⃣ Get or create session
        def get_or_create_session():
            session = db.query(SessionModel).filter_by(id=session_id).first()
            if not session:
                session = SessionModel(id=session_id, whatsapp_number=session_id)
                db.add(session)
                db.commit()
            return session

        session = db_operation_with_retry(get_or_create_session)

        # 4️⃣ Save user message
        def save_user_message():
            user_message = Message(
                session_id=session_id,
                sender="user",
                content=text,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(user_message)
            db.commit()
            return user_message

        db_operation_with_retry(save_user_message)

        # 5️⃣ Get bot response
        response = agent.get_response(incoming_text=text, session_id=session_id)
        formatted_response = formatting(response)

        # 6️⃣ Save bot response
        def save_bot_message():
            bot_message = Message(
                sender="bot",
                session_id=session_id,
                content=formatted_response,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(bot_message)
            db.commit()
            return bot_message

        db_operation_with_retry(save_bot_message)
        logger.info(f"Bot response for {session_id} saved to DB.")

        # 7️⃣ Send new chat email
        send_new_chat_email(session, text, db)
        logger.info(f"New chat email sent for session {session_id}.")

        # 8️⃣ Send WhatsApp message
        try:
            await send_whatsapp_message(session_id, formatted_response)
            logger.info(f"Bot reply to {session_id}: {formatted_response}")
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")

    except Exception as e:
        logger.error(f"Unexpected error in background flow: {e}")
        traceback.print_exc()
        if "session_id" in locals():
            try:
                await send_whatsapp_message(
                    session_id, "Sorry, something went wrong. Please try again."
                )
            except:
                pass
    finally:
        if db:
            try:
                db.close()
            except:
                logger.warning("Failed to close database session")


@router.post("/meta-webhook")
async def receive_message(request: Request):
    try:
        data = await request.json()
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages")

        if not messages:
            return {"status": "ignored"}

        if "text" not in messages[0]:
            return {"status": "ignored"}

        message = messages[0]

        logger.info(f"Incoming message: {message['from']} -> {message['text']['body']}")

        # Schedule the full background flow
        asyncio.create_task(background_whatsapp_flow(message))

    except Exception as e:
        logger.error(f"❌ Exception in webhook: {e}")
        traceback.print_exc()
        return {"status": "error"}

    # Immediately return 200 OK to WhatsApp
    return {"status": "ok"}


async def send_whatsapp_message(recipient_number: str, message: str):
    url = (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    )
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "text",
        "text": {"body": message},
    }

    try:
        logger.info(f"Sending WhatsApp message to {recipient_number}")
        async with httpx.AsyncClient(timeout=30.0) as client:  # Increased timeout
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"❌ WhatsApp send failed: {response.text}")
            else:
                logger.info(f"✅ Message sent successfully to {recipient_number}")
    except httpx.RequestError as e:
        logger.error(f"❌ Network error while sending message: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error while sending message: {e}")


async def send_typing_indicator(message_id: str):
    url = (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    )
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {"type": "text"},
    }

    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)
