from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from threading import Lock
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.app.core.config import get_settings
from backend.app.db.repository import append_api_event

logger = logging.getLogger("monopoly.api")


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            if len(self._buckets) > 10_000:
                stale = [name for name, values in self._buckets.items() if not values]
                for name in stale[:1_000]:
                    self._buckets.pop(name, None)
            return True


rate_limiter = SlidingWindowRateLimiter()


async def security_and_observability_middleware(request: Request, call_next):
    settings = get_settings()
    request_id = request.headers.get("x-request-id") or str(uuid4())
    client_ip = request.client.host if request.client else "unknown"
    started = time.perf_counter()

    content_length = request.headers.get("content-length")
    try:
        request_bytes = int(content_length) if content_length else 0
    except ValueError:
        request_bytes = 0
    if request_bytes > settings.max_request_bytes:
        return JSONResponse(
            status_code=413,
            content={
                "detail": "Request body vượt giới hạn cho phép.",
                "request_id": request_id,
            },
        )

    if request.url.path.startswith("/api/"):
        limit = settings.rate_limit_per_minute
        if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/register"}:
            limit = min(10, limit)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            limit = max(10, limit // 3)
        if not rate_limiter.allow(f"{client_ip}:{request.method}", limit):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
                    "request_id": request_id,
                },
                headers={"Retry-After": "60"},
            )

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled request failure",
            extra={"request_id": request_id, "path": request.url.path},
        )
        if settings.environment == "production":
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "Lỗi nội bộ. Vui lòng cung cấp request_id cho quản trị viên.",
                    "request_id": request_id,
                },
            )
        else:
            raise

    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; connect-src 'self'"
    )
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        try:
            await asyncio.to_thread(
                append_api_event,
                request_id=request_id,
                user_id=None,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
            )
        except Exception:
            logger.exception(
                "Could not persist API event",
                extra={"request_id": request_id, "path": request.url.path},
            )
    return response
