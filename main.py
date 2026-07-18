import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from sentry_sdk.types import Event, Hint
from sentry_sdk.utils import BadDsn
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from adapters.redis import check_redis_connection
from auth import ApiKeyError
from config import ENV, LOG_LEVEL, REDIS_URL, SENTRY_DSN, limiter
from routes.render import router

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

_SENSITIVE_HEADERS = {"x-api-key", "authorization", "cookie"}


def _scrub_before_send(event: Event, hint: Hint) -> Event | None:
    # Defense in depth: this app's own error paths already avoid logging
    # payload content, but strip sensitive headers here too before anything
    # leaves the process.
    request = event.get("request")
    if request and "headers" in request:
        request["headers"] = {
            k: ("[Filtered]" if k.lower() in _SENSITIVE_HEADERS else v)
            for k, v in request["headers"].items()
        }
    return event


if SENTRY_DSN:
    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENV,
            send_default_pii=False,
            before_send=_scrub_before_send,
        )
    except BadDsn as exc:
        # A malformed DSN raises here (unlike a well-formed-but-wrong/
        # unreachable one, which fails silently in the background transport
        # instead). Log and continue without Sentry rather than let a typo'd
        # env var take the whole app down.
        logger.warning("Sentry disabled: SENTRY_DSN is malformed (%s)", exc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    check_redis_connection(REDIS_URL)
    logger.info("Redis connectivity check passed")
    yield


app = FastAPI(title="JSON+Image to PDF/DOCX Converter", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(ApiKeyError)
async def api_key_error_handler(request: Request, exc: ApiKeyError) -> JSONResponse:
    return JSONResponse({"error": exc.code}, status_code=exc.status_code)


app.include_router(router, prefix="/v1")
