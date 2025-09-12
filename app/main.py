from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agent
from app.chatbot import models
from app.database import engine
from app.routers import wati_webhook

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(agent.router)
app.include_router(wati_webhook.router)
