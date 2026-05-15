"""Background scheduler: RSS every 2h, NewsAPI every 6h."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings
from news_service import fetch_newsapi
from rss_service import fetch_rss_feeds

logger = logging.getLogger("contextnews.scheduler")
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        fetch_rss_feeds,
        trigger="interval",
        hours=settings.rss_fetch_interval_hours,
        id="rss_fetch",
        next_run_time=None,
        replace_existing=True,
    )
    _scheduler.add_job(
        fetch_newsapi,
        trigger="interval",
        hours=settings.newsapi_fetch_interval_hours,
        id="newsapi_fetch",
        next_run_time=None,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler started: RSS every %dh, NewsAPI every %dh",
        settings.rss_fetch_interval_hours,
        settings.newsapi_fetch_interval_hours,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
