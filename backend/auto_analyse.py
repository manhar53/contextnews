"""Background job: auto-analyse EVERY un-analysed "important" SSB-topic
article via the LLM chain so common lecturette topics are pre-prepared and
shared with every user (cached analyses are free for everyone).

Each run keeps going until one of:
  * all important articles are analysed,
  * the per-run wall-clock budget is hit, or
  * every configured LLM provider returns 429 (real exhaustion).
"""
import logging
import time
from datetime import datetime, timedelta

from config import settings
from database import SessionLocal
from gemini_service import GeminiRateLimited, analyze_article
from models import Analysis, Article
from topics import is_important

logger = logging.getLogger("contextnews.auto_analyse")


def auto_analyse_important() -> int:
    if not settings.auto_analyse_enabled:
        return 0
    if not (
        settings.gemini_api_key
        or settings.groq_api_key
        or settings.openrouter_api_key
    ):
        return 0

    started = time.monotonic()
    budget = float(settings.auto_analyse_max_seconds)
    max_articles = settings.auto_analyse_per_run

    db = SessionLocal()
    done = 0
    skipped = 0
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
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
            .limit(800)
            .all()
        )
        for a in candidates:
            if done >= max_articles:
                logger.info("Per-run article cap (%d) reached.", max_articles)
                break
            if time.monotonic() - started >= budget:
                logger.info("Wall-clock budget (%ds) reached after %d analysed.",
                            int(budget), done)
                break

            text = f"{a.headline or ''} {a.description or ''}"
            if not is_important(text):
                continue

            try:
                result = analyze_article(db, a)
            except GeminiRateLimited:
                # Every provider is 429 right now — yield until next tick.
                logger.warning("All LLM providers rate-limited; "
                                "stopping run with %d analysed, %d skipped.",
                                done, skipped)
                break
            if result is None:
                skipped += 1  # bad output / unconfigured providers
                continue
            done += 1
            if done % 5 == 0:
                logger.info("auto_analyse progress: %d analysed so far", done)

        if done or skipped:
            logger.info("Auto-analyse run done: %d analysed, %d skipped.",
                        done, skipped)
    finally:
        db.close()
    return done
