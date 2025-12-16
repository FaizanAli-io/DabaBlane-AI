import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()


class PasswordRequest(BaseModel):
    password: str


@router.post("/interface/verify-password")
async def verify_password(request: PasswordRequest):
    interface_password = os.getenv("INTERFACE_PASSWORD")
    if not interface_password:
        raise HTTPException(status_code=500, detail="Interface password not configured")

    if request.password == interface_password:
        return {"success": True}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")


@router.get("/interface")
async def serve_interface():
    return FileResponse(os.path.join("static", "chat.html"))
