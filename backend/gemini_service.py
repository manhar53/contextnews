"""Gemini deep analysis with multi-model fallback + schema validation."""
import json
import logging
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from config import settings
from context_service import build_historical_context
from models import Analysis, Article

logger = logging.getLogger("contextnews.gemini")


class GeminiRateLimited(Exception):
    """Raised only when every configured model returns a 429 quota error."""


SYSTEM_PROMPT = """You are an expert geopolitical analyst, defence affairs specialist, and current affairs educator with deep knowledge of Indian defence, foreign policy, and global events.
Given a news article, respond ONLY in valid JSON with these exact fields:
{
 "summary": "string (2 sentences, factual and clear)",
 "causal_timeline": [
   {
     "date": "string",
     "event": "string (title, max 8 words)",
     "detail": "string (2 sentences explaining significance)",
     "type": "root_cause | development | current | consequence"
   }
 ],
 "future_consequences": [
   {
     "timeframe": "string (e.g. 3 months, 1 year)",
     "consequence": "string",
     "likelihood": "high | medium | low"
   }
 ],
 "defence_aspirant_impact": {
   "relevance": "high | medium | low",
   "explanation": "string (3 sentences, specific to SSB and defence exam preparation)",
   "lecturette_worthy": true
 },
 "lecturette_structure": {
   "opening": "string",
   "point_one": "string",
   "point_two": "string",
   "point_three": "string",
   "conclusion": "string",
   "estimated_minutes": 3
 },
 "lecturette_category": "security | economic | social",
 "impact_level": "high | medium | low",
 "key_terms": [{"term": "string", "definition": "string (one line)"}]
}
The causal_timeline MUST be ordered oldest-first and include exactly one node of type "current" for the article's main event, with root_cause first and consequence nodes (if any) last.

LECTURETTE CRAFT — the SSB lecturette assesses a candidate's articulation and awareness of contemporary events (global, and India in particular). Build lecturette_structure so a speaker can achieve the three aims of public speaking:
1. get into your subject — opening must show command of facts/context;
2. get your subject into yourself — the three points must let the speaker reason and take a clear stance, not just list facts;
3. get your subject into the heart of the audience — the conclusion must connect to national interest / the listener and end with conviction.
Use crisp, speakable sentences (not written prose); each point one idea; estimated_minutes ~3.
Set lecturette_category to the single best fit: "security" (defence, military, terrorism, borders, strategic affairs), "economic" (economy, trade, budget, industry, energy), or "social" (society, governance, education, health, environment, polity).

You are analysing news specifically for Indian defence aspirants preparing for SSB, NDA, CDS, and AFCAT.
Prioritise and give higher relevance scores (defence_aspirant_impact.relevance and impact_level) to these topics, in this order:
1. Indian armed forces operations and policy
2. India border tensions (China, Pakistan)
3. Indian defence acquisitions and technology
4. Geopolitical events affecting India
5. Indian foreign policy and diplomacy
6. Defence budget and government schemes
7. Global conflicts with Indian strategic interest
8. Indian economy affecting defence capability
9. General government policy
10. Global news with indirect India impact

Deprioritise (assign low relevance and low impact_level):
- Entertainment and sports
- State-level politics unless defence relevant
- Corporate news unless defence sector
- Weather and natural disasters unless strategic impact

Draw on your full historical training knowledge combined with the provided Wikipedia summaries and GDELT events to build the deepest possible causal timeline. Connect current events to their historical roots even if they go back decades."""


# ---------- Schema validation (improvement #5) ----------

def _norm_level(v: Any) -> str:
    s = str(v or "").lower().strip()
    return s if s in {"high", "medium", "low"} else "medium"


class TimelineNode(BaseModel):
    date: str = ""
    event: str
    detail: str = ""
    type: str = "development"

    @field_validator("type")
    @classmethod
    def _vtype(cls, v: str) -> str:
        v = (v or "").lower().strip()
        return v if v in {"root_cause", "development", "current", "consequence"} else "development"


class FutureItem(BaseModel):
    timeframe: str = ""
    consequence: str
    likelihood: str = "medium"

    @field_validator("likelihood")
    @classmethod
    def _vl(cls, v: str) -> str:
        return _norm_level(v)


class DefenceImpact(BaseModel):
    relevance: str = "medium"
    explanation: str = ""
    lecturette_worthy: bool = False

    @field_validator("relevance")
    @classmethod
    def _vr(cls, v: str) -> str:
        return _norm_level(v)


class Lecturette(BaseModel):
    opening: str = ""
    point_one: str = ""
    point_two: str = ""
    point_three: str = ""
    conclusion: str = ""
    estimated_minutes: float = 3


class KeyTerm(BaseModel):
    term: str
    definition: str = ""


class GeminiPayload(BaseModel):
    summary: str = ""
    causal_timeline: list[TimelineNode] = Field(default_factory=list)
    future_consequences: list[FutureItem] = Field(default_factory=list)
    defence_aspirant_impact: DefenceImpact = Field(default_factory=DefenceImpact)
    lecturette_structure: Lecturette = Field(default_factory=Lecturette)
    lecturette_category: str = "social"
    impact_level: str = "medium"
    key_terms: list[KeyTerm] = Field(default_factory=list)

    @field_validator("impact_level")
    @classmethod
    def _vi(cls, v: str) -> str:
        return _norm_level(v)

    @field_validator("lecturette_category")
    @classmethod
    def _vlc(cls, v: str) -> str:
        s = str(v or "").lower().strip()
        return s if s in {"security", "economic", "social"} else "social"


# ---------- Gemini call with fallback (improvement #1) ----------

_configured = False


def _ensure_configured() -> bool:
    global _configured
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set; analysis unavailable.")
        return False
    if not _configured:
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True
    return True


def _user_content(db: Session, article: Article) -> str:
    return (
        f"HEADLINE: {article.headline}\n"
        f"SOURCE: {article.source or 'Unknown'}\n"
        f"AUTHOR: {article.author or 'Unknown'}\n"
        f"PUBLISHED: {article.published_at}\n"
        f"DESCRIPTION: {article.description or ''}\n"
        f"CONTENT: {article.content or ''}\n"
        f"URL: {article.url}\n\n"
        f"{build_historical_context(db, article)}"
    )


def _is_rate_limit(exc: Exception) -> bool:
    name = type(exc).__name__
    return name in {"ResourceExhausted", "TooManyRequests"} or "429" in str(exc)


def _models() -> list[str]:
    chain = [settings.gemini_model]
    if settings.gemini_fallback_model and settings.gemini_fallback_model not in chain:
        chain.append(settings.gemini_fallback_model)
    return chain


def _try_models(content: str) -> tuple[dict | None, bool]:
    """One pass over the model chain. Returns (payload|None, all_rate_limited)."""
    all_rate_limited = True
    for model_name in _models():
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.4,
                },
            )
            resp = model.generate_content(content)
            return json.loads(resp.text), False
        except json.JSONDecodeError as exc:
            logger.error("Model %s returned non-JSON: %s", model_name, exc)
            all_rate_limited = False
            continue
        except Exception as exc:  # noqa: BLE001
            if _is_rate_limit(exc):
                logger.warning("Model %s rate-limited.", model_name)
                continue
            logger.error("Model %s failed: %s", model_name, exc)
            all_rate_limited = False
            continue
    return None, all_rate_limited


def _generate(db: Session, article: Article) -> dict | None:
    """Try the model chain; on a full rate-limit, auto-retry once after a
    short backoff so users don't have to manually retry."""
    import time

    content = _user_content(db, article)
    for attempt in (1, 2):
        payload, all_rl = _try_models(content)
        if payload is not None:
            return payload
        if not all_rl:
            return None  # a non-rate-limit failure — don't burn time retrying
        if attempt == 1:
            logger.warning("All models rate-limited; backing off 8s then retrying.")
            time.sleep(8)
    raise GeminiRateLimited()


def analyze_article(db: Session, article: Article) -> Analysis | None:
    """Return cached analysis, or generate + validate + persist a new one."""
    if article.analysis:
        return article.analysis
    if not _ensure_configured():
        return None

    raw = _generate(db, article)  # may raise GeminiRateLimited
    if raw is None:
        return None

    try:
        payload = GeminiPayload.model_validate(raw)
    except ValidationError as exc:
        logger.error("Gemini payload failed schema validation for %s: %s", article.id, exc)
        return None

    analysis = Analysis(
        article_id=article.id,
        summary=payload.summary,
        causal_timeline=[n.model_dump() for n in payload.causal_timeline],
        future_consequences=[f.model_dump() for f in payload.future_consequences],
        defence_aspirant_impact=payload.defence_aspirant_impact.model_dump(),
        lecturette_structure=payload.lecturette_structure.model_dump(),
        lecturette_category=payload.lecturette_category,
        key_terms=[k.model_dump() for k in payload.key_terms],
        impact_level=payload.impact_level,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
