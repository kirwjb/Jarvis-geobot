from redis.asyncio import Redis

class RateLimiter:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def is_allowed(self, user_id: int, limit: int = 5, window: int = 3) -> bool:
        if await self.redis.exists(f"penalty:{user_id}"):
            return False
            
        key = f"rate_limit:{user_id}"
        count = await self.redis.incr(key)
        
        if count == 1:
            await self.redis.expire(key, window)
            
        return count <= limit