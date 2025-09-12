from langchain.tools import tool

from app.database import SessionLocal
from app.chatbot.models import Session


@tool("authenticate_email")
def authenticate_email(session_id: str, client_email: str) -> str:
    """
    Authenticates a user by email and associates it with a session.
    """
    with SessionLocal() as db:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            return f"Session {session_id} not found."

        session.client_email = client_email
        db.commit()

    return f"Authenticated {client_email} for session {session_id}"
