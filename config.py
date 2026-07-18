from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import Limiter
from slowapi.util import get_remote_address


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required -- slowapi/limits silently falls back to in-memory storage if
    # this is unset, which is explicitly not wanted, so pydantic-settings
    # fails construction (and therefore app startup) if it's missing rather
    # than letting rate limiting quietly become per-instance.
    redis_url: str

    api_key: str | None = None
    sentry_dsn: str | None = None
    log_level: str = "INFO"
    env: str = "development"


settings = Settings()

# Flat re-exports so existing `from config import X` call sites don't need
# to change to `from config import settings` + `settings.x` everywhere.
REDIS_URL = settings.redis_url
API_KEY = settings.api_key
SENTRY_DSN = settings.sentry_dsn
LOG_LEVEL = settings.log_level
ENV = settings.env

limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL)

# retryguard/tenacity config -- not secrets, plain constants.
RETRY_MAX_ATTEMPTS: int = 5
RETRY_FALLBACK_DELAY_SECONDS: float = 2.0
