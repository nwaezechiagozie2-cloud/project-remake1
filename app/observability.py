import contextvars
import logging
import time
from collections import Counter
from threading import Lock
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")

logger = logging.getLogger(__name__)


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        token = _correlation_id.set(correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        logger.info(
            "http_request_started | method=%s | path=%s",
            request.method,
            request.url.path,
        )
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            _correlation_id.reset(token)

        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "http_request_completed | method=%s | path=%s | status=%s | duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()

    def increment(self, name: str, amount: int = 1) -> None:
        if amount <= 0:
            return
        with self._lock:
            self._counters[name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


_metrics_registry = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    return _metrics_registry