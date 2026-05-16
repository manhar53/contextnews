"""RSS ingestion from multiple feeds (no API key needed)."""
from datetime import datetime, timezone
import logging
from time import mktime

import feedparser
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from dedupe import is_duplicate, normalise
from models import Article
from sources import get_priority

logger = logging.getLogger("contextnews.rss")

# Browser-style headers so feeds don't block the default feedparser UA.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/rss+xml, application/xml",
}

def _gnews(query: str) -> str:
    """Google News RSS search feed (India edition) — aggregates many publishers.

    Approach borrowed from fetch-and-index-global-news / worldmonitor, which
    lean on Google News RSS + many feeds for source diversity.
    """
    from urllib.parse import quote

    return (
        f"https://news.google.com/rss/search?q={quote(query)}"
        "&hl=en-IN&gl=IN&ceid=IN:en"
    )


# feed url -> (source name, default category)
RSS_FEEDS: dict[str, tuple[str, str]] = {
    # Broad
    "http://feeds.bbci.co.uk/news/rss.xml": ("BBC News", "general"),
    "https://feeds.reuters.com/reuters/topNews": ("Reuters", "general"),
    # Al Jazeera moved to 'general' so it stops flooding the Defence tab.
    "https://www.aljazeera.com/xml/rss/all.xml": ("Al Jazeera", "general"),
    "https://www.thehindu.com/feeder/default.rss": ("The Hindu", "india"),
    "https://indianexpress.com/feed/": ("Indian Express", "india"),
    "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3": ("PIB India", "government"),
    "http://www.indiandefencereview.com/feed/": ("Indian Defence Review", "defence"),
    "https://theprint.in/category/defence/feed/": ("The Print Defence", "defence"),
    "https://www.aninews.in/rss/world.xml": ("ANI News", "geopolitics"),
    "https://idsa.in/rss": ("IDSA", "defence"),
    "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml": ("Hindustan Times", "india"),
    "https://feeds.feedburner.com/ndtvnews-india-news": ("NDTV India", "india"),
    # Indian defence-specific publishers
    "https://www.thehindu.com/news/national/feeder/default.rss": ("The Hindu National", "india"),
    "https://www.financialexpress.com/about/defence/feed/": ("Financial Express Defence", "defence"),
    "https://theprint.in/category/diplomacy/feed/": ("The Print Diplomacy", "geopolitics"),
    # Google News RSS aggregates (many publishers, India-targeted) — diversity
    _gnews("India defence"): ("Google News · India Defence", "defence"),
    _gnews("Indian Army OR Indian Navy OR Indian Air Force"): ("Google News · Armed Forces", "defence"),
    _gnews("DRDO OR HAL OR defence acquisition India"): ("Google News · Defence Tech", "defence"),
    _gnews("India China border OR India Pakistan border"): ("Google News · Borders", "geopolitics"),
    _gnews("Indian foreign policy OR India diplomacy OR Indo-Pacific"): ("Google News · Diplomacy", "geopolitics"),
    _gnews("Ministry of Defence India OR defence budget India"): ("Google News · MoD/Policy", "government"),
    _gnews("Indian economy"): ("Google News · Economy", "economy"),
    # Broader news-hub feeds (Top Stories diversity, not defence-specific)
    _gnews("world news today"): ("Google News · World", "general"),
    _gnews("India business OR Indian markets OR Sensex Nifty"): ("Google News · Business India", "economy"),
    _gnews("India technology OR Indian startups OR AI India"): ("Google News · Tech India", "general"),
    _gnews("India health OR public health India"): ("Google News · Health India", "india"),
    _gnews("India top news"): ("Google News · India Top", "india"),
}


def _entry_dt(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime.fromtimestamp(mktime(val), tz=timezone.utc).replace(tzinfo=None)
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    import re

    return re.sub(r"<[^>]+>", "", text).strip() or None


def fetch_rss_feeds() -> int:
    db = SessionLocal()
    total_new = 0
    try:
        rows = db.query(Article.headline_norm).order_by(Article.id.desc()).limit(800).all()
        recent_norms = [r[0] for r in rows if r[0]]
        seen_urls: set[str] = set()

        for url, (source, category) in RSS_FEEDS.items():
            try:
                parsed = feedparser.parse(url, request_headers=REQUEST_HEADERS)
            except Exception as exc:  # noqa: BLE001  never crash on one bad feed
                logger.warning("RSS parse failed for %s: %s", source, exc)
                continue
            if parsed.bozo and not parsed.entries:
                logger.warning(
                    "RSS feed unreadable, skipping: %s (%s)",
                    source,
                    getattr(parsed, "bozo_exception", "unknown"),
                )
                continue

            for entry in parsed.entries[:40]:
                try:
                    link = entry.get("link")
                    title = entry.get("title")
                    if not link or not title:
                        continue
                    if link in seen_urls:
                        continue
                    if db.query(Article).filter(Article.url == link).first():
                        continue
                    if is_duplicate(db, title, recent_norms):
                        continue
                    seen_urls.add(link)

                    # Google News titles are "Headline - Publisher"; resolve the
                    # real publisher so credibility scoring still applies.
                    disp_source = source
                    if source.startswith("Google News"):
                        pub = (entry.get("source") or {}).get("title")
                        if pub:
                            disp_source = pub
                            if title.endswith(f" - {pub}"):
                                title = title[: -len(f" - {pub}")].strip()
                        elif " - " in title:
                            title, _, pub = title.rpartition(" - ")
                            title = title.strip()
                            disp_source = pub.strip() or source

                    norm = normalise(title)
                    db.add(
                        Article(
                            url=link,
                            headline=title,
                            headline_norm=norm,
                            source=disp_source,
                            author=entry.get("author"),
                            description=_clean(entry.get("summary")),
                            content=_clean(entry.get("summary")),
                            image_url=(
                                entry.get("media_content", [{}])[0].get("url")
                                if entry.get("media_content")
                                else None
                            ),
                            origin="rss",
                            category=category,
                            source_priority=get_priority(disp_source),
                            published_at=_entry_dt(entry),
                        )
                    )
                    recent_norms.append(norm)
                    total_new += 1
                except Exception as exc:  # noqa: BLE001  one bad entry must not crash
                    logger.warning("Skipping bad entry in %s: %s", source, exc)
                    continue

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                logger.warning("Commit conflict on feed %s; skipped batch.", source)
        logger.info("RSS fetch complete. %d new articles.", total_new)
    finally:
        db.close()
    return total_new
