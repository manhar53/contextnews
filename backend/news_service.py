"""NewsAPI supplement: reserved for a few specific search queries only."""
from datetime import datetime, timezone
import logging

import httpx
from sqlalchemy.exc import IntegrityError

from config import settings
from database import SessionLocal
from dedupe import is_duplicate, normalise
from models import Article
from sources import get_priority

logger = logging.getLogger("contextnews.newsapi")

NEWSAPI_URL = "https://newsapi.org/v2/everything"

# reserved search queries -> category bucket
SEARCH_QUERIES: dict[str, str] = {
    "India defence": "defence",
    "geopolitics": "geopolitics",
    "Indian economy": "economy",
    "government policy India": "government",
}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )
    except ValueError:
        return None


def fetch_newsapi() -> int:
    if not settings.newsapi_key:
        logger.warning("NEWSAPI_KEY not set; skipping NewsAPI fetch.")
        return 0

    db = SessionLocal()
    total_new = 0
    try:
        rows = db.query(Article.headline_norm).order_by(Article.id.desc()).limit(800).all()
        recent_norms = [r[0] for r in rows if r[0]]
        seen_urls: set[str] = set()

        with httpx.Client(timeout=20) as client:
            for query, category in SEARCH_QUERIES.items():
                params = {
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 20,
                    "apiKey": settings.newsapi_key,
                }
                try:
                    resp = client.get(NEWSAPI_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as exc:
                    logger.error("NewsAPI request failed for '%s': %s", query, exc)
                    continue
                if data.get("status") != "ok":
                    logger.error("NewsAPI error for '%s': %s", query, data.get("message"))
                    continue

                for a in data.get("articles", []):
                    url = a.get("url")
                    title = a.get("title")
                    if not url or not title:
                        continue
                    if url in seen_urls:
                        continue
                    if db.query(Article).filter(Article.url == url).first():
                        continue
                    if is_duplicate(db, title, recent_norms):
                        continue
                    seen_urls.add(url)

                    norm = normalise(title)
                    db.add(
                        Article(
                            url=url,
                            headline=title,
                            headline_norm=norm,
                            source=(a.get("source") or {}).get("name"),
                            author=a.get("author"),
                            description=a.get("description"),
                            content=a.get("content"),
                            image_url=a.get("urlToImage"),
                            origin="newsapi",
                            category=category,
                            source_priority=get_priority((a.get("source") or {}).get("name")),
                            published_at=_parse_dt(a.get("publishedAt")),
                        )
                    )
                    recent_norms.append(norm)
                    total_new += 1
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    logger.warning("Commit conflict for query '%s'; skipped.", query)
        logger.info("NewsAPI fetch complete. %d new articles.", total_new)
    finally:
        db.close()
    if total_new:
        try:
            from auto_analyse import auto_analyse_important

            auto_analyse_important()  # pre-analyse any new ★ articles immediately
        except Exception as exc:  # noqa: BLE001  never break the fetch
            logger.warning("Post-fetch auto-analyse skipped: %s", exc)
    return total_new
