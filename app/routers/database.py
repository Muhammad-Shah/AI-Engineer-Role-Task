from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.models.schemas import DatabaseConnectRequest, DatabaseConnectResponse, DatabaseValidateResponse, DisconnectResponse
from app.services.connections import registry

router = APIRouter(prefix="/api/database", tags=["database"])


@router.post("/connect", response_model=DatabaseConnectResponse)
def connect_database(body: DatabaseConnectRequest):
    try:
        result = registry.connect(
            host=body.host,
            port=body.port,
            database=body.database,
            username=body.username,
            password=body.password,
            db_type=body.db_type,
            options=body.options or {},
        )
        return result
    except Exception as exc:
        return DatabaseConnectResponse(connection_id="", status="failed", error=str(exc))


@router.get("/validate/{connection_id}", response_model=DatabaseValidateResponse)
def validate_connection(connection_id: str):
    result = registry.validate(connection_id)
    # Ensure last_checked is ISO with Z
    if "last_checked" not in result:
        result["last_checked"] = datetime.now(timezone.utc).isoformat()
    return result


@router.delete("/disconnect/{connection_id}", response_model=DisconnectResponse)
def disconnect_database(connection_id: str):
    return registry.disconnect(connection_id)
