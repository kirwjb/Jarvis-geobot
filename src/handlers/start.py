import datetime
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import User
from src.utils.utils import log, error

MINI_APP_URL = "https://t.me/Jarvis67_676767bot/jarvis_geo"

START_TEXT = """
<b>🗺️ JARVIS GeoBot</b>

Исследуй города, находи интересные места, сохраняй избранное,
планируй маршруты и проверяй погоду в пару кликов.

<b>Доступные команды:</b>

<code>/start</code> — открыть JARVIS
<code>/help</code> — главное меню и справка
<code>/support</code> — связаться с разработчиком

<i>Разработано <b>Кириллом Изотовым</b> (kirwjb@gmail.com)</i>
"""


def _open_app_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            text="🚀 Открыть JARVIS",
            url=MINI_APP_URL,
        ),
        types.InlineKeyboardButton(
            text="💬 Связаться с поддержкой",
            callback_data="help_support",
        ),
    )
    return keyboard


async def ensure_db_user(user_id: int, username: str | None) -> User:
    """Entry point to database: guarantees user exists in PostgreSQL."""
    async with AsyncSessionLocal() as session:
        try:
            user = await session.get(User, user_id)
            if not user:
                user = User(
                    user_id=user_id,
                    username=username,
                    tokens=10,
                    last_reset=datetime.date.today(),
                    is_banned=False,
                    is_admin=False,
                )
                session.add(user)
                await session.commit()
                log(f"DB Entry: Created new user #{user_id} (@{username})")
            else:
                if username and user.username != username:
                    user.username = username
                    await session.commit()
                    log(f"DB Entry: Updated username for #{user_id} -> @{username}")
            return user
        except Exception as exc:
            await session.rollback()
            error(f"DB Entry error for user #{user_id}: {exc}")
            raise


async def register_start_handlers(bot: AsyncTeleBot) -> None:
    """Register welcoming start/help handlers acting as DB entry points."""

    @bot.message_handler(commands=["start", "help"])
    async def start_help(message: types.Message) -> None:
        user_id = message.from_user.id
        username = message.from_user.username
        try:
            await ensure_db_user(user_id, username)
        except Exception:
            pass  # Do not block welcome response if DB has a temporary glitch

        await bot.send_message(
            chat_id=message.chat.id,
            text=START_TEXT,
            parse_mode="HTML",
            reply_markup=_open_app_keyboard(),
            disable_web_page_preview=True,
        )

    @bot.message_handler(commands=["support"])
    async def support_command(message: types.Message) -> None:
        await bot.send_message(
            chat_id=message.chat.id,
            text=(
                "Возникли вопросы или предложения?\n\n"
                "Напишите автору: "
                '<a href="mailto:kirwjb@gmail.com">kirwjb@gmail.com</a>'
            ),
            parse_mode="HTML",
        )

    @bot.callback_query_handler(func=lambda call: call.data == "help_support")
    async def support_callback(call: types.CallbackQuery) -> None:
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            chat_id=call.message.chat.id,
            text=(
                "Возникли вопросы или предложения?\n\n"
                "Напишите автору: "
                '<a href="mailto:kirwjb@gmail.com">kirwjb@gmail.com</a>'
            ),
            parse_mode="HTML",
        )
