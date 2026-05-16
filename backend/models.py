from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    preferences = relationship("UserPreferences", back_populates="user", uselist=False)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    profile = Column(String, default="defence_aspirant")
    preparing_for = Column(String, nullable=True)          # NDA / CDS / SSB Direct Entry / AFCAT / Territorial Army
    journey_stage = Column(String, nullable=True)          # Just Starting / Written Cleared SSB Pending / Repeater
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    weak_areas = Column(JSON, default=list)                # list[str]
    news_scope = Column(String, default="national")        # global / national / local
    notifications = Column(JSON, default=dict)             # {breaking: bool, daily_digest: bool}
    onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    headline = Column(String, nullable=False, index=True)
    headline_norm = Column(String, index=True, nullable=True)   # normalised for dedupe
    source = Column(String, nullable=True)
    author = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    origin = Column(String, default="rss")                      # rss / newsapi / gdelt
    category = Column(String, index=True, nullable=True)         # defence/geopolitics/india/economy/government/general
    source_priority = Column(Integer, default=5, index=True)     # layer 1: 0-10 credibility
    published_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="article", uselist=False)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    causal_timeline = Column(JSON, default=list)            # [{date,event,detail,type}]
    future_consequences = Column(JSON, default=list)        # [{timeframe,consequence,likelihood}]
    defence_aspirant_impact = Column(JSON, default=dict)    # {relevance,explanation,lecturette_worthy}
    lecturette_structure = Column(JSON, default=dict)       # {opening,point_one,point_two,point_three,conclusion,estimated_minutes}
    key_terms = Column(JSON, default=list)                  # [{term,definition}]
    lecturette_category = Column(String, default="social")  # security/economic/social
    impact_level = Column(String, default="medium")         # high/medium/low
    created_at = Column(DateTime, default=datetime.utcnow)

    article = relationship("Article", back_populates="analysis")


class UserSignal(Base):
    """Layer 3: per-user behaviour. kind = 'click' (interest) | 'down' (irrelevant)."""

    __tablename__ = "user_signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    category = Column(String, index=True, nullable=True)
    kind = Column(String, nullable=False)                # 'click' | 'down'
    created_at = Column(DateTime, default=datetime.utcnow)


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)            # JSON-encoded payload
    expires_at = Column(DateTime, nullable=False, index=True)


class ArticleContext(Base):
    """Cached historical context (Wikipedia + GDELT) per article, to avoid refetch."""

    __tablename__ = "article_context"

    article_id = Column(Integer, ForeignKey("articles.id"), primary_key=True)
    entities = Column(JSON, default=list)        # ["Entity A", ...]
    wikipedia = Column(JSON, default=list)       # [{title, extract, url}]
    gdelt = Column(JSON, default=list)           # [{title, domain, date, url}]
    created_at = Column(DateTime, default=datetime.utcnow)


class LLMUsage(Base):
    """Daily per-provider counters for visibility (attempts/successes/429s)."""

    __tablename__ = "llm_usage"
    __table_args__ = (UniqueConstraint("provider", "usage_date_ist", name="uq_llm_day"),)

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)   # gemini|groq|openrouter
    usage_date_ist = Column(Date, nullable=False, index=True)
    attempts = Column(Integer, default=0)
    successes = Column(Integer, default=0)
    rate_limits = Column(Integer, default=0)


class AnalysisUsage(Base):
    __tablename__ = "analysis_usage"
    __table_args__ = (UniqueConstraint("user_id", "usage_date_ist", name="uq_user_day"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    usage_date_ist = Column(Date, nullable=False, index=True)   # IST calendar day
    count = Column(Integer, default=0)
