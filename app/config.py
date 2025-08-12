# Configuration and environment settings utilities
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


def get_env_list(name: str, default: str) -> List[str]:
    raw = os.getenv(name, default)
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


@dataclass
class Settings:
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    reload: bool = os.getenv("APP_RELOAD", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "info")

    cors_allow_origins: List[str] = None  # set in __post_init__

    cache_similarity_threshold: int = int(os.getenv("CACHE_SIMILARITY_THRESHOLD", "90"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "86400"))

    # Local SQLite path for app session storage
    sqlite_path: str = os.getenv("LOCAL_SQLITE_PATH", os.path.join(os.path.dirname(__file__), "..", "var", "app_data.sqlite"))

    def __post_init__(self):
        self.cors_allow_origins = get_env_list("CORS_ALLOW_ORIGINS", os.getenv("CORS_ALLOW_ORIGINS", "*"))


settings = Settings()
