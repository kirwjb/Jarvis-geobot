"""HTTP Rate Limiting & Layer 7 DDoS Mitigation Middleware for FastAPI."""

import logging
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.database.session_manager import redis_client
from src.middleware.rate_limiter import TokenBucketLimiter, RateLimitResult

logger = logging.getLogger(__name__)

EXEMPT_PATHS = {
    "/",
    "/index.html",
    "/health",
    "/api/health",
    "/mir_castle.webp",
}

ROUTE_POLICIES = {
    "/api/route/build": (6, 0.5),
    "/api/pois/query": (15, 2.0),
    "/api/geo/photo-proxy": (20, 3.0),
}

DEFAULT_POLICY = (25, 5.0)

def get_client_ip(request: Request) -> str:
    """Extract real client IP from forward headers or direct socket."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

class HttpDDoSProtectionMiddleware(BaseHTTPMiddleware):
    """
    Protects FastAPI endpoints with a distributed Token Bucket rate limiter,
    automatic violation tracking, penalty boxes, and standard RFC headers.
    """

    def __init__(
        self,
        app,
        limiter: Optional[TokenBucketLimiter] = None,
    ):
        super().__init__(app)
        self.limiter = limiter or TokenBucketLimiter(
            redis_client=redis_client,
            default_capacity=DEFAULT_POLICY[0],
            default_refill_rate=DEFAULT_POLICY[1],
            violation_threshold=5,
            violation_window=60,
            penalty_duration=120,
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if (
            path in EXEMPT_PATHS
            or path.startswith("/media/")
            or path.startswith("/assets/")
            or path.startswith("/css/")
            or path.startswith("/js/")
        ):
            return await call_next(request)

        user_id = getattr(request.state, "telegram_user_id", None)
        client_ip = get_client_ip(request)

        if user_id:
            identifier = f"user:{user_id}"
        else:
            identifier = f"ip:{client_ip}"

        capacity, refill_rate = ROUTE_POLICIES.get(path, DEFAULT_POLICY)

        res: RateLimitResult = await self.limiter.check(
            identifier=identifier,
            capacity=capacity,
            refill_rate=refill_rate,
            cost=1,
        )

        if not res.allowed:
            detail_msg = (
                "Temporarily blocked due to excessive requests. Cooldown active."
                if res.is_penalized
                else "Rate limit exceeded. Please slow down."
            )
            headers = {
                "Retry-After": str(res.retry_after),
                "X-RateLimit-Limit": str(capacity),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(res.retry_after),
            }
            return JSONResponse(
                status_code=429,
                content={
                    "detail": detail_msg,
                    "retry_after": res.retry_after,
                    "penalized": res.is_penalized,
                },
                headers=headers,
            )

        response: Response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(capacity)
        response.headers["X-RateLimit-Remaining"] = str(res.remaining)

        return response
