import json
from redis.asyncio import Redis
from src.config import REDIS_HOST, REDIS_PORT

class SessionManager:
    def __init__(self, redis_client: Redis, ttl: int = 7200):
        self.redis = redis_client
        self.ttl = ttl

    async def get_user_session(self, user_id: int) -> dict:
        data = await self.redis.get(f"user_session:{user_id}")
        return json.loads(data) if data else {}

    async def set_user_session(self, user_id: int, data: dict):
        await self.redis.setex(
            f"user_session:{user_id}", 
            self.ttl, 
            json.dumps(data, ensure_ascii=False)
        )

    async def get_group_session(self, group_id: int) -> dict:
        data = await self.redis.get(f"group_session:{group_id}")
        return json.loads(data) if data else {}

    async def set_group_session(self, group_id: int, data: dict):
        await self.redis.setex(
            f"group_session:{group_id}", 
            self.ttl, 
            json.dumps(data, ensure_ascii=False)
        )

    async def delete_user_session(self, user_id: int):
        await self.redis.delete(f"user_session:{user_id}")

    async def delete_group_session(self, group_id: int):
        await self.redis.delete(f"group_session:{group_id}")


redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
user_sessions = SessionManager(redis_client)