"""Wikipedia REST summary lookup + lightweight entity extraction."""
import logging
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger("contextnews.wiki")

SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
# Wikimedia requires a descriptive UA with contact info, else 403.
HEADERS = {
    "User-Agent": "ContextNews/1.0 (https://contextnews.app; mailto:kartik004srivastava@gmail.com)",
    "Accept": "application/json",
}

# Words that look capitalised in Title-Case headlines but are not entities.
_COMMON = {
    "the", "a", "an", "this", "that", "these", "those", "it", "he", "she",
    "they", "we", "in", "on", "at", "for", "and", "but", "or", "as", "is",
    "are", "was", "were", "be", "been", "to", "of", "by", "with", "from",
    "after", "before", "over", "amid", "says", "said", "new", "how", "why",
    "what", "when", "where", "who", "will", "can", "could", "should", "would",
    "building", "solve", "make", "makes", "set", "sets", "get", "gets",
    "world", "worlds", "largest", "first", "one", "two", "into", "report",
    "reports", "update", "live", "watch", "india", "indian",
}


def _is_title_case(text: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z]+", text) if len(w) > 2]
    if not words:
        return False
    caps = sum(1 for w in words if w[0].isupper())
    return caps / len(words) > 0.7


def extract_entities(headline: str, body: str = "", limit: int = 3) -> list[str]:
    """Key-entity extraction.

    Headlines are often Title Case (capitalisation carries no signal), so
    prefer sentence-case body text and fall back to the headline only if
    needed. Runs of Capitalised non-common tokens form an entity.
    """
    source = headline or ""
    if body and body.strip() and (_is_title_case(headline) or not headline):
        source = body
    elif body and body.strip():
        source = f"{headline}. {body}"
    if not source:
        return []

    entities: list[str] = []
    current: list[str] = []
    for tok in re.findall(r"\b[A-Za-z]+\b", source):
        if tok[0].isupper() and tok.lower() not in _COMMON:
            current.append(tok)
        else:
            if current:
                entities.append(" ".join(current))
            current = []
    if current:
        entities.append(" ".join(current))

    scored: dict[str, int] = {}
    for e in (x.strip() for x in entities):
        if len(e) < 4 or e.lower() in _COMMON:
            continue
        scored[e] = scored.get(e, 0) + len(e.split()) + 1

    ranked = sorted(scored.items(), key=lambda kv: kv[1], reverse=True)
    out, seen = [], set()
    for name, _ in ranked:
        low = name.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(name)
        if len(out) >= limit:
            break
    return out


def fetch_summary(entity: str) -> dict | None:
    try:
        resp = httpx.get(
            SUMMARY_URL.format(quote(entity.replace(" ", "_"))),
            headers=HEADERS,
            timeout=8,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("Wikipedia lookup failed for '%s': %s", entity, exc)
        return None
    extract = data.get("extract")
    if not extract or data.get("type") == "disambiguation":
        return None
    return {
        "title": data.get("title", entity),
        "extract": extract,
        "url": (data.get("content_urls", {}).get("desktop", {}) or {}).get("page"),
    }


def fetch_entity_summaries(
    headline: str, body: str = "", limit: int = 3
) -> tuple[list[str], list[dict]]:
    entities = extract_entities(headline, body, limit)
    summaries = []
    for e in entities:
        s = fetch_summary(e)
        if s:
            summaries.append(s)
    return entities, summaries
