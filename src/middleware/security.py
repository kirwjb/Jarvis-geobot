from telebot.handler_backends import BaseMiddleware, CancelUpdate
from telebot.types import CallbackQuery
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import User
from src.config import SUPERADMINS
from src.services.rbac import is_superadmin, resolve_user_role, Role
from src.utils.redis_keys import RedisKeys
from .limiter import RateLimiter
from src.utils.languages import get_text

class CancelPayload(dict, CancelUpdate):
    """Payload returned by middleware to halt TeleBot update processing."""
    def __init__(self):
        dict.__init__(self, {"cancel": True})
        CancelUpdate.__init__(self)

    def __eq__(self, other):
        if other == "cancel" or other == {"cancel": True}:
            return True
        return super().__eq__(other)

class SecurityMiddleware(BaseMiddleware):
    def __init__(self, redis_client):
        super().__init__()
        self.redis = redis_client
        self.limiter = RateLimiter(redis_client)
        self.update_types = ['message', 'callback_query']

    async def pre_process(self, message, data):
        if hasattr(message, "from_user") and message.from_user:
            user = message.from_user
        elif hasattr(message, "callback_query") and message.callback_query:
            user = getattr(message.callback_query, "from_user", None)
        else:
            user = None
        if not user:
            return

        user_id = user.id

        if is_superadmin(user_id):
            return

        maintenance = await self.redis.get(RedisKeys.maintenance())
        if maintenance == "1":
            user_is_admin = await self._is_admin(user_id)
            if not user_is_admin:
                if isinstance(message, CallbackQuery):
                    try:
                        await message.bot.answer_callback_query(
                            message.id,
                            text=get_text("maintenance_mode_msg"),
                            show_alert=True,
                        )
                    except Exception:
                        pass
                else:
                    chat_id = getattr(message, "chat", None)
                    if chat_id and hasattr(chat_id, "id"):
                        try:
                            await message.bot.send_message(chat_id.id, get_text("maintenance_mode_msg"))
                        except Exception:
                            pass
                return CancelPayload()

        if not await self.limiter.is_allowed(user_id):
            await self._send_rejection(message)
            return CancelPayload()

        if await self._is_banned(user_id):
            if isinstance(message, CallbackQuery):
                try:
                    await message.bot.answer_callback_query(
                        message.id,
                        text="⛔ Вы заблокированы в системе.",
                        show_alert=True,
                    )
                except Exception:
                    pass
            return CancelPayload()

        if await self._is_muted(user_id):
            if isinstance(message, CallbackQuery):
                try:
                    await message.bot.answer_callback_query(
                        message.id,
                        text="🔇 Ваши сообщения ограничены модератором (режим mute).",
                        show_alert=True,
                    )
                except Exception:
                    pass
            else:
                chat = getattr(message, "chat", None)
                if chat and hasattr(chat, "id"):
                    try:
                        await message.bot.send_message(
                            chat.id,
                            "🔇 Ваши сообщения ограничены модератором (режим mute).",
                        )
                    except Exception:
                        pass
            return CancelPayload()

    async def _is_admin(self, user_id: int) -> bool:
        if is_superadmin(user_id):
            return True
        cached = await self.redis.get(f"admin_status:{user_id}")
        if cached == "admin":
            return True
        if cached == "user":
            return False

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User.role, User.is_admin).where(User.user_id == user_id)
            )
            row = result.first()
            if not row:
                return False
            db_role, is_adm = row[0], row[1]
            role = resolve_user_role(user_id, db_role, is_adm)
            is_admin_flag = role >= Role.ADMIN

        status_str = "admin" if is_admin_flag else "user"
        await self.redis.setex(f"admin_status:{user_id}", 300, status_str)
        return is_admin_flag

    async def _is_banned(self, user_id: int) -> bool:
        cached = await self.redis.get(RedisKeys.ban(user_id))
        if cached in ("banned", "1"):
            return True
        if cached in ("safe", "0"):
            return False

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User.is_banned).where(User.user_id == user_id))
            is_banned = result.scalar_one_or_none()

        if is_banned:
            await self.redis.setex(RedisKeys.ban(user_id), 600, "banned")
            return True
        else:
            await self.redis.setex(RedisKeys.ban(user_id), 60, "safe")
            return False

    async def _is_muted(self, user_id: int) -> bool:
        cached = await self.redis.get(RedisKeys.mute(user_id))
        if cached in ("muted", "1"):
            return True
        if cached in ("safe", "0"):
            return False

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User.is_muted).where(User.user_id == user_id))
            is_muted = result.scalar_one_or_none()

        if is_muted:
            await self.redis.setex(RedisKeys.mute(user_id), 600, "muted")
            return True
        else:
            await self.redis.setex(RedisKeys.mute(user_id), 60, "safe")
            return False

    async def _send_rejection(self, message):
        if isinstance(message, CallbackQuery):
            try:
                await message.bot.answer_callback_query(
                    message.id, 
                    text=get_text("flood_msg"), 
                    show_alert=True
                )
            except Exception:
                pass
        elif hasattr(message, "chat") and getattr(message, "chat", None) is not None:
            chat = message.chat
            chat_id = getattr(chat, "id", None)
            if chat_id:
                try:
                    await message.bot.send_message(chat_id, get_text("flood_msg"))
                except Exception:
                    pass
        elif getattr(message, 'callback_query', None) is not None:
            try:
                await message.bot.answer_callback_query(
                    message.callback_query.id, 
                    text=get_text("flood_msg"), 
                    show_alert=True
                )
            except Exception:
                pass

    async def post_process(self, message, data, exception):
        pass
