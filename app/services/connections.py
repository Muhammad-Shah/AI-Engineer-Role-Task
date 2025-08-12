from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    import pymongo
except Exception:  # pragma: no cover
    pymongo = None  # type: ignore


@dataclass
class ConnectionEntry:
    connection_id: str
    db_type: str  # postgresql | mysql | mongodb
    created_at: float
    last_checked: float
    database: Optional[str]
    engine: Optional[Engine] = None
    mongo_client: Optional[Any] = None


class ConnectionRegistry:
    def __init__(self) -> None:
        self._store: Dict[str, ConnectionEntry] = {}

    def connect(self, host: str, port: int, database: str, username: str, password: str, db_type: str = "postgresql", options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        connection_id = str(uuid.uuid4())
        created_at = time.time()
        options = options or {}

        if db_type in ("postgresql", "mysql"):
            driver = "postgresql+psycopg2" if db_type == "postgresql" else "mysql+pymysql"
            url = f"{driver}://{username}:{password}@{host}:{port}/{database}"
            pool_size = int(options.get("pool_size", 5))
            max_overflow = int(options.get("max_overflow", 10))
            pool_timeout = int(options.get("pool_timeout", 30))
            connect_timeout = int(options.get("connect_timeout", 10))
            engine = create_engine(
                url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                connect_args={"connect_timeout": connect_timeout},
                pool_pre_ping=True,
                future=True,
            )
            # Validate connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                server_version = None
                try:
                    result = conn.execute(text("SELECT version()"))
                    server_version = result.scalar_one_or_none()
                except Exception:
                    server_version = None

            entry = ConnectionEntry(
                connection_id=connection_id,
                db_type=db_type,
                created_at=created_at,
                last_checked=created_at,
                database=database,
                engine=engine,
            )
            self._store[connection_id] = entry
            return {
                "connection_id": connection_id,
                "status": "connected",
                "database_info": {
                    "db_type": db_type,
                    "database": database,
                    "server_version": server_version,
                },
            }

        elif db_type == "mongodb":
            if pymongo is None:
                raise RuntimeError("pymongo is not installed")
            uri = f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource={database}"
            server_selection_timeout_ms = int(options.get("serverSelectionTimeoutMS", 5000))
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=server_selection_timeout_ms)
            # Validate connection
            client.admin.command("ping")
            server_info = client.server_info()
            entry = ConnectionEntry(
                connection_id=connection_id,
                db_type=db_type,
                created_at=created_at,
                last_checked=created_at,
                database=database,
                mongo_client=client,
            )
            self._store[connection_id] = entry
            return {
                "connection_id": connection_id,
                "status": "connected",
                "database_info": {
                    "db_type": db_type,
                    "database": database,
                    "server_version": str(server_info.get("version")),
                },
            }
        else:
            raise ValueError(f"Unsupported db_type: {db_type}")

    def validate(self, connection_id: str) -> Dict[str, Any]:
        entry = self._store.get(connection_id)
        now = time.time()
        if not entry:
            return {"connection_id": connection_id, "is_valid": False, "last_checked": datetime.utcfromtimestamp(now).isoformat() + "Z", "error": "not_found"}

        try:
            if entry.db_type in ("postgresql", "mysql") and entry.engine is not None:
                with entry.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            elif entry.db_type == "mongodb" and entry.mongo_client is not None:
                entry.mongo_client.admin.command("ping")
            else:
                raise RuntimeError("invalid entry state")
            entry.last_checked = now
            return {"connection_id": connection_id, "is_valid": True, "last_checked": datetime.utcfromtimestamp(now).isoformat() + "Z"}
        except Exception as exc:
            return {"connection_id": connection_id, "is_valid": False, "last_checked": datetime.utcfromtimestamp(now).isoformat() + "Z", "error": str(exc)}

    def disconnect(self, connection_id: str) -> Dict[str, Any]:
        entry = self._store.pop(connection_id, None)
        if not entry:
            return {"connection_id": connection_id, "status": "not_found"}
        try:
            if entry.engine is not None:
                entry.engine.dispose()
            if entry.mongo_client is not None:
                entry.mongo_client.close()
        finally:
            return {"connection_id": connection_id, "status": "disconnected"}


registry = ConnectionRegistry()
