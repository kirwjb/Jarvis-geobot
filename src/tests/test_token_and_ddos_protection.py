import datetime
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.datastructures import Headers

from src.database.models import User
from src.middleware.rate_limiter import TokenBucketLimiter, RateLimitResult
from src.middleware.http_rate_limiter import HttpDDoSProtectionMiddleware, get_client_ip
from src.services.token_service import UserTokenService, UNLIMITED_TOKEN_COUNT

@pytest.mark.asyncio
async def test_token_bucket_allows_within_capacity():
    mock_redis = AsyncMock()
    mock_redis.evalsha.return_value = [1, 9, 0, 0]
    mock_redis.script_load.return_value = "fake_sha1"

    limiter = TokenBucketLimiter(mock_redis, default_capacity=10, default_refill_rate=2.0)
    res = await limiter.check(identifier="user:123", capacity=10, refill_rate=2.0, cost=1)

    assert res.allowed is True
    assert res.remaining == 9
    assert res.retry_after == 0
    assert res.is_penalized is False

@pytest.mark.asyncio
async def test_token_bucket_rejects_when_exhausted():
    mock_redis = AsyncMock()
    mock_redis.evalsha.return_value = [0, 0, 3, 0]
    mock_redis.script_load.return_value = "fake_sha1"
    mock_redis.incr.return_value = 1

    limiter = TokenBucketLimiter(mock_redis, default_capacity=5, default_refill_rate=1.0)
    res = await limiter.check(identifier="ip:192.168.1.1", capacity=5, refill_rate=1.0, cost=1)

    assert res.allowed is False
    assert res.remaining == 0
    assert res.retry_after == 3
    assert res.is_penalized is False
    mock_redis.incr.assert_called_once()

@pytest.mark.asyncio
async def test_token_bucket_trips_penalty_box():
    mock_redis = AsyncMock()
    mock_redis.evalsha.return_value = [0, 0, 5, 0]
    mock_redis.script_load.return_value = "fake_sha1"
    mock_redis.incr.return_value = 5

    limiter = TokenBucketLimiter(mock_redis, violation_threshold=5, penalty_duration=120)
    res = await limiter.check(identifier="bad_actor:666")

    assert res.allowed is False
    mock_redis.setex.assert_called_once()
    assert "penalty:bad_actor:666" in mock_redis.setex.call_args[0]

@pytest.mark.asyncio
async def test_token_bucket_enforces_existing_penalty():
    mock_redis = AsyncMock()
    mock_redis.evalsha.return_value = [0, 0, 45, 1]
    mock_redis.script_load.return_value = "fake_sha1"

    limiter = TokenBucketLimiter(mock_redis)
    res = await limiter.check(identifier="jailed:999")

    assert res.allowed is False
    assert res.is_penalized is True
    assert res.retry_after == 45

@pytest.mark.asyncio
async def test_superadmin_has_unlimited_tokens(monkeypatch):
    monkeypatch.setattr("src.services.token_service.is_superadmin", lambda uid: uid == 777)
    service = UserTokenService(redis=AsyncMock())
    balance = await service.get_token_balance(777)
    assert balance == UNLIMITED_TOKEN_COUNT

    allowed, rem = await service.consume_tokens(777, cost=5)
    assert allowed is True
    assert rem == UNLIMITED_TOKEN_COUNT

@pytest.mark.asyncio
async def test_user_daily_token_reset(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    user = User(
        user_id=101,
        username="traveler",
        tokens=1,
        last_reset=datetime.date.today() - datetime.timedelta(days=1),
        role="USER",
        is_admin=False,
    )

    class FakeSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def get(self, model, ident):
            return user
        async def commit(self):
            pass

    monkeypatch.setattr("src.services.token_service.AsyncSessionLocal", lambda: FakeSession())
    monkeypatch.setattr("src.services.token_service.is_superadmin", lambda uid: False)

    service = UserTokenService(redis=mock_redis, default_quota=15)
    balance = await service.get_token_balance(101)

    assert balance == 15
    assert user.tokens == 15
    assert user.last_reset == datetime.date.today()
    mock_redis.setex.assert_called_once()

@pytest.mark.asyncio
async def test_user_consume_and_refund_tokens(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.get.return_value = "5"

    user = User(
        user_id=102,
        username="explorer",
        tokens=5,
        last_reset=datetime.date.today(),
        role="USER",
        is_admin=False,
    )

    class FakeSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def get(self, model, ident):
            return user
        async def commit(self):
            pass

    monkeypatch.setattr("src.services.token_service.AsyncSessionLocal", lambda: FakeSession())
    monkeypatch.setattr("src.services.token_service.is_superadmin", lambda uid: False)

    service = UserTokenService(redis=mock_redis)
    allowed, rem = await service.consume_tokens(102, cost=2)
    assert allowed is True
    assert rem == 3
    assert user.tokens == 3

    mock_redis.get.return_value = "3"
    allowed, rem = await service.consume_tokens(102, cost=10)
    assert allowed is False
    assert rem == 3

    refunded = await service.refund_tokens(102, amount=2)
    assert refunded == 5
    assert user.tokens == 5

@pytest.mark.asyncio
async def test_http_rate_limiter_allows_and_adds_headers():
    mock_limiter = AsyncMock()
    mock_limiter.check.return_value = RateLimitResult(
        allowed=True,
        remaining=19,
        retry_after=0,
        is_penalized=False,
    )

    middleware = HttpDDoSProtectionMiddleware(app=None, limiter=mock_limiter)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/test-route",
        "headers": [(b"host", b"localhost")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    async def call_next(req):
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert response.headers.get("X-RateLimit-Limit") is not None
    assert response.headers.get("X-RateLimit-Remaining") == "19"

@pytest.mark.asyncio
async def test_http_rate_limiter_exempts_health_endpoint():
    mock_limiter = AsyncMock()
    middleware = HttpDDoSProtectionMiddleware(app=None, limiter=mock_limiter)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [(b"host", b"localhost")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    async def call_next(req):
        return JSONResponse({"status": "ok"})

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    mock_limiter.check.assert_not_called()

@pytest.mark.asyncio
async def test_http_rate_limiter_rejects_with_429():
    mock_limiter = AsyncMock()
    mock_limiter.check.return_value = RateLimitResult(
        allowed=False,
        remaining=0,
        retry_after=12,
        is_penalized=False,
    )

    middleware = HttpDDoSProtectionMiddleware(app=None, limiter=mock_limiter)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/heavy-route",
        "headers": [(b"host", b"localhost")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)

    async def call_next(req):
        return JSONResponse({"data": 123})

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "12"
    body = json.loads(response.body.decode())
    assert "Rate limit exceeded" in body["detail"]

def test_extract_client_ip():
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 70.41.3.18")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)
    assert get_client_ip(request) == "203.0.113.195"
