from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# Database connection
class DatabaseConnectRequest(BaseModel):
    host: str
    port: int
    database: str
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    db_type: Literal["postgresql", "mysql", "mongodb"] = Field(default="postgresql")
    options: Optional[Dict[str, Any]] = None


class DatabaseInfo(BaseModel):
    db_type: str
    server_version: Optional[str] = None
    database: Optional[str] = None


class DatabaseConnectResponse(BaseModel):
    connection_id: str
    status: Literal["connected", "failed"]
    database_info: Optional[DatabaseInfo] = None
    error: Optional[str] = None


class DatabaseValidateResponse(BaseModel):
    connection_id: str
    is_valid: bool
    last_checked: str
    error: Optional[str] = None


class DisconnectResponse(BaseModel):
    connection_id: str
    status: Literal["disconnected", "not_found"]


# Chat schemas
class ChatQueryRequest(BaseModel):
    connection_id: str
    message: str
    session_id: Optional[str] = None


class ChatSessionModel(BaseModel):
    session_id: str
    created_at: str
    title: str


class ChatSessionCreateResponse(BaseModel):
    session_id: str
    created_at: str


class ChatMessageModel(BaseModel):
    message_id: str
    type: Literal["user", "assistant"]
    content: str
    timestamp: str


class DeleteSessionResponse(BaseModel):
    session_id: str
    status: Literal["deleted", "not_found"]
