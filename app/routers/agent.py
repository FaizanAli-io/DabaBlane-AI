import uuid
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from fastapi.responses import RedirectResponse

from app.database import get_db
from app.database import SessionLocal
from app.agent.booking_agent import BookingToolAgent
from app.email.email_service import send_new_chat_email
from app.chatbot.models import Session as SessionModel, Message

router = APIRouter()
agent = BookingToolAgent()


class ChatInput(BaseModel):
    session_id: str
    message: str


@router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@router.post("/chat")
def chat_with_agent(request: ChatInput, db: Session = Depends(get_db)):
    session_id = request.session_id
    user_message = request.message

    # Log user message
    user_msg = Message(
        sender="user",
        content=user_message,
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(user_msg)
    db.commit()

    # Get agent response
    response_text = agent.get_response(user_message, session_id)
    response_text = response_text.replace("**", "*")

    # Log bot response
    bot_msg = Message(
        sender="bot",
        content=response_text,
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(bot_msg)
    db.commit()

    # Send email if new conversation
    session = db.query(SessionModel).filter_by(id=session_id).first()
    send_new_chat_email(session, user_message, db)

    return {"response": response_text}


@router.get("/session/list")
def list_sessions():
    db = SessionLocal()
    sessions = db.query(SessionModel).order_by(SessionModel.created_at.asc()).all()
    db.close()
    return [
        {
            "id": session.id,
            "created_at": session.created_at,
            "last_interaction": session.last_interaction,
        }
        for session in sessions
    ]


@router.post("/session/create")
def create_session():
    session_id = str(uuid.uuid4())
    with SessionLocal() as db:
        new_session = SessionModel(
            id=session_id,
            last_interaction=None,
        )
        db.add(new_session)
        db.commit()

    return {"session_id": session_id}


@router.delete("/session/delete")
def delete_all_sessions():
    db = SessionLocal()
    db.query(Message).delete()
    deleted = db.query(SessionModel).delete()
    db.commit()
    db.close()

    return {"detail": "All sessions deleted", "deleted_sessions": deleted}


@router.delete("/session/{session_id}")
def delete_session(session_id: str):
    db = SessionLocal()
    db.query(Message).filter(Message.session_id == session_id).delete()
    deleted = db.query(SessionModel).filter(SessionModel.id == session_id).delete()
    db.commit()
    db.close()

    return {"detail": "Session deleted" if deleted else "Session not found"}


@router.get("/chat/history/{session_id}")
def get_chat_history(session_id: str):
    db = SessionLocal()
    history = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp)
        .all()
    )
    db.close()
    return [
        {"sender": msg.sender, "message": msg.content, "timestamp": msg.timestamp}
        for msg in history
    ]


@router.delete("/chat/history/{session_id}")
def clear_chat_history(session_id: str):
    db = SessionLocal()
    deleted = db.query(Message).filter(Message.session_id == session_id).delete()
    db.commit()
    db.close()
    if deleted:
        return {"detail": "Chat history cleared"}
    else:
        return {"detail": "No chat history found for this session"}


@router.delete("/chat/history")
def clear_all_chat_history():
    """Delete chat messages for all sessions (does not delete sessions)."""
    db = SessionLocal()
    deleted = db.query(Message).delete()
    db.commit()
    db.close()
    return {"detail": f"Cleared {deleted} messages across all sessions"}
