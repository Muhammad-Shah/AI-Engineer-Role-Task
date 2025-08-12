from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.db_models import init_local_db
from app.routers import database as database_router
from app.routers import chat as chat_router


app = FastAPI(title="Database Chatbot with FastAPI", version="1.0.0")

# CORS
origins = settings.cors_allow_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(database_router.router)
app.include_router(chat_router.router)


@app.on_event("startup")
def on_startup():
    # Ensure local SQLite exists
    init_local_db()


@app.get("/")
def root():
    return {"status": "ok", "app": app.title, "version": "1.0.0"}
