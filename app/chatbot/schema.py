from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime


class ClientBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: Optional[str] = "CLIENT"


class ClientCreate(ClientBase):
    password: Optional[str] = None  # If needed during creation


class ClientOut(ClientBase):
    authenticated_at: Optional[datetime] = None
    auth_token: Optional[str] = None

    class Config:
        orm_mode = True


class SessionCreate(BaseModel):
    client_email: Optional[str] = None


class SessionOut(SessionCreate):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True


class MessageCreate(BaseModel):
    session_id: str
    sender: Literal["user", "bot"]
    content: str


class MessageOut(MessageCreate):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True
