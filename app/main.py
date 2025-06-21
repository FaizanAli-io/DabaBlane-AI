from fastapi import FastAPI

from app.routers import bookings
from app.routers import agent  # 👈 new import
from app.database import engine
from app.chatbot import models

# This will register (create) all tables in the DB
models.Base.metadata.create_all(bind=engine)
#from app.chatbot.models import client, session, message
app = FastAPI()


#app.include_router(bookings.router)
app.include_router(agent.router)  # 👈 include agent router
