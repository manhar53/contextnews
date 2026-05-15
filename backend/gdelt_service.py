"""GDELT context: pull related historical coverage to enrich causal chains.

Free, no API key. Used to give Gemini real prior-event context so the
causal_timeline is grounded rather than hallucinated.
"""
import logging
import re

import httpx

logger = logging.getLogger("contextnews.gdelt")

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "with", "as", "is",
    "at", "by", "from", "after", "over", "amid", "says", "new", "india", "indian",
}


def _keywords(headline: str, limit: int = 5) -> str:
    words = re.findall(r"[A-Za-z]{4,}", headline or "")
    keep = [w for w in words if w.lower() not in _STOPWORDS][:limit]
    return " ".join(keep) if keep else (headline or "")[:60]


def backfill_historic() -> int:
    """One-shot: pull ~12 months of coverage for the core topics via GDELT.

    Gives the causal timeline real historical depth on day one (idea borrowed
    from fetch-and-index-global-news' "historic" mode).
    """
    import time
    from datetime import datetime

    from config import settings
    from database import SessionLocal
    from dedupe import is_duplicate, normalise
    from models import Article
    from sources import get_priority

    queries = {
        "India defence military": "defence",
        "India geopolitics border": "geopolitics",
        "Indian economy policy": "economy",
        "India government ministry": "government",
    }
    db = SessionLocal()
    total = 0
    try:
        rows = db.query(Article.headline_norm).order_by(Article.id.desc()).limit(1500).all()
        recent = [r[0] for r in rows if r[0]]
        seen: set[str] = set()
        for i, (query, category) in enumerate(queries.items()):
            if i:
                time.sleep(6)  # GDELT allows ~1 request / 5s
            params = {
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": settings.gdelt_backfill_max_per_query,
                "timespan": f"{settings.gdelt_backfill_months}m",
                "sort": "datedesc",
            }
            try:
                resp = httpx.get(GDELT_DOC_URL, params=params, timeout=25)
                resp.raise_for_status()
                articles = resp.json().get("articles", [])
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("GDELT backfill failed for '%s': %s", query, exc)
                continue

            for a in articles:
                url = a.get("url")
                title = a.get("title")
                if not url or not title or url in seen:
                    continue
                if db.query(Article).filter(Article.url == url).first():
                    continue
                if is_duplicate(db, title, recent):
                    continue
                seen.add(url)
                norm = normalise(title)
                pub = None
                try:
                    pub = datetime.strptime(a.get("seendate", ""), "%Y%m%dT%H%M%SZ")
                except (ValueError, TypeError):
                    pass
                db.add(
                    Article(
                        url=url,
                        headline=title,
                        headline_norm=norm,
                        source=a.get("domain"),
                        description=None,
                        content=None,
                        image_url=a.get("socialimage"),
                        origin="gdelt",
                        category=category,
                        source_priority=get_priority(a.get("domain")),
                        published_at=pub,
                    )
                )
                recent.append(norm)
                total += 1
            db.commit()
        logger.info("GDELT backfill complete. %d historic articles.", total)
    finally:
        db.close()
    return total


def get_events(headline: str, top: int = 5, months: int = 60) -> list[dict]:
    """Top historical events for the article keywords over ~5 years (default 60m)."""
    query = _keywords(headline)
    if not query:
        return []
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": max(top, 10),
        "timespan": f"{months}m",
        "sort": "datedesc",
    }
    try:
        resp = httpx.get(GDELT_DOC_URL, params=params, timeout=20)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("GDELT events unavailable for '%s': %s", query, exc)
        return []
    out = []
    for a in articles[:top]:
        if a.get("title"):
            out.append(
                {
                    "title": a.get("title"),
                    "domain": a.get("domain"),
                    "date": a.get("seendate"),
                    "url": a.get("url"),
                }
            )
    return out


