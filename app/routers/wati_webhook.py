# from fastapi import APIRouter, Request
# import os
# import httpx
# from dotenv import load_dotenv
# from datetime import datetime
# from app.agent.booking_agent import BookingToolAgent
# from app.database import SessionLocal
# from app.chatbot.models import Session as SessionModel, Message
# from fastapi.responses import PlainTextResponse
# from app.format_message import formatting
# load_dotenv()

# router = APIRouter()
# agent = BookingToolAgent()

# VERIFY_TOKEN = "my_custom_secret_token"
# WHATSAPP_TOKEN = os.getenv("META_ACCESS_TOKEN")
# PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")




# @router.get("/meta-webhook")
# def verify_webhook(request: Request):
#     params = request.query_params
#     if params.get("hub.verify_token") == VERIFY_TOKEN:
#         return PlainTextResponse(params.get("hub.challenge"))
#     return PlainTextResponse("Invalid token", status_code=403)



# @router.post("/meta-webhook")
# async def receive_message(request: Request):
#     data = await request.json()
#     print("📩 Incoming:", data)

#     db = SessionLocal()
#     try:
#         entry = data["entry"][0]
#         changes = entry["changes"][0]
#         value = changes["value"]
#         messages = value.get("messages")

#         if not messages:
#             return {"status": "ignored"}

#         wa_id = messages[0]["from"]
#         text = messages[0]["text"]["body"]
#         session_id = wa_id

#         # --- Check for existing session ---
#         session = db.query(SessionModel).filter_by(id=session_id).first()

#         if not session:
#             session = SessionModel(
#                 id=session_id,
#                 whatsapp_number=wa_id
#             )
#             db.add(session)
#             db.commit()

#         # --- Save user message ---
#         db.add(Message(
#             session_id=session_id,
#             sender="user",
#             content=text,
#             timestamp=datetime.utcnow()
#         ))
#         db.commit()

#         # --- Get bot reply ---
#         response = agent.get_response(incoming_text=text, session_id=session_id)
        
#         # formatted response
#         response = formatting(response)

#         # --- Save bot response ---
#         db.add(Message(
#             session_id=session_id,
#             sender="bot",
#             content=response,
#             timestamp=datetime.utcnow()
#         ))
#         db.commit()

#         print(f"🤖 Agent Reply: {response}")
#         await send_whatsapp_message(wa_id, response)

#     except Exception as e:
#         print("❌ Error in webhook:", e)

#     finally:
#         db.close() 

#     return {"status": "ok"}



# async def send_whatsapp_message(recipient_number: str, message: str):
#     url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
#     headers = {
#         "Authorization": f"Bearer {WHATSAPP_TOKEN}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": recipient_number,
#         "type": "text",
#         "text": {"body": message}
#     }

#     async with httpx.AsyncClient() as client:
#         response = await client.post(url, json=payload, headers=headers)
#         if response.status_code != 200:
#             print("❌ Failed to send:", response.text)
# from fastapi import APIRouter, Request
# from fastapi.responses import PlainTextResponse
# from dotenv import load_dotenv
# from datetime import datetime
# import os
# import httpx
# import logging
# import traceback

# from app.agent.booking_agent import BookingToolAgent
# from app.database import SessionLocal
# from app.chatbot.models import Session as SessionModel, Message
# from app.format_message import formatting

# # Load environment variables
# load_dotenv()

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Config
# VERIFY_TOKEN = "my_custom_secret_token"
# WHATSAPP_TOKEN = os.getenv("META_ACCESS_TOKEN")
# PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")

# router = APIRouter()
# agent = BookingToolAgent()


# @router.get("/meta-webhook")
# def verify_webhook(request: Request):
#     params = request.query_params
#     if params.get("hub.verify_token") == VERIFY_TOKEN:
#         return PlainTextResponse(params.get("hub.challenge"))
#     return PlainTextResponse("Invalid token", status_code=403)


# @router.post("/meta-webhook")
# async def receive_message(request: Request):
#     db = SessionLocal()

#     try:
#         data = await request.json()
#         logger.info("📩 Incoming data: %s", data)

#         entry = data.get("entry", [])[0]
#         changes = entry.get("changes", [])[0]
#         value = changes.get("value", {})
#         messages = value.get("messages")

#         if not messages:
#             logger.info("🔕 No new message received.")
#             return {"status": "ignored"}

#         message = messages[0]
#         wa_id = message["from"]
#         session_id = wa_id

#         # Ensure it's a text message
#         if "text" not in message:
#             logger.warning("⚠️ Non-text message received. Ignored.")
#             return {"status": "ignored"}

#         text = message["text"]["body"]
#         logger.info(f"✅ Message from {wa_id}: {text}")

#         # --- Session handling ---
#         session = db.query(SessionModel).filter_by(id=session_id).first()
#         if not session:
#             session = SessionModel(id=session_id, whatsapp_number=wa_id)
#             db.add(session)
#             db.commit()

#         # --- Save user message ---
#         db.add(Message(session_id=session_id, sender="user", content=text, timestamp=datetime.utcnow()))
#         db.commit()

#         # --- Get bot response ---
#         response = agent.get_response(incoming_text=text, session_id=session_id)
#         formatted_response = formatting(response)

#         # --- Save bot response ---
#         db.add(Message(session_id=session_id, sender="bot", content=formatted_response, timestamp=datetime.utcnow()))
#         db.commit()

#         logger.info(f"🤖 Bot reply to {wa_id}: {formatted_response}")
#         await send_whatsapp_message(wa_id, formatted_response)

#     except Exception as e:
#         logger.error("❌ Exception in webhook: %s", e)
#         traceback.print_exc()

#     finally:
#         db.close()

#     return {"status": "ok"}


# async def send_whatsapp_message(recipient_number: str, message: str):
#     url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
#     headers = {
#         "Authorization": f"Bearer {WHATSAPP_TOKEN}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": recipient_number,
#         "type": "text",
#         "text": {"body": message}
#     }

#     try:
#         async with httpx.AsyncClient(timeout=10.0) as client:
#             response = await client.post(url, json=payload, headers=headers)
#             if response.status_code != 200:
#                 logger.error("❌ WhatsApp send failed: %s", response.text)
#             else:
#                 logger.info("✅ Message sent successfully to %s", recipient_number)
#     except httpx.RequestError as e:
#         logger.error("❌ Network error while sending message: %s", e)
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from datetime import datetime
import os
import httpx
import logging
import traceback
import time
from sqlalchemy.exc import OperationalError

from app.agent.booking_agent import BookingToolAgent
from app.database import SessionLocal
from app.chatbot.models import Session as SessionModel, Message
from app.format_message import formatting

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
VERIFY_TOKEN = "my_custom_secret_token"
WHATSAPP_TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")

router = APIRouter()
agent = BookingToolAgent()


def db_operation_with_retry(operation_func, max_retries=3, delay=1):
    """
    Retry database operations on connection failures
    """
    for attempt in range(max_retries):
        try:
            return operation_func()
        except OperationalError as e:
            error_msg = str(e).lower()
            if ("ssl connection has been closed" in error_msg or 
                "connection" in error_msg) and attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}), retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
                continue
            else:
                logger.error(f"Database operation failed after {max_retries} attempts: {e}")
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


@router.post("/meta-webhook")
async def receive_message(request: Request):
    db = None
    
    try:
        data = await request.json()
        logger.info("📩 Incoming data: %s", data)

        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages")

        if not messages:
            logger.info("🔕 No new message received.")
            return {"status": "ignored"}

        message = messages[0]
        wa_id = message["from"]
        session_id = wa_id

        # Ensure it's a text message
        if "text" not in message:
            logger.warning("⚠️ Non-text message received. Ignored.")
            return {"status": "ignored"}

        text = message["text"]["body"]
        logger.info(f"✅ Message from {wa_id}: {text}")

        # Create database session with retry logic
        def create_db_session():
            return SessionLocal()
        
        db = db_operation_with_retry(create_db_session)

        # --- Session handling with retry ---
        def get_or_create_session():
            session = db.query(SessionModel).filter_by(id=session_id).first()
            if not session:
                session = SessionModel(id=session_id, whatsapp_number=wa_id)
                db.add(session)
                db.commit()
            return session

        session = db_operation_with_retry(get_or_create_session)

        # --- Save user message with retry ---
        def save_user_message():
            user_message = Message(
                session_id=session_id, 
                sender="user", 
                content=text, 
                timestamp=datetime.utcnow()
            )
            db.add(user_message)
            db.commit()
            return user_message

        db_operation_with_retry(save_user_message)

        # --- Get bot response ---
        response = agent.get_response(incoming_text=text, session_id=session_id)
        formatted_response = formatting(response)

        # --- Save bot response with retry ---
        def save_bot_message():
            bot_message = Message(
                session_id=session_id, 
                sender="bot", 
                content=formatted_response, 
                timestamp=datetime.utcnow()
            )
            db.add(bot_message)
            db.commit()
            return bot_message

        db_operation_with_retry(save_bot_message)

        logger.info(f"🤖 Bot reply to {wa_id}: {formatted_response}")
        await send_whatsapp_message(wa_id, formatted_response)

    except OperationalError as e:
        logger.error("❌ Database connection error in webhook: %s", e)
        # Return a graceful response even if database fails
        if "wa_id" in locals():
            try:
                await send_whatsapp_message(wa_id, "Sorry, I'm experiencing technical difficulties. Please try again in a moment.")
            except:
                pass
        return {"status": "database_error", "error": "temporary_database_issue"}
        
    except Exception as e:
        logger.error("❌ Exception in webhook: %s", e)
        traceback.print_exc()
        # Send error message to user if possible
        if "wa_id" in locals():
            try:
                await send_whatsapp_message(wa_id, "Sorry, something went wrong. Please try again.")
            except:
                pass
        return {"status": "error"}

    finally:
        if db:
            try:
                db.close()
            except:
                logger.warning("Failed to close database session")

    return {"status": "ok"}


async def send_whatsapp_message(recipient_number: str, message: str):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "text",
        "text": {"body": message}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:  # Increased timeout
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error("❌ WhatsApp send failed: %s", response.text)
            else:
                logger.info("✅ Message sent successfully to %s", recipient_number)
    except httpx.RequestError as e:
        logger.error("❌ Network error while sending message: %s", e)
    except Exception as e:
        logger.error("❌ Unexpected error while sending message: %s", e)