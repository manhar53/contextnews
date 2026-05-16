import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import extract, or_
from sqlalchemy.orm import Session

import models
import schemas
from auth import (
    assert_quota,
    consume_quota,
    create_token,
    get_current_user,
    get_usage,
    hash_password,
    next_ist_midnight_iso,
    verify_password,
)
from cache import cache_clear, cache_get, cache_set
from config import settings
from database import get_db, init_db
from gdelt_service import backfill_historic
from gemini_service import GeminiRateLimited, analyze_article
from news_service import fetch_newsapi
from rss_service import fetch_rss_feeds
from scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="ContextNews API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "newsapi_configured": bool(settings.newsapi_key),
        "gemini_configured": bool(settings.gemini_api_key),
    }


# ---------- Auth ----------

@app.post("/api/auth/signup", response_model=schemas.TokenOut)
def signup(body: schemas.SignupIn, db: Session = Depends(get_db)):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    email = body.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    prefs = models.UserPreferences(user_id=user.id)
    db.add(prefs)
    db.commit()
    return schemas.TokenOut(
        access_token=create_token(user.id), email=user.email, onboarded=False
    )


@app.post("/api/auth/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    onboarded = bool(user.preferences and user.preferences.onboarded)
    return schemas.TokenOut(
        access_token=create_token(user.id), email=user.email, onboarded=onboarded
    )


# ---------- Preferences ----------

def _prefs_for(db: Session, user: models.User) -> models.UserPreferences:
    prefs = user.preferences
    if not prefs:
        prefs = models.UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@app.get("/api/preferences", response_model=schemas.PreferencesOut)
def get_preferences(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    p = _prefs_for(db, user)
    return schemas.PreferencesOut(
        profile=p.profile,
        preparing_for=p.preparing_for,
        journey_stage=p.journey_stage,
        city=p.city,
        state=p.state,
        weak_areas=p.weak_areas or [],
        news_scope=p.news_scope,
        notifications=p.notifications or {},
        onboarded=bool(p.onboarded),
    )


@app.put("/api/preferences", response_model=schemas.PreferencesOut)
def save_preferences(
    body: schemas.PreferencesIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _prefs_for(db, user)
    p.profile = body.profile
    p.preparing_for = body.preparing_for
    p.journey_stage = body.journey_stage
    p.city = body.city
    p.state = body.state
    p.weak_areas = body.weak_areas
    p.news_scope = body.news_scope
    p.notifications = body.notifications
    p.onboarded = body.onboarded
    db.commit()
    db.refresh(p)
    return schemas.PreferencesOut(
        profile=p.profile,
        preparing_for=p.preparing_for,
        journey_stage=p.journey_stage,
        city=p.city,
        state=p.state,
        weak_areas=p.weak_areas or [],
        news_scope=p.news_scope,
        notifications=p.notifications or {},
        onboarded=bool(p.onboarded),
    )


# ---------- News feed ----------

DEFENCE_CATEGORIES = {"defence", "geopolitics"}


def _to_card(a: models.Article) -> schemas.ArticleOut:
    return schemas.ArticleOut(
        id=a.id,
        url=a.url,
        headline=a.headline,
        source=a.source,
        author=a.author,
        description=a.description,
        image_url=a.image_url,
        origin=a.origin,
        category=a.category,
        source_priority=a.source_priority,
        published_at=a.published_at,
        impact_level=a.analysis.impact_level if a.analysis else None,
        analysed=a.analysis is not None,
    )


def _user_affinity(db: Session, user_id: int):
    """Layer 3: clicks/downs aggregated per category, plus downvoted article ids."""
    rows = (
        db.query(models.UserSignal.category, models.UserSignal.kind)
        .filter(models.UserSignal.user_id == user_id)
        .all()
    )
    clicks: dict[str, int] = {}
    downs: dict[str, int] = {}
    for cat, kind in rows:
        bucket = clicks if kind == "click" else downs
        bucket[cat or ""] = bucket.get(cat or "", 0) + 1
    down_ids = {
        s.article_id
        for s in db.query(models.UserSignal.article_id)
        .filter(
            models.UserSignal.user_id == user_id,
            models.UserSignal.kind == "down",
        )
        .all()
    }
    return clicks, downs, down_ids


_PERIOD_DAYS = {"24h": 1, "7d": 7, "30d": 30, "90d": 90, "1y": 365}


@app.get("/api/news", response_model=list[schemas.ArticleOut])
def list_news(
    tab: str = "top",
    q: str | None = None,
    period: str = "30d",          # 24h | 7d | 30d | 90d | 1y | all
    year: int | None = None,      # exact publication year (overrides period)
    limit: int = Query(20, le=50),
    offset: int = 0,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current affairs first. tab: top | defence | personalised.

    Recency is the primary ordering; source credibility / personalisation are
    tiebreakers. Historic GDELT backfill is hidden from the default feed and
    only surfaced when searching, picking a year, or period=all.
    """
    query = db.query(models.Article)

    if tab == "defence":
        query = query.filter(models.Article.category.in_(DEFENCE_CATEGORIES))
    elif tab == "personalised":
        p = _prefs_for(db, user)
        if p.news_scope == "global":
            query = query.filter(
                models.Article.category.in_({"geopolitics", "economy", "general"})
            )
        elif p.news_scope == "local":
            query = query.filter(models.Article.category.in_({"india", "government"}))
        else:  # national
            query = query.filter(
                models.Article.category.in_({"india", "defence", "government"})
            )

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(models.Article.headline.ilike(like), models.Article.description.ilike(like))
        )

    # Historic (GDELT 5-yr backfill) only when explicitly wanted.
    include_historic = period == "all" or year is not None or bool(q)
    if not include_historic:
        query = query.filter(models.Article.origin != "gdelt")

    # Date window
    if year is not None:
        query = query.filter(extract("year", models.Article.published_at) == year)
    elif period != "all":
        days = _PERIOD_DAYS.get(period, 30)
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(models.Article.published_at >= cutoff)

    if tab == "personalised":
        # Recency-first, then learned affinity, then credibility. Downvoted hidden.
        clicks, downs, down_ids = _user_affinity(db, user.id)
        pool = (
            query.order_by(models.Article.published_at.desc().nullslast())
            .limit(500)
            .all()
        )

        def affinity(a: models.Article) -> float:
            cat = a.category or ""
            return 1.5 * clicks.get(cat, 0) - 1.0 * downs.get(cat, 0)

        ranked = sorted(
            (a for a in pool if a.id not in down_ids),
            key=lambda a: (
                a.published_at or datetime.min,   # current affairs first
                affinity(a),                       # then personalisation
                a.source_priority or 5,            # then credibility
            ),
            reverse=True,
        )
        return [_to_card(a) for a in ranked[offset : offset + limit]]

    # top / defence: recency first, source credibility as tiebreaker.
    cache_key = (
        f"news:{tab}:{period}:{year}:{offset}:{limit}" if not q else None
    )
    if cache_key:
        cached = cache_get(db, cache_key)
        if cached is not None:
            return cached

    rows = (
        query.order_by(
            models.Article.published_at.desc().nullslast(),
            models.Article.source_priority.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    result = [_to_card(a) for a in rows]
    if cache_key:
        cache_set(
            db,
            cache_key,
            [r.model_dump() for r in result],
            settings.feed_cache_ttl_seconds,
        )
    return result


@app.get("/api/news/{article_id}", response_model=schemas.ArticleDetailOut)
def get_news_detail(
    article_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the article + cached analysis (if already deep-analysed)."""
    a = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Article not found")
    analysis = a.analysis
    return schemas.ArticleDetailOut(
        id=a.id,
        url=a.url,
        headline=a.headline,
        source=a.source,
        author=a.author,
        description=a.description,
        image_url=a.image_url,
        origin=a.origin,
        category=a.category,
        published_at=a.published_at,
        content=a.content,
        impact_level=analysis.impact_level if analysis else None,
        analysed=analysis is not None,
        analysis=schemas.AnalysisOut.model_validate(analysis) if analysis else None,
    )


@app.post("/api/news/{article_id}/analyze", response_model=schemas.ArticleDetailOut)
def deep_analyze(
    article_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run Gemini deep analysis. Rate-limited to N/day per user (IST reset).

    Cached analyses are returned free (do not consume quota).
    """
    a = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Article not found")

    if a.analysis is None:
        usage = assert_quota(db, user.id)  # 429 if user's daily limit hit
        try:
            analysis = analyze_article(db, a)
        except GeminiRateLimited:
            raise HTTPException(
                status_code=429,
                detail="Gemini is rate-limited on the free tier. Wait ~30s and retry — this did not use your daily quota.",
            )
        if analysis is None:
            raise HTTPException(
                status_code=502,
                detail="Gemini analysis failed (check GEMINI_API_KEY / model). Quota not consumed.",
            )
        consume_quota(db, usage)  # only on success
    else:
        analysis = a.analysis

    return schemas.ArticleDetailOut(
        id=a.id,
        url=a.url,
        headline=a.headline,
        source=a.source,
        author=a.author,
        description=a.description,
        image_url=a.image_url,
        origin=a.origin,
        category=a.category,
        published_at=a.published_at,
        content=a.content,
        impact_level=analysis.impact_level,
        analysed=True,
        analysis=schemas.AnalysisOut.model_validate(analysis),
    )


@app.get("/api/usage", response_model=schemas.UsageOut)
def usage(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    u = get_usage(db, user.id)
    return schemas.UsageOut(
        used=u.count,
        limit=settings.daily_analysis_limit,
        remaining=max(0, settings.daily_analysis_limit - u.count),
        resets_at_ist=next_ist_midnight_iso(),
    )


def _record_signal(db: Session, user_id: int, article_id: int, kind: str):
    a = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Article not found")
    db.add(
        models.UserSignal(
            user_id=user_id,
            article_id=article_id,
            category=a.category,
            kind=kind,
        )
    )
    db.commit()


@app.post("/api/news/{article_id}/click")
def signal_click(
    article_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Layer 3: opening an article signals interest in its category."""
    _record_signal(db, user.id, article_id, "click")
    return {"ok": True}


@app.post("/api/news/{article_id}/feedback")
def signal_feedback(
    article_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Layer 3: thumbs-down — hide this article and down-weight its category."""
    _record_signal(db, user.id, article_id, "down")
    return {"ok": True}


@app.post("/api/news/refresh")
def refresh_news(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Manually trigger both ingestion jobs and invalidate the feed cache."""
    rss = fetch_rss_feeds()
    napi = fetch_newsapi()
    cache_clear(db, prefix="news:")
    return {"rss_new": rss, "newsapi_new": napi}


@app.post("/api/news/backfill")
def backfill(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """One-shot GDELT historic backfill (~12 months) for causal depth."""
    added = backfill_historic()
    cache_clear(db, prefix="news:")
    return {"historic_added": added}


@app.get("/api/news/{article_id}/export")
def export_analysis(
    article_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export the article's analysis as a Markdown lecturette brief."""
    a = db.query(models.Article).filter(models.Article.id == article_id).first()
    if not a or not a.analysis:
        raise HTTPException(status_code=404, detail="No analysis to export")
    an = a.analysis
    lec = an.lecturette_structure or {}
    dai = an.defence_aspirant_impact or {}
    lines = [
        f"# {a.headline}",
        f"_{a.source or ''} · {a.published_at or ''} · impact: {an.impact_level}_",
        "",
        "## Summary",
        an.summary or "",
        "",
        "## Causal Timeline",
    ]
    for n in an.causal_timeline or []:
        lines.append(f"- **[{n.get('type')}]** {n.get('date')} — {n.get('event')}: {n.get('detail')}")
    lines += ["", "## Projected Consequences"]
    for f in an.future_consequences or []:
        lines.append(f"- ({f.get('timeframe')}, {f.get('likelihood')}) {f.get('consequence')}")
    lines += [
        "",
        "## What this means for you",
        f"Relevance: {dai.get('relevance')}",
        dai.get("explanation", ""),
        "",
        f"## Lecturette (~{lec.get('estimated_minutes', 3)} min)",
        f"**Opening:** {lec.get('opening', '')}",
        f"1. {lec.get('point_one', '')}",
        f"2. {lec.get('point_two', '')}",
        f"3. {lec.get('point_three', '')}",
        f"**Conclusion:** {lec.get('conclusion', '')}",
        "",
        "## Key Terms",
    ]
    for kt in an.key_terms or []:
        if isinstance(kt, dict):
            lines.append(f"- **{kt.get('term')}** — {kt.get('definition', '')}")
        else:
            lines.append(f"- {kt}")
    md = "\n".join(lines)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="contextnews-{article_id}.md"'
        },
    )
