from fastapi import FastAPI

from app.routers import wati_webhook
from app.routers import agent
from app.database import engine
from app.chatbot import models


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(agent.router)
app.include_router(wati_webhook.router)
