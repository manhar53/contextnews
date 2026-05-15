"""Headline de-duplication via token-set Jaccard similarity.

Replaces difflib SequenceMatcher: Jaccard on token sets is order-independent
and scales better across hundreds of feeds (approach borrowed from
worldmonitor, which dedups on >60% token overlap).
"""
import re

from sqlalchemy.orm import Session

from models import Article

JACCARD_THRESHOLD = 0.6
_RECENT_LOOKBACK = 800
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "with", "as",
    "is", "at", "by", "from", "after", "over", "amid", "says", "new", "will",
}


def normalise(headline: str) -> str:
    h = (headline or "").lower()
    h = re.sub(r"[^a-z0-9 ]", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def _tokens(norm: str) -> frozenset[str]:
    return frozenset(t for t in norm.split() if t not in _STOP and len(t) > 2)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b) if inter else 0.0


def is_duplicate(db: Session, headline: str, recent_norms: list[str] | None = None) -> bool:
    norm = normalise(headline)
    if not norm:
        return True

    if recent_norms is None:
        rows = (
            db.query(Article.headline_norm)
            .order_by(Article.id.desc())
            .limit(_RECENT_LOOKBACK)
            .all()
        )
        recent_norms = [r[0] for r in rows if r[0]]

    if norm in recent_norms:
        return True

    tokens = _tokens(norm)
    if not tokens:
        return False
    for existing in recent_norms:
        if _jaccard(tokens, _tokens(existing)) >= JACCARD_THRESHOLD:
            return True
    return False
