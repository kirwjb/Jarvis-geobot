"""User Token Quota Service for managing operational tokens and Layer 7 protection."""

import datetime
import logging
from typing import Optional, Tuple
from sqlalchemy import select, update
from redis.asyncio import Redis

from src.database.db import AsyncSessionLocal
from src.database.models import User
from src.database.session_manager import redis_client
from src.services.rbac import is_superadmin, resolve_user_role, Role
from src.utils.redis_keys import RedisKeys

logger = logging.getLogger(__name__)

DEFAULT_DAILY_QUOTA = 15
UNLIMITED_TOKEN_COUNT = 999999

class UserTokenService:
    """Manages User.tokens from DB with fast-path Redis caching and daily replenishment."""

    def __init__(self, redis: Optional[Redis] = None, default_quota: int = DEFAULT_DAILY_QUOTA):
        self.redis = redis or redis_client
        self.default_quota = default_quota

    async def get_token_balance(self, user_id: int) -> int:
        """Fetch current token balance for user. Handles daily reset if needed."""
        if is_superadmin(user_id):
            return UNLIMITED_TOKEN_COUNT

        token_key = RedisKeys.user_tokens(user_id)
        if self.redis:
            try:
                cached = await self.redis.get(token_key)
                if cached is not None:
                    return int(cached)
            except Exception as exc:
                logger.warning("Redis error getting user tokens for #%d: %s", user_id, exc)

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return self.default_quota

            role = resolve_user_role(user_id, user.role, user.is_admin)
            if role >= Role.ADMIN:
                return UNLIMITED_TOKEN_COUNT

            today = datetime.date.today()
            if user.last_reset is None or user.last_reset < today:
                user.tokens = max(user.tokens, self.default_quota)
                user.last_reset = today
                await session.commit()
                logger.info("Daily token reset performed for user #%d -> %d tokens", user_id, user.tokens)

            balance = user.tokens

        if self.redis:
            try:
                await self.redis.setex(token_key, 86400, str(balance))
            except Exception as exc:
                logger.warning("Redis set error for user tokens #%d: %s", user_id, exc)

        return balance

    async def consume_tokens(
        self,
        user_id: int,
        cost: int = 1,
    ) -> Tuple[bool, int]:
        """
        Atomically consume tokens for an operation.
        Returns:
            (allowed: bool, remaining_tokens: int)
        """
        if cost <= 0 or is_superadmin(user_id):
            return True, UNLIMITED_TOKEN_COUNT

        current_balance = await self.get_token_balance(user_id)
        if current_balance == UNLIMITED_TOKEN_COUNT:
            return True, UNLIMITED_TOKEN_COUNT

        if current_balance < cost:
            return False, current_balance

        token_key = RedisKeys.user_tokens(user_id)

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False, 0

            role = resolve_user_role(user_id, user.role, user.is_admin)
            if role >= Role.ADMIN:
                return True, UNLIMITED_TOKEN_COUNT

            if user.tokens < cost:
                if self.redis:
                    await self.redis.setex(token_key, 86400, str(user.tokens))
                return False, user.tokens

            user.tokens -= cost
            remaining = user.tokens
            await session.commit()

        if self.redis:
            try:
                await self.redis.setex(token_key, 86400, str(remaining))
            except Exception as exc:
                logger.warning("Failed to update token cache for #%d: %s", user_id, exc)

        return True, remaining

    async def refund_tokens(self, user_id: int, amount: int = 1) -> int:
        """Refund tokens back to user if a downstream request failed."""
        if amount <= 0 or is_superadmin(user_id):
            return UNLIMITED_TOKEN_COUNT

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return 0
            user.tokens += amount
            balance = user.tokens
            await session.commit()

        token_key = RedisKeys.user_tokens(user_id)
        if self.redis:
            try:
                await self.redis.setex(token_key, 86400, str(balance))
            except Exception:
                pass
        return balance

    async def add_tokens(self, user_id: int, amount: int) -> int:
        """Grant additional tokens to a user (admin operation or top-up)."""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} does not exist")
            user.tokens += amount
            balance = user.tokens
            await session.commit()

        token_key = RedisKeys.user_tokens(user_id)
        if self.redis:
            try:
                await self.redis.setex(token_key, 86400, str(balance))
            except Exception:
                pass
        return balance

token_service = UserTokenService(redis_client)
