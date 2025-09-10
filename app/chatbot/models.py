from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

# class Client(Base):
#     __tablename__ = "clients"

#     email = Column(String(255), primary_key=True, index=True, unique=True)  # ✅ LENGTH ADDED
#     name = Column(String(100), nullable=True)
#     role = Column(String(20), default="CLIENT")
#     auth_token = Column(String(255), nullable=True)
#     authenticated_at = Column(DateTime, default=datetime.utcnow)

#     sessions = relationship("Session", back_populates="client")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(
        String(64), primary_key=True, index=True
    )  # Use a UUID string or similar
    client_email = Column(String(255), nullable=True)
    client_id = Column(Integer, nullable=True)
    whatsapp_number = Column(String(30), nullable=True)
    # client_email = Column(String(255), ForeignKey("clients.email"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # client = relationship("Client", back_populates="sessions")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("sessions.id"))
    sender = Column(String(10))  # e.g. "user" or "bot"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")
