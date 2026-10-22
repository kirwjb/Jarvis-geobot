"""Distributed Token Bucket Rate Limiter with Redis Lua scripting & automated DDoS penalty box."""

import logging
import time
from typing import NamedTuple, Optional
from redis.asyncio import Redis

from src.utils.redis_keys import RedisKeys

logger = logging.getLogger(__name__)

TOKEN_BUCKET_LUA = """
local bucket_key = KEYS[1]
local penalty_key = KEYS[2]

local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local cost = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

-- 1. Check if client is currently in penalty box
if redis.call("EXISTS", penalty_key) == 1 then
    local p_ttl = redis.call("TTL", penalty_key)
    if p_ttl < 1 then p_ttl = 1 end
    return {0, 0, p_ttl, 1} -- {allowed, remaining, retry_after, is_penalized}
end

-- 2. Fetch current server time directly from Redis (avoids app clock drift)
local time_res = redis.call("TIME")
local now = tonumber(time_res[1]) + (tonumber(time_res[2]) / 1000000)

-- 3. Read current bucket state
local bucket = redis.call("HMGET", bucket_key, "tokens", "last_updated")
local tokens = tonumber(bucket[1])
local last_updated = tonumber(bucket[2])

if tokens == nil or last_updated == nil then
    tokens = capacity
    last_updated = now
else
    local delta = math.max(0, now - last_updated)
    tokens = math.min(capacity, tokens + delta * refill_rate)
    last_updated = now
end

local allowed = 0
local retry_after = 0

if tokens >= cost then
    tokens = tokens - cost
    allowed = 1
else
    allowed = 0
    local needed = cost - tokens
    retry_after = math.ceil(needed / refill_rate)
    if retry_after < 1 then retry_after = 1 end
end

-- 4. Persist updated bucket state
redis.call("HSET", bucket_key, "tokens", tostring(tokens), "last_updated", tostring(last_updated))
redis.call("EXPIRE", bucket_key, ttl)

return {allowed, math.floor(tokens), retry_after, 0}
"""

class RateLimitResult(NamedTuple):
    allowed: bool
    remaining: int
    retry_after: int
    is_penalized: bool

class TokenBucketLimiter:
    """Enterprise-grade Token Bucket Rate Limiter with automated DDoS mitigation."""

    def __init__(
        self,
        redis_client: Optional[Redis],
        default_capacity: int = 20,
        default_refill_rate: float = 4.0,
        violation_threshold: int = 5,
        violation_window: int = 60,
        penalty_duration: int = 120,
    ):
        self.redis = redis_client
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self.violation_threshold = violation_threshold
        self.violation_window = violation_window
        self.penalty_duration = penalty_duration
        self._script_sha: Optional[str] = None

    async def _get_script_sha(self) -> str:
        if not self._script_sha and self.redis:
            try:
                self._script_sha = await self.redis.script_load(TOKEN_BUCKET_LUA)
            except Exception as exc:
                logger.warning("Failed to preload Lua script in Redis: %s", exc)
        return self._script_sha or ""

    async def check(
        self,
        identifier: str,
        capacity: Optional[int] = None,
        refill_rate: Optional[float] = None,
        cost: int = 1,
    ) -> RateLimitResult:
        """Evaluate rate limit for identifier using Token Bucket."""
        if not self.redis:
            return RateLimitResult(allowed=True, remaining=10, retry_after=0, is_penalized=False)

        cap = capacity if capacity is not None else self.default_capacity
        refill = refill_rate if refill_rate is not None else self.default_refill_rate
        bucket_ttl = int(cap / refill) + 60

        bucket_key = RedisKeys.rate_limit_bucket(identifier)
        penalty_key = RedisKeys.penalty(identifier)

        try:
            sha = await self._get_script_sha()
            if sha:
                res = await self.redis.evalsha(
                    sha,
                    2,
                    bucket_key,
                    penalty_key,
                    cap,
                    refill,
                    cost,
                    bucket_ttl,
                )
            else:
                res = await self.redis.eval(
                    TOKEN_BUCKET_LUA,
                    2,
                    bucket_key,
                    penalty_key,
                    cap,
                    refill,
                    cost,
                    bucket_ttl,
                )

            allowed = bool(res[0])
            remaining = int(res[1])
            retry_after = int(res[2])
            is_penalized = bool(res[3])

            if not allowed and not is_penalized:
                await self._record_violation(identifier)

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                retry_after=retry_after,
                is_penalized=is_penalized,
            )
        except Exception as exc:
            logger.error("Rate limiter Redis evaluation error for %s: %s", identifier, exc)
            return RateLimitResult(allowed=True, remaining=1, retry_after=0, is_penalized=False)

    async def _record_violation(self, identifier: str) -> None:
        """Increment consecutive violations. If threshold is exceeded, trigger penalty box."""
        try:
            violation_key = RedisKeys.violations(identifier)
            count = await self.redis.incr(violation_key)
            if count == 1:
                await self.redis.expire(violation_key, self.violation_window)

            if count >= self.violation_threshold:
                penalty_key = RedisKeys.penalty(identifier)
                await self.redis.setex(penalty_key, self.penalty_duration, "penalized")
                await self.redis.delete(violation_key)
                logger.warning(
                    "DDoS Mitigation: Identifier '%s' exceeded %d violations; placed in penalty box for %ds",
                    identifier,
                    self.violation_threshold,
                    self.penalty_duration,
                )
        except Exception as exc:
            logger.error("Failed to record rate limit violation for %s: %s", identifier, exc)

    async def lift_penalty(self, identifier: str) -> None:
        """Manual unban/lift penalty for identifier."""
        if self.redis:
            await self.redis.delete(RedisKeys.penalty(identifier))
            await self.redis.delete(RedisKeys.violations(identifier))
