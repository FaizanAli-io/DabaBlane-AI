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
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from datetime import datetime
import os
import httpx
import logging
import traceback

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


@router.get("/meta-webhook")
def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Invalid token", status_code=403)


@router.post("/meta-webhook")
async def receive_message(request: Request):
    db = SessionLocal()

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

        # --- Session handling ---
        session = db.query(SessionModel).filter_by(id=session_id).first()
        if not session:
            session = SessionModel(id=session_id, whatsapp_number=wa_id)
            db.add(session)
            db.commit()

        # --- Save user message ---
        db.add(Message(session_id=session_id, sender="user", content=text, timestamp=datetime.utcnow()))
        db.commit()

        # --- Get bot response ---
        response = agent.get_response(incoming_text=text, session_id=session_id)
        formatted_response = formatting(response)

        # --- Save bot response ---
        db.add(Message(session_id=session_id, sender="bot", content=formatted_response, timestamp=datetime.utcnow()))
        db.commit()

        logger.info(f"🤖 Bot reply to {wa_id}: {formatted_response}")
        await send_whatsapp_message(wa_id, formatted_response)

    except Exception as e:
        logger.error("❌ Exception in webhook: %s", e)
        traceback.print_exc()

    finally:
        db.close()

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
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error("❌ WhatsApp send failed: %s", response.text)
            else:
                logger.info("✅ Message sent successfully to %s", recipient_number)
    except httpx.RequestError as e:
        logger.error("❌ Network error while sending message: %s", e)
