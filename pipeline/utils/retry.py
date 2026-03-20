"""Retry decorator with exponential back-off."""
import time
import functools
from pipeline.utils.logger import get_logger

log = get_logger(__name__)


def retry(max_attempts: int = 3, delay: float = 2.0, backoff: float = 2.0,
          exceptions: tuple = (Exception,)):
    """Decorator that retries *func* up to *max_attempts* times."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        log.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    log.warning(
                        "%s attempt %d/%d failed (%s). Retrying in %.0fs…",
                        func.__name__, attempt, max_attempts, exc, wait,
                    )
                    time.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator
