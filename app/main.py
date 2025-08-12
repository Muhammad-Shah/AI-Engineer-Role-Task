from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.db_models import init_local_db
from app.routers import database as database_router
from app.routers import chat as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_local_db()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="Database Chatbot with FastAPI", 
    version="1.0.0",
    description="""
    A comprehensive database chatbot that enables natural language interactions with various databases.
    
    ## Features
    
    * **Multi-Database Support**: Connect to PostgreSQL, MySQL, and MongoDB
    * **Natural Language Processing**: Convert plain English to SQL/MongoDB queries using LLM agents
    * **Real-time Streaming**: Get live feedback as queries are processed
    * **Session Management**: Maintain conversation history and context
    * **Smart Caching**: Intelligent query result caching with similarity matching
    * **Secure Connections**: Connection pooling with timeout management
    
    ## Getting Started
    
    1. **Connect to Database**: Use `/api/database/connect` to establish a connection
    2. **Create Chat Session**: Use `/api/chat/sessions` to start a conversation
    3. **Send Queries**: Use `/api/chat/query` to ask questions in natural language
    4. **Stream Results**: Receive real-time responses as your query is processed
    
    ## Example Queries
    
    * "Show me all users from the last month"
    * "How many orders were placed yesterday?"
    * "List users in the Engineering department"
    * "What's the total revenue this year?"
    
    **Note**: LLM functionality requires `OPENAI_API_KEY` environment variable.
    """,
    contact={
        "name": "Muhammad Shah",
        "email": "muhammadof9@gmail.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)

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





@app.get("/")
def root():
    return {"status": "ok", "app": app.title, "version": "1.0.0"}
