from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    newsapi_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_fallback_model: str = "gemini-flash-latest"
    feed_cache_ttl_seconds: int = 120
    gdelt_backfill_months: int = 12
    gdelt_backfill_max_per_query: int = 60
    database_url: str = "sqlite:///./contextnews.db"

    rss_fetch_interval_hours: int = 2
    newsapi_fetch_interval_hours: int = 6

    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    daily_analysis_limit: int = 10

    # Comma-separated origins allowed by CORS. Override via ALLOWED_ORIGINS env.
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )


settings = Settings()
