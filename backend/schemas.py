from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, field_serializer


# ---------- Auth ----------

class SignupIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthIn(BaseModel):
    credential: str   # Google Identity Services ID token (JWT)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    onboarded: bool


# ---------- Preferences ----------

class PreferencesIn(BaseModel):
    profile: str = "defence_aspirant"
    city: Optional[str] = None
    state: Optional[str] = None
    weak_areas: list[str] = []
    news_scopes: list[str] = ["national"]   # any of global/national/local
    notifications: dict[str, Any] = {}
    onboarded: bool = True


class PreferencesOut(BaseModel):
    profile: str
    city: Optional[str] = None
    state: Optional[str] = None
    weak_areas: list[str] = []
    news_scopes: list[str] = ["national"]
    notifications: dict[str, Any] = {}
    onboarded: bool = False

    class Config:
        from_attributes = True


# ---------- Analysis / Articles ----------

class AnalysisOut(BaseModel):
    summary: Optional[str] = None
    causal_timeline: list[dict[str, Any]] = []
    future_consequences: list[dict[str, Any]] = []
    defence_aspirant_impact: dict[str, Any] = {}
    lecturette_structure: dict[str, Any] = {}
    lecturette_category: str = "social"
    key_terms: list[Any] = []
    impact_level: str = "medium"

    class Config:
        from_attributes = True


class ArticleOut(BaseModel):
    id: int
    url: str
    headline: str
    source: Optional[str]
    author: Optional[str] = None
    description: Optional[str]
    image_url: Optional[str]
    origin: Optional[str] = None
    category: Optional[str]
    source_priority: Optional[int] = 5
    published_at: Optional[datetime]
    impact_level: Optional[str] = None
    lecturette_category: Optional[str] = None
    important: bool = False
    analysed: bool = False

    @field_serializer("published_at")
    def _ser_dt(self, dt: Optional[datetime]) -> Optional[str]:
        """Always emit timestamps as UTC ISO so browser `new Date()` reads correctly."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True


class ArticleDetailOut(ArticleOut):
    content: Optional[str] = None
    analysis: Optional[AnalysisOut] = None


class UsageOut(BaseModel):
    used: int
    limit: int
    remaining: int
    resets_at_ist: str
    unlimited: bool = False
