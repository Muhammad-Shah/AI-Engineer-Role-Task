from __future__ import annotations

import json
import re
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.db_models import CachedQuery


def _tokenize(text: str) -> set:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return {t for t in text.split() if t}


def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def find_cached_result(db: Session, normalized_message: str, threshold: float = 0.9) -> Optional[Tuple[CachedQuery, float]]:
    candidates = db.query(CachedQuery).all()
    best: Optional[Tuple[CachedQuery, float]] = None
    for c in candidates:
        if c.is_expired():
            continue
        score = jaccard_similarity(normalized_message, c.normalized_message)
        if score >= threshold and (best is None or score > best[1]):
            best = (c, score)
    return best


def store_cache(db: Session, normalized_message: str, sql_text: str, result: list, ttl_seconds: int = 86400) -> CachedQuery:
    entry = CachedQuery(
        normalized_message=normalized_message,
        sql_text=sql_text,
        result_json=json.dumps(result),
        ttl_seconds=ttl_seconds,
        hit_count=0,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def increment_cache_hit(db: Session, entry: CachedQuery) -> None:
    entry.hit_count = (entry.hit_count or 0) + 1
    db.add(entry)
    db.commit()