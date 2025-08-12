from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, Integer, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VAR_DIR = os.path.join(BASE_DIR, "var")
if not os.path.exists(VAR_DIR):
    os.makedirs(VAR_DIR, exist_ok=True)

SQLITE_PATH = os.path.join(VAR_DIR, "app_data.sqlite")
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String(200), default="Chat Session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), index=True)
    sender_type = Column(String(16))  # user | assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CachedQuery(Base):
    __tablename__ = "cached_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    normalized_message = Column(Text, index=True)
    sql_text = Column(Text)
    result_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=0)
    ttl_seconds = Column(Integer, default=86400)

    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return datetime.utcnow() > self.created_at + timedelta(seconds=int(self.ttl_seconds))


def init_local_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
