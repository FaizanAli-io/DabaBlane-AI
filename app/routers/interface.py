import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/interface")
async def serve_interface():
    return FileResponse(os.path.join("static", "chat.html"))
