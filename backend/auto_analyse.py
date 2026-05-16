"""Background job: auto-analyse a small batch of un-analysed "important"
SSB-topic articles via Gemini, so common lecturette topics are pre-prepared
and shared with every user (cached analyses are free for everyone).
"""
import logging
from datetime import datetime, timedelta

from config import settings
from database import SessionLocal
from gemini_service import GeminiRateLimited, analyze_article
from models import Analysis, Article
from topics import is_important

logger = logging.getLogger("contextnews.auto_analyse")


def auto_analyse_important() -> int:
    """Pick up to N un-analysed important articles and Gemini-analyse them.

    Stops early on a Gemini rate-limit; preserves the free-tier API quota.
    """
    if not settings.auto_analyse_enabled:
        return 0
    if not settings.gemini_api_key:
        return 0

    db = SessionLocal()
    done = 0
    try:
        cutoff = datetime.utcnow() - timedelta(days=14)
        # Recent un-analysed RSS/NewsAPI articles, highest-credibility first.
        candidates = (
            db.query(Article)
            .outerjoin(Analysis, Analysis.article_id == Article.id)
            .filter(Analysis.id.is_(None))
            .filter(Article.origin.in_(("rss", "newsapi")))
            .filter(Article.published_at >= cutoff)
            .order_by(
                Article.source_priority.desc(),
                Article.published_at.desc().nullslast(),
            )
            .limit(150)
            .all()
        )
        for a in candidates:
            if done >= settings.auto_analyse_per_run:
                break
            text = f"{a.headline or ''} {a.description or ''}"
            if not is_important(text):
                continue
            try:
                result = analyze_article(db, a)
            except GeminiRateLimited:
                logger.warning("Gemini rate-limited; stopping this run.")
                break
            if result is not None:
                done += 1
                logger.info("Auto-analysed important article %s: %s",
                            a.id, (a.headline or "")[:80])
        if done:
            logger.info("Auto-analyse complete: %d analysed.", done)
    finally:
        db.close()
    return done
