from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.chatbot import models
from app.database import engine

from app.routers import (
    agent,
    payment,
    interface,
    wati_webhook,
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Mount static files
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")

app.include_router(agent.router)
app.include_router(payment.router)
app.include_router(interface.router)
app.include_router(wati_webhook.router)
