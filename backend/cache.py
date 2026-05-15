"""Tiny SQLite-backed TTL cache for feed responses (zero extra infra)."""
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import CacheEntry


def cache_get(db: Session, key: str):
    row = db.query(CacheEntry).filter(CacheEntry.key == key).first()
    if not row:
        return None
    if row.expires_at < datetime.utcnow():
        db.delete(row)
        db.commit()
        return None
    return json.loads(row.value)


def cache_set(db: Session, key: str, value, ttl_seconds: int) -> None:
    expires = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    payload = json.dumps(value, default=str)
    row = db.query(CacheEntry).filter(CacheEntry.key == key).first()
    if row:
        row.value = payload
        row.expires_at = expires
    else:
        db.add(CacheEntry(key=key, value=payload, expires_at=expires))
    db.commit()


def cache_clear(db: Session, prefix: str | None = None) -> None:
    q = db.query(CacheEntry)
    if prefix:
        q = q.filter(CacheEntry.key.like(f"{prefix}%"))
    q.delete(synchronize_session=False)
    db.commit()
