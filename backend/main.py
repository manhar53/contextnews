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
        "google_login_enabled": bool(settings.google_client_id),
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


@app.post("/api/auth/google", response_model=schemas.TokenOut)
def google_auth(body: schemas.GoogleAuthIn, db: Session = Depends(get_db)):
    """Verify a Google Identity Services ID token; create/link the user."""
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="Google login is not configured")
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token

        info = id_token.verify_oauth2_token(
            body.credential, g_requests.Request(), settings.google_client_id
        )
    except Exception:  # noqa: BLE001  invalid/expired/wrong-audience token
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = (info.get("email") or "").lower()
    if not email or not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email not verified")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        import secrets

        user = models.User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),  # unusable pw
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(models.UserPreferences(user_id=user.id))
        db.commit()
    onboarded = bool(user.preferences and user.preferences.onboarded)
    return schemas.TokenOut(
        access_token=create_token(user.id), email=user.email, onboarded=onboarded
    )


# ---------- Preferences ----------

def _is_owner(user: models.User) -> bool:
    return bool(
        settings.owner_email
        and user.email
        and user.email.lower() == settings.owner_email.lower()
    )


def _prefs_for(db: Session, user: models.User) -> models.UserPreferences:
    prefs = user.preferences
    if not prefs:
        prefs = models.UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def _scopes_of(p: models.UserPreferences) -> list[str]:
    raw = p.news_scope or "national"
    vals = raw.split(",") if isinstance(raw, str) else list(raw)
    out = [v.strip() for v in vals if v and v.strip() in {"global", "national", "local"}]
    return out or ["national"]


def _prefs_out(p: models.UserPreferences) -> schemas.PreferencesOut:
    return schemas.PreferencesOut(
        profile=p.profile,
        city=p.city,
        state=p.state,
        weak_areas=p.weak_areas or [],
        news_scopes=_scopes_of(p),
        notifications=p.notifications or {},
        onboarded=bool(p.onboarded),
    )


@app.get("/api/preferences", response_model=schemas.PreferencesOut)
def get_preferences(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _prefs_out(_prefs_for(db, user))


@app.put("/api/preferences", response_model=schemas.PreferencesOut)
def save_preferences(
    body: schemas.PreferencesIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _prefs_for(db, user)
    p.profile = body.profile
    p.city = body.city
    p.state = body.state
    p.weak_areas = body.weak_areas
    scopes = [s for s in body.news_scopes if s in {"global", "national", "local"}]
    p.news_scope = ",".join(scopes or ["national"])
    p.notifications = body.notifications
    p.onboarded = body.onboarded
    db.commit()
    db.refresh(p)
    return _prefs_out(p)


# ---------- News feed ----------

DEFENCE_CATEGORIES = {"defence", "geopolitics"}


# Lecturette buckets: security / economic / social (SSB lecturette themes).
_SES_BY_CATEGORY = {
    "defence": "security",
    "geopolitics": "security",
    "economy": "economic",
    "india": "social",
    "government": "social",
    "general": "social",
}


def _ses(a: models.Article) -> str:
    """Precise Gemini category if analysed, else heuristic from feed category."""
    if a.analysis and a.analysis.lecturette_category in {
        "security",
        "economic",
        "social",
    }:
        return a.analysis.lecturette_category
    return _SES_BY_CATEGORY.get(a.category or "", "social")


def _to_card(a: models.Article) -> schemas.ArticleOut:
    from topics import is_important

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
        lecturette_category=_ses(a),
        important=is_important(f"{a.headline or ''} {a.description or ''}"),
        analysed=a.analysis is not None,
    )


def _user_affinity(db: Session, user_id: int):
    """Per-user category leanings from this user's own clicks/ups/downs.

    No content is hidden — these only gently personalise ordering.
    """
    rows = (
        db.query(models.UserSignal.category, models.UserSignal.kind)
        .filter(models.UserSignal.user_id == user_id)
        .all()
    )
    likes: dict[str, int] = {}
    dislikes: dict[str, int] = {}
    for cat, kind in rows:
        if kind in ("click", "up"):
            likes[cat or ""] = likes.get(cat or "", 0) + 1
        elif kind == "down":
            dislikes[cat or ""] = dislikes.get(cat or "", 0) + 1
    return likes, dislikes


def _crowd_scores(db: Session, ids: list[int]) -> dict[int, float]:
    """Aggregate everyone's votes per article -> a global ranking nudge.

    Mass review, not one person's tap: up = strong +, click = mild +,
    down = strong -. Applied to the feed for all users.
    """
    if not ids:
        return {}
    from sqlalchemy import func

    rows = (
        db.query(
            models.UserSignal.article_id,
            models.UserSignal.kind,
            func.count().label("n"),
        )
        .filter(models.UserSignal.article_id.in_(ids))
        .group_by(models.UserSignal.article_id, models.UserSignal.kind)
        .all()
    )
    agg: dict[int, dict[str, int]] = {}
    for aid, kind, n in rows:
        agg.setdefault(aid, {})[kind] = n
    out: dict[int, float] = {}
    for aid, k in agg.items():
        net = k.get("up", 0) - k.get("down", 0)
        score = 6.0 * net + 0.25 * k.get("click", 0)
        # Bounded so a brigade can't fully hijack or bury relevance.
        out[aid] = max(-30.0, min(30.0, score))
    return out


_PERIOD_DAYS = {"24h": 1, "7d": 7, "30d": 30, "90d": 90, "1y": 365}

_SCOPE_CATEGORIES = {
    "global": {"geopolitics", "economy", "general"},
    "national": {"india", "defence", "government"},
    "local": {"india", "government"},
}

# Defence-aspirant topical relevance keywords -> weight.
_RELEVANCE_KW: dict[str, int] = {
    "india": 3, "indian": 3, "defence": 4, "defense": 4, "military": 4,
    "army": 4, "navy": 4, "air force": 4, "iaf": 4, "drdo": 4, "isro": 2,
    "missile": 3, "border": 3, "china": 3, "pakistan": 3, "ladakh": 3,
    "loc": 2, "lac": 3, "galwan": 3, "kashmir": 3, "ssb": 3, "nda": 2,
    "cds": 2, "afcat": 2, "soldier": 2, "war": 3, "security": 2,
    "geopolitic": 3, "diplomacy": 2, "ministry of defence": 4,
    "armed forces": 4, "terror": 3, "insurgency": 2, "indo-pacific": 3,
    "quad": 2, "brahmos": 3, "tejas": 3, "submarine": 3, "regiment": 2,
    "paramilitary": 2, "strategic": 2, "frontier": 2, "naval": 3,
    "aircraft": 2, "warship": 3, "defence ministry": 4, "s-400": 3,
    "rafale": 3, "sukhoi": 2, "border security": 3, "ceasefire": 2,
}
_IMPACT_BOOST = {"high": 8, "medium": 4, "low": 1}

# Weak area -> categories it should up-rank in the Personalised feed.
_WEAK_CATEGORIES = {
    "Defence News": {"defence"},
    "Geopolitics": {"geopolitics"},
    "International Relations": {"geopolitics"},
    "Indian Economy": {"economy"},
}
# These weak areas favour deeply-analysed / high-impact pieces instead.
_WEAK_DEPTH = {"Current Affairs Depth", "Lecturette Topics"}


def _weak_match(a: models.Article, weak: set[str]) -> int:
    """1 if the article matches a selected weak area (priority tier), else 0."""
    if not weak:
        return 0
    for w in weak:
        if a.category in _WEAK_CATEGORIES.get(w, ()):
            return 1
    if weak & _WEAK_DEPTH and a.analysis and a.analysis.impact_level in {"high", "medium"}:
        return 1
    return 0


def _freshness(a: models.Article) -> float:
    if not a.published_at:
        return 0.0
    age_d = (datetime.utcnow() - a.published_at).total_seconds() / 86400
    return max(0.0, 12.0 - age_d * 0.4)


def _topical(a: models.Article) -> int:
    text = f"{a.headline or ''} {a.description or ''}".lower()
    score = sum(w for kw, w in _RELEVANCE_KW.items() if kw in text)
    return min(score, 24)


def _impact_boost(a: models.Article) -> int:
    return _IMPACT_BOOST.get(a.analysis.impact_level if a.analysis else "", 0)


def _relevance(a: models.Article, affinity: float = 0.0) -> float:
    """Defence-topical ranking — for the Defence tab and Personalised affinity."""
    return _topical(a) + float(a.source_priority or 5) + _impact_boost(a) + _freshness(a) + affinity


def _general_score(a: models.Article) -> float:
    """Top Stories — broadest-importance score, NOT defence-keyword biased.

    Surfaces the biggest stories of the day across all categories so this tab
    is distinct from the Defence tab.
    """
    cred = float(a.source_priority or 5)
    return cred * 1.4 + _impact_boost(a) * 1.5 + _freshness(a) * 1.5


@app.get("/api/news", response_model=list[schemas.ArticleOut])
def list_news(
    tab: str = "top",
    q: str | None = None,
    period: str = "30d",          # 24h | 7d | 30d | 90d | 1y | all
    year: int | None = None,      # exact publication year (overrides period)
    lecturette: str | None = None,  # security | economic | social
    limit: int = Query(20, le=50),
    offset: int = 0,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Relevance-prioritised within a freshness window. tab: top | defence |
    personalised. Order = defence-topical relevance + credibility + analysed
    impact + freshness (+ personal affinity). Historic GDELT is hidden unless
    searching, a year, or period=all is chosen.
    """
    query = db.query(models.Article)

    if tab == "defence":
        query = query.filter(models.Article.category.in_(DEFENCE_CATEGORIES))
    elif tab == "personalised":
        p = _prefs_for(db, user)
        cats: set[str] = set()
        for sc in _scopes_of(p):
            cats |= _SCOPE_CATEGORIES.get(sc, set())
        query = query.filter(models.Article.category.in_(cats or {"india"}))

    if q:
        # Tokenised search: each word (>=2 chars) matches headline/desc; ANY
        # token hit wins. Lets "modi ji" return Modi articles, "india china
        # border" return either, etc.
        import re

        tokens = [t for t in re.findall(r"[A-Za-z0-9]{2,}", q) if t]
        if tokens:
            conds = []
            for t in tokens:
                like = f"%{t}%"
                conds.append(models.Article.headline.ilike(like))
                conds.append(models.Article.description.ilike(like))
            query = query.filter(or_(*conds))
        else:
            like = f"%{q.strip()}%"
            query = query.filter(
                or_(models.Article.headline.ilike(like), models.Article.description.ilike(like))
            )

    include_historic = period == "all" or year is not None or bool(q)
    if not include_historic:
        query = query.filter(models.Article.origin != "gdelt")

    if year is not None:
        query = query.filter(extract("year", models.Article.published_at) == year)
    elif period != "all":
        days = _PERIOD_DAYS.get(period, 30)
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(models.Article.published_at >= cutoff)

    les = lecturette if lecturette in {"security", "economic", "social"} else None

    cache_key = (
        f"news:{tab}:{period}:{year}:{les}:{offset}:{limit}"
        if tab != "personalised" and not q
        else None
    )
    if cache_key:
        cached = cache_get(db, cache_key)
        if cached is not None:
            return cached

    # Candidate pool ordered by recency, then ranked by relevance in Python.
    pool = (
        query.order_by(models.Article.published_at.desc().nullslast())
        .limit(600)
        .all()
    )
    if les:  # SSB lecturette-prep filter
        pool = [a for a in pool if _ses(a) == les]
    # Crowd score: everyone's aggregated votes nudge the feed for all users.
    crowd = _crowd_scores(db, [a.id for a in pool])

    if tab == "personalised":
        likes, dislikes = _user_affinity(db, user.id)
        weak = set(p.weak_areas or [])
        from topics import is_important

        def aff(a: models.Article) -> float:
            c = a.category or ""
            # mild personal lean; nothing is hidden
            return 1.0 * likes.get(c, 0) - 0.5 * dislikes.get(c, 0)

        def imp(a: models.Article) -> int:
            return 1 if is_important(f"{a.headline or ''} {a.description or ''}") else 0

        # Tiered ranking for defence aspirants:
        #   1) ★ important AFPA topics float to the very top,
        #   2) then articles matching their weak areas,
        #   3) then relevance + crowd + recency within.
        ranked = sorted(
            pool,
            key=lambda a: (
                imp(a),
                _weak_match(a, weak),
                _relevance(a, aff(a)) + crowd.get(a.id, 0.0),
                a.published_at or datetime.min,
            ),
            reverse=True,
        )
        return [_to_card(a) for a in ranked[offset : offset + limit]]

    score_fn = _general_score if tab == "top" else _relevance

    def _diversify_top(items: list, per_cat: int) -> list:
        """Cap each category so Top Stories shows a real cross-topic mix."""
        counts: dict[str, int] = {}
        out, overflow = [], []
        for a in items:
            c = a.category or ""
            if counts.get(c, 0) < per_cat:
                counts[c] = counts.get(c, 0) + 1
                out.append(a)
            else:
                overflow.append(a)
        return out + overflow  # overflow appended so pagination still works

    ranked = sorted(
        pool,
        key=lambda a: (
            score_fn(a) + crowd.get(a.id, 0.0),
            a.published_at or datetime.min,
        ),
        reverse=True,
    )
    if tab == "top":
        # cross-category mix so Top is visibly broader than Defence
        ranked = _diversify_top(ranked, per_cat=max(2, limit // 3))
    result = [_to_card(a) for a in ranked[offset : offset + limit]]
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
        owner = _is_owner(user)
        usage = None if owner else assert_quota(db, user.id)
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
        if usage is not None:
            consume_quota(db, usage)  # owners bypass the daily limit
    else:
        analysis = a.analysis  # cached → free for everyone, no quota spent

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
    if _is_owner(user):
        return schemas.UsageOut(
            used=0,
            limit=settings.daily_analysis_limit,
            remaining=settings.daily_analysis_limit,
            resets_at_ist=next_ist_midnight_iso(),
            unlimited=True,
        )
    u = get_usage(db, user.id)
    return schemas.UsageOut(
        used=u.count,
        limit=settings.daily_analysis_limit,
        remaining=max(0, settings.daily_analysis_limit - u.count),
        resets_at_ist=next_ist_midnight_iso(),
        unlimited=False,
    )


@app.get("/api/admin/stats")
def admin_stats(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Owner-only operational snapshot — users, analyses, LLM provider health."""
    if not _is_owner(user):
        raise HTTPException(status_code=403, detail="Owner only")
    from sqlalchemy import func

    from auth import ist_today

    today = ist_today()
    users_total = db.query(func.count(models.User.id)).scalar() or 0
    articles_total = db.query(func.count(models.Article.id)).scalar() or 0
    analyses_total = db.query(func.count(models.Analysis.id)).scalar() or 0
    since = datetime.utcnow() - timedelta(hours=24)
    analyses_24h = (
        db.query(func.count(models.Analysis.id))
        .filter(models.Analysis.created_at >= since)
        .scalar()
        or 0
    )
    users_at_limit = (
        db.query(func.count(models.AnalysisUsage.id))
        .filter(
            models.AnalysisUsage.usage_date_ist == today,
            models.AnalysisUsage.count >= settings.daily_analysis_limit,
        )
        .scalar()
        or 0
    )
    provider_rows = (
        db.query(models.LLMUsage)
        .filter(models.LLMUsage.usage_date_ist == today)
        .all()
    )
    providers_today = [
        {
            "provider": r.provider,
            "attempts": r.attempts or 0,
            "successes": r.successes or 0,
            "rate_limits": r.rate_limits or 0,
        }
        for r in provider_rows
    ]
    last = (
        db.query(models.Analysis)
        .order_by(models.Analysis.created_at.desc())
        .first()
    )
    return {
        "users": users_total,
        "articles": articles_total,
        "analyses_total": analyses_total,
        "analyses_24h": analyses_24h,
        "users_at_daily_limit_today": users_at_limit,
        "providers_today": providers_today,
        "last_analysis_at": last.created_at.isoformat() if last else None,
        "configured": {
            "gemini": bool(settings.gemini_api_key),
            "groq": bool(settings.groq_api_key),
            "openrouter": bool(settings.openrouter_api_key),
        },
        "daily_limit_per_user": settings.daily_analysis_limit,
        "auto_analyse_per_run": settings.auto_analyse_per_run,
    }


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


@app.post("/api/news/{article_id}/upvote")
def signal_upvote(
    article_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thumbs-up — a positive crowd vote (nothing is hidden/removed)."""
    _record_signal(db, user.id, article_id, "up")
    return {"ok": True}


@app.post("/api/news/{article_id}/feedback")
def signal_feedback(
    article_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thumbs-down — a negative crowd vote. Content is NOT removed for anyone;
    it only lowers the article's aggregate ranking score."""
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
