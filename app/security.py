import hashlib
import hmac
import time
from collections import defaultdict, deque
from dataclasses import dataclass

import redis.asyncio as redis
from fastapi import Request

from app.config import Settings, get_settings
from app.exceptions import AuthorizationError, TooManyRequestsError, ValidationError

_redis_client: redis.Redis | None = None

def get_redis_client() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if settings.redis_url:
            _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def ensure_jwt_secret_strength(settings: Settings) -> None:
    env = (settings.app_env or "development").strip().lower()
    if env in {"development", "dev", "local", "test", "testing"}:
        return

    secret = settings.jwt_secret or ""
    if len(secret) < settings.jwt_min_secret_length:
        raise RuntimeError(
            "JWT_SECRET is too weak for non-development environment. "
            f"Minimum length is {settings.jwt_min_secret_length}."
        )

    weak_secrets = {
        "change_me",
        "secret",
        "password",
        "jwt_secret",
        "one_tap_secret",
        "replace_with_long_random_secret",
    }
    if secret.strip().lower() in weak_secrets:
        raise RuntimeError("JWT_SECRET uses a known weak placeholder for non-development environment.")


def verify_webhook_signature(raw_body: bytes, signature_header: str | None, app_secret: str | None) -> None:
    if not app_secret:
        return

    if not signature_header:
        raise AuthorizationError("Missing webhook signature")

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        raise AuthorizationError("Invalid webhook signature format")

    received = signature_header[len(prefix):].strip()
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received, expected):
        raise AuthorizationError("Webhook signature verification failed")


@dataclass(slots=True)
class _RateLimitBucket:
    timestamps: deque[float]


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _RateLimitBucket] = defaultdict(lambda: _RateLimitBucket(deque()))

    def allow(self, key: str, *, max_requests: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket = self._buckets[key]
        while bucket.timestamps and bucket.timestamps[0] <= cutoff:
            bucket.timestamps.popleft()

        if len(bucket.timestamps) >= max_requests:
            return False

        bucket.timestamps.append(now)
        return True

    def reset(self) -> None:
        self._buckets.clear()


rate_limiter = InMemoryRateLimiter()

async def check_rate_limit_redis(key: str, max_requests: int, window_seconds: int) -> bool:
    client = get_redis_client()
    if not client:
        return rate_limiter.allow(key, max_requests=max_requests, window_seconds=window_seconds)

    now = int(time.time())
    pipeline = client.pipeline()
    pipeline.zremrangebyscore(key, 0, now - window_seconds)
    pipeline.zadd(key, {str(now + float(time.monotonic() % 1)): now})
    pipeline.zcard(key)
    pipeline.expire(key, window_seconds)
    results = await pipeline.execute()
    count = results[2]
    return count <= max_requests


def _client_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{request.url.path}"


def rate_limit_dependency(*, scope: str):
    async def _dependency(request: Request) -> None:
        settings = get_settings()
        if scope == "auth":
            max_requests = settings.auth_rate_limit_max
            window_seconds = settings.auth_rate_limit_window_seconds
        elif scope == "webhook":
            max_requests = settings.webhook_rate_limit_max
            window_seconds = settings.webhook_rate_limit_window_seconds
        else:
            raise ValidationError("Unknown rate limit scope")

        key = f"rate_limit:{scope}:{_client_key(request)}"
        allowed = await check_rate_limit_redis(key, max_requests=max_requests, window_seconds=window_seconds)
        if not allowed:
            raise TooManyRequestsError(
                "Rate limit exceeded",
                details={
                    "scope": scope,
                    "max_requests": max_requests,
                    "window_seconds": window_seconds,
                },
            )

    return _dependency