from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.db_models import ChatMessage, ChatSession, get_db_session
from app.models.schemas import ChatQueryRequest, ChatSessionCreateResponse, ChatSessionModel, ChatMessageModel, DeleteSessionResponse
from app.services.connections import registry
from app.services.cache import find_cached_result, store_cache, increment_cache_hit
from app.services.llm_agent import run_sql_react_agent, run_mongo_react_agent
from app.config import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _ensure_session(db: Session, session_id: Optional[str]) -> ChatSession:
    if session_id:
        sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if sess:
            return sess
    # create new
    sess = ChatSession(title="Chat Session")
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _normalize_message(message: str) -> str:
    # Simple normalization for caching similarity
    return re.sub(r"\s+", " ", message.strip().lower())


@router.post("/sessions", response_model=ChatSessionCreateResponse)
def create_session(db: Session = Depends(get_db_session)):
    sess = _ensure_session(db, None)
    return ChatSessionCreateResponse(session_id=sess.id, created_at=sess.created_at.replace(tzinfo=timezone.utc).isoformat())


@router.get("/sessions", response_model=List[ChatSessionModel])
def list_sessions(db: Session = Depends(get_db_session)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return [
        ChatSessionModel(
            session_id=s.id,
            created_at=s.created_at.replace(tzinfo=timezone.utc).isoformat(),
            title=s.title,
        ) for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageModel])
def get_messages(session_id: str, db: Session = Depends(get_db_session)):
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    return [
        ChatMessageModel(
            message_id=m.id,
            type=m.sender_type,
            content=m.content,
            timestamp=m.created_at.replace(tzinfo=timezone.utc).isoformat(),
        ) for m in msgs
    ]


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
def delete_session(session_id: str, db: Session = Depends(get_db_session)):
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess:
        return DeleteSessionResponse(session_id=session_id, status="not_found")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(sess)
    db.commit()
    return DeleteSessionResponse(session_id=session_id, status="deleted")


@router.post("/query")
def query_chat(body: ChatQueryRequest, db: Session = Depends(get_db_session)):
    # Validate connection
    conn_info = registry.validate(body.connection_id)
    if not conn_info.get("is_valid"):
        raise HTTPException(status_code=400, detail=f"Invalid connection: {conn_info.get('error', 'unknown')}")

    # Ensure session
    sess = _ensure_session(db, body.session_id)

    # Persist user message
    user_msg = ChatMessage(session_id=sess.id, sender_type="user", content=body.message)
    db.add(user_msg)
    db.commit()

    def event_stream() -> Generator[bytes, None, None]:
        # step 1: acknowledge
        yield json.dumps({"event": "start", "session_id": sess.id}).encode() + b"\n"

        normalized = _normalize_message(body.message)
        # Bonus: cache lookup (threshold from settings, percentage -> fraction)
        cache_threshold = max(0.0, min(1.0, settings.cache_similarity_threshold / 100.0))
        cache_hit = find_cached_result(db, normalized, threshold=cache_threshold)
        if cache_hit is not None:
            entry, score = cache_hit
            increment_cache_hit(db, entry)
            yield json.dumps({"event": "cache_hit", "similarity": score, "message": entry.normalized_message}).encode() + b"\n"
            result = json.loads(entry.result_json)
            # Persist assistant message
            assistant_msg = ChatMessage(session_id=sess.id, sender_type="assistant", content=json.dumps(result))
            db.add(assistant_msg)
            db.commit()
            yield json.dumps({"event": "result", "data": result}).encode() + b"\n"
            yield json.dumps({"event": "end"}).encode() + b"\n"
            return

        # No cache: use LLM ReAct agent
        try:
            entry = registry._store.get(body.connection_id)
            if entry is None:
                raise RuntimeError("connection not found")

            if entry.db_type in ("postgresql", "mysql") and entry.engine is not None:
                yield json.dumps({"event": "agent_started", "mode": "sql"}).encode() + b"\n"
                agent_out = run_sql_react_agent(entry.engine, body.message, temperature=0.6)
                if agent_out.generated_sql:
                    yield json.dumps({"event": "generated_sql", "sql": agent_out.generated_sql, "params": {}}).encode() + b"\n"
                result = {"columns": agent_out.result_columns, "rows": agent_out.result_rows}
                # persist and cache
                store_cache(db, normalized, agent_out.generated_sql or "", result, ttl_seconds=settings.cache_ttl_seconds)
                assistant_msg = ChatMessage(session_id=sess.id, sender_type="assistant", content=json.dumps(result))
                db.add(assistant_msg)
                db.commit()
                yield json.dumps({"event": "result", "data": result}).encode() + b"\n"
                yield json.dumps({"event": "end"}).encode() + b"\n"
                return

            elif entry.db_type == "mongodb" and entry.mongo_client is not None:
                yield json.dumps({"event": "agent_started", "mode": "mongo"}).encode() + b"\n"
                agent_out = run_mongo_react_agent(entry.mongo_client, entry.database or "admin", body.message, temperature=0.6)
                if agent_out.generated_filter is not None:
                    yield json.dumps({"event": "generated_filter", "filter": agent_out.generated_filter}).encode() + b"\n"
                result = {"columns": agent_out.result_columns, "rows": agent_out.result_rows}
                store_cache(
                    db,
                    normalized,
                    json.dumps({"collection": "*", "filter": agent_out.generated_filter or {}}),
                    result,
                    ttl_seconds=settings.cache_ttl_seconds,
                )
                assistant_msg = ChatMessage(session_id=sess.id, sender_type="assistant", content=json.dumps(result))
                db.add(assistant_msg)
                db.commit()
                yield json.dumps({"event": "result", "data": result}).encode() + b"\n"
                yield json.dumps({"event": "end"}).encode() + b"\n"
                return
            else:
                yield json.dumps({"event": "error", "message": "Unsupported connection type"}).encode() + b"\n"
                yield json.dumps({"event": "end"}).encode() + b"\n"
                return
        except Exception as exc:
            yield json.dumps({"event": "agent_error", "message": str(exc)}).encode() + b"\n"
            yield json.dumps({"event": "end"}).encode() + b"\n"

    # Stream as NDJSON
    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
