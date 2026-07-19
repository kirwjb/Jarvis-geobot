from telebot.handler_backends import BaseMiddleware
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import User
from src.config import SUPERADMINS
from .limiter import RateLimiter
from src.utils.languages import get_text

class SecurityMiddleware(BaseMiddleware):
    def __init__(self, redis_client):
        super().__init__()
        self.redis = redis_client
        self.limiter = RateLimiter(redis_client)
        self.update_types = ['message', 'callback_query']

    async def pre_process(self, message, data):
        user = message.from_user if message.from_user else (message.callback_query.from_user if message.callback_query else None)
        if not user: return

        user_id = user.id

        if user_id in SUPERADMINS: 
            return

        maintenance = await self.redis.get("maintenance_mode")
        if maintenance == "1" and message.from_user.id not in SUPERADMINS:
            await message.bot.reply_to(message, get_text("maintenance_mode_msg"))
            return "cancel" 

        if not await self.limiter.is_allowed(user_id):
            await self._send_rejection(message)
            return {"cancel": True}

        if await self._is_banned(user_id):
            return {"cancel": True}

    async def _is_banned(self, user_id: int) -> bool:
        cached = await self.redis.get(f"ban_status:{user_id}")
        if cached == "banned": return True
        if cached == "safe": return False

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User.is_banned).where(User.user_id == user_id))
            is_banned = result.scalar_one_or_none()

        if is_banned:
            await self.redis.setex(f"ban_status:{user_id}", 600, "banned")
            return True
        else:
            await self.redis.setex(f"ban_status:{user_id}", 60, "safe")
            return False

    async def _send_rejection(self, message):
        if hasattr(message, 'callback_query') and message.callback_query:
            try:
                await message.bot.answer_callback_query(
                    message.callback_query.id, 
                    text=get_text("flood_msg"), 
                    show_alert=True
                )
            except Exception: pass

    async def post_process(self, message, data, exception):
        pass