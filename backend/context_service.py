"""Builds (and caches) historical context for an article from Wikipedia + GDELT.

Fetched data is persisted in ArticleContext keyed by article id so the same
article is never enriched twice.
"""
import logging

from sqlalchemy.orm import Session

from gdelt_service import get_events
from models import Article, ArticleContext
from wiki_service import fetch_entity_summaries

logger = logging.getLogger("contextnews.context")


def _get_or_fetch(db: Session, article: Article) -> ArticleContext:
    ctx = (
        db.query(ArticleContext)
        .filter(ArticleContext.article_id == article.id)
        .first()
    )
    if ctx:
        return ctx

    body = article.description or article.content or ""
    entities, wiki = fetch_entity_summaries(article.headline, body, limit=3)
    gdelt = get_events(article.headline, top=5, months=60)

    ctx = ArticleContext(
        article_id=article.id,
        entities=entities,
        wikipedia=wiki,
        gdelt=gdelt,
    )
    db.add(ctx)
    db.commit()
    db.refresh(ctx)
    logger.info(
        "Enriched article %s: %d wiki, %d gdelt",
        article.id,
        len(wiki),
        len(gdelt),
    )
    return ctx


def build_historical_context(db: Session, article: Article) -> str:
    ctx = _get_or_fetch(db, article)

    parts: list[str] = []
    if ctx.wikipedia:
        wiki_lines = [
            f"- {w.get('title')}: {w.get('extract')}" for w in ctx.wikipedia
        ]
        parts.append("WIKIPEDIA BACKGROUND ON KEY ENTITIES:\n" + "\n".join(wiki_lines))
    if ctx.gdelt:
        gdelt_lines = [
            f"- {g.get('date', '?')}: {g.get('title')} ({g.get('domain')})"
            for g in ctx.gdelt
        ]
        parts.append(
            "GDELT HISTORICAL EVENTS (last ~5 years, related coverage):\n"
            + "\n".join(gdelt_lines)
        )
    if not parts:
        return "No external historical context available."
    return "\n\n".join(parts)
