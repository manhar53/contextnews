from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    newsapi_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_fallback_model: str = "gemini-flash-latest"
    # Additional free LLM providers used as fallbacks when Gemini is exhausted.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:free"
    # Provider order (csv). Each runs only if its key is configured.
    llm_provider_order: str = "gemini,groq,openrouter"
    feed_cache_ttl_seconds: int = 120
    gdelt_backfill_months: int = 12
    gdelt_backfill_max_per_query: int = 60
    database_url: str = "sqlite:///./contextnews.db"

    rss_fetch_interval_hours: int = 2
    newsapi_fetch_interval_hours: int = 6

    google_client_id: str = ""   # for Google Sign-In token verification
    owner_email: str = ""         # this account bypasses the daily analysis limit

    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    daily_analysis_limit: int = 10
    # Background auto-analysis of "important" SSB topics (no user / no quota).
    auto_analyse_enabled: bool = True
    auto_analyse_interval_minutes: int = 30
    auto_analyse_per_run: int = 8

    # Comma-separated origins allowed by CORS. Override via ALLOWED_ORIGINS env.
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )


settings = Settings()
