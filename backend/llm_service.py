"""Multi-provider LLM chain for JSON-mode generation.

Providers tried in `LLM_PROVIDER_ORDER` order; only those with an API key
configured run. On a 429-style rate-limit, fall through to the next. Raises
`AllProvidersRateLimited` only when every configured provider returns 429.

Tracks per-day per-provider counters in the LLMUsage table for visibility.
"""
import json
import logging

import httpx

from auth import IST
from config import settings
from datetime import datetime
from database import SessionLocal
from models import LLMUsage

logger = logging.getLogger("contextnews.llm")


class AllProvidersRateLimited(Exception):
    """Every configured provider returned a 429 / quota error."""


def _is_rate_limit(exc: Exception) -> bool:
    name = type(exc).__name__
    return name in {"ResourceExhausted", "TooManyRequests"} or "429" in str(exc)


def _log(provider: str, kind: str) -> None:
    db = SessionLocal()
    try:
        today = datetime.now(IST).date()
        row = (
            db.query(LLMUsage)
            .filter(LLMUsage.provider == provider, LLMUsage.usage_date_ist == today)
            .first()
        )
        if not row:
            row = LLMUsage(provider=provider, usage_date_ist=today)
            db.add(row)
            db.flush()
        if kind == "attempt":
            row.attempts = (row.attempts or 0) + 1
        elif kind == "success":
            row.successes = (row.successes or 0) + 1
        elif kind == "rate_limit":
            row.rate_limits = (row.rate_limits or 0) + 1
        db.commit()
    except Exception:  # noqa: BLE001  observability must never break analysis
        db.rollback()
    finally:
        db.close()


# ---------- Providers ----------

def _gemini(system: str, user: str) -> dict | None:
    if not settings.gemini_api_key:
        return None
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    for model_name in [settings.gemini_model, settings.gemini_fallback_model]:
        if not model_name:
            continue
        _log("gemini", "attempt")
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.4,
                },
            )
            resp = model.generate_content(user)
            data = json.loads(resp.text)
            _log("gemini", "success")
            return data
        except json.JSONDecodeError as exc:
            logger.error("Gemini %s returned non-JSON: %s", model_name, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            if _is_rate_limit(exc):
                _log("gemini", "rate_limit")
                logger.warning("Gemini model %s rate-limited.", model_name)
                continue
            logger.error("Gemini %s failed: %s", model_name, exc)
            return None
    raise AllProvidersRateLimited()  # all Gemini models 429 -> signal upstream


def _strip_json(text: str) -> str:
    """Some open models wrap JSON in ```json fences. Strip them."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    return t.strip()


def _openai_compat(provider: str, base_url: str, api_key: str, model: str,
                    system: str, user: str, extra_headers: dict | None = None) -> dict | None:
    _log(provider, "attempt")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    body = {
        "model": model,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": user + "\n\nRespond with valid JSON only — no markdown, no commentary.",
            },
        ],
    }
    try:
        r = httpx.post(base_url, headers=headers, json=body, timeout=90)
    except httpx.HTTPError as exc:
        logger.error("%s network failed: %s", provider, exc)
        return None
    if r.status_code == 429:
        _log(provider, "rate_limit")
        logger.warning("%s rate-limited.", provider)
        raise AllProvidersRateLimited()
    if r.status_code >= 400:
        logger.error("%s HTTP %s: %s", provider, r.status_code, r.text[:200])
        return None
    try:
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        out = json.loads(_strip_json(text))
        _log(provider, "success")
        return out
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.error("%s bad response: %s", provider, exc)
        return None


def _groq(system: str, user: str) -> dict | None:
    if not settings.groq_api_key:
        return None
    return _openai_compat(
        "groq",
        "https://api.groq.com/openai/v1/chat/completions",
        settings.groq_api_key,
        settings.groq_model,
        system,
        user,
    )


def _openrouter(system: str, user: str) -> dict | None:
    if not settings.openrouter_api_key:
        return None
    return _openai_compat(
        "openrouter",
        "https://openrouter.ai/api/v1/chat/completions",
        settings.openrouter_api_key,
        settings.openrouter_model,
        system,
        user,
        extra_headers={
            "HTTP-Referer": "https://contextnews-api.onrender.com",
            "X-Title": "ContextNews",
        },
    )


_PROVIDERS = {"gemini": _gemini, "groq": _groq, "openrouter": _openrouter}


def generate_json(system: str, user: str) -> dict | None:
    """Run the configured provider chain in order. Returns the first
    successful result. Falls through on ANY failure (bad JSON, network,
    rate-limit) and tries the next provider. Returns None only if every
    configured provider failed for non-rate-limit reasons; raises
    AllProvidersRateLimited only if every configured provider returned 429.
    """
    order = [p.strip() for p in settings.llm_provider_order.split(",") if p.strip()]
    configured = 0
    rate_limited = 0
    for name in order:
        fn = _PROVIDERS.get(name)
        if not fn:
            continue
        # skip providers without their key — they'd noop anyway
        if name == "gemini" and not settings.gemini_api_key:
            continue
        if name == "groq" and not settings.groq_api_key:
            continue
        if name == "openrouter" and not settings.openrouter_api_key:
            continue
        configured += 1
        try:
            result = fn(system, user)
        except AllProvidersRateLimited:
            rate_limited += 1
            continue  # try next provider
        if result is not None:
            return result
        # None = bad output from this provider; continue to next
    if configured and rate_limited == configured:
        raise AllProvidersRateLimited()
    return None
