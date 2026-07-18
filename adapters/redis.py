import logging

import redis
import redis.exceptions
from retryguard import ErrorClassifier, RetryCategory, RetryDecision
from retryguard.integrations.tenacity import (
    before_sleep_log_retryguard,
    retry_if_retryguard,
    wait_retryguard,
)
from tenacity import retry, stop_after_attempt

from config import RETRY_FALLBACK_DELAY_SECONDS, RETRY_MAX_ATTEMPTS

logger = logging.getLogger(__name__)


def _classify_redis_exceptions(exc: BaseException) -> RetryDecision | None:
    # redis-py's ConnectionError/TimeoutError are its own classes (RedisError
    # -> Exception) -- they do NOT inherit from the builtin ConnectionError/
    # TimeoutError that retryguard's default rules check via isinstance, so
    # they're invisible to retryguard without this rule and would otherwise
    # fall through to "unknown exception -> non-retryable".
    if isinstance(exc, (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError)):
        return RetryDecision(
            retryable=True,
            category=RetryCategory.NETWORK,
            reason_code="redis_connection_error",
            reason="Transient Redis connection failure",
            suggested_delay_seconds=RETRY_FALLBACK_DELAY_SECONDS,
        )
    return None


classifier = ErrorClassifier(rules=(_classify_redis_exceptions, *ErrorClassifier.DEFAULT_RULES))


@retry(
    retry=retry_if_retryguard(classifier),
    wait=wait_retryguard(classifier, fallback_seconds=RETRY_FALLBACK_DELAY_SECONDS),
    stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    before_sleep=before_sleep_log_retryguard(logger, classifier=classifier),
    reraise=True,
)
def check_redis_connection(redis_url: str) -> None:
    """Ping Redis at startup, retrying transient connection failures.

    A deploy race (app container up before Redis is reachable) is exactly
    the kind of transient failure this app otherwise has no outbound call
    site to apply retryguard/tenacity to -- rate-limit checks happen inside
    slowapi's Limiter internals, not a function this app authors.
    """
    client = redis.Redis.from_url(redis_url, socket_connect_timeout=5)
    try:
        client.ping()
    finally:
        client.close()
