"""Background scheduler: RSS, NewsAPI, and auto-analysis of important topics."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from auto_analyse import auto_analyse_important
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
    if settings.auto_analyse_enabled:
        _scheduler.add_job(
            auto_analyse_important,
            trigger="interval",
            minutes=settings.auto_analyse_interval_minutes,
            id="auto_analyse",
            next_run_time=None,
            replace_existing=True,
        )
    _scheduler.start()
    logger.info(
        "Scheduler started: RSS every %dh, NewsAPI every %dh, auto-analyse %s",
        settings.rss_fetch_interval_hours,
        settings.newsapi_fetch_interval_hours,
        f"every {settings.auto_analyse_interval_minutes}m"
        if settings.auto_analyse_enabled
        else "disabled",
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
