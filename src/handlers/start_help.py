from telebot import types
from telebot.async_telebot import AsyncTeleBot

MINI_APP_URL = "https://t.me/Jarvis67_676767bot/jarvis_geo"

START_TEXT = """🤖 **JARVIS GeoBot**

Исследуй города, находи интересные места, сохраняй избранное, планируй маршруты и проверяй погоду в пару кликов.

**📋 Доступные команды:**
`/start` — открыть JARVIS
`/help` — главное меню и справка
`/support` — связаться с разработчиком

*Разработано **Кириллом Морозом** (kirwjb@gmail.com)*"""


def _open_app_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            text="🗺 Открыть JARVIS",
            url=MINI_APP_URL,
        ),
        types.InlineKeyboardButton(
            text="💬 Связаться с поддержкой",
            callback_data="help_support",
        ),
    )
    return keyboard


async def register_start_help_handlers(bot: AsyncTeleBot) -> None:

    @bot.message_handler(commands=["start", "help"])
    async def start_help(message: types.Message) -> None:
        await bot.send_message(
            message.chat.id,
            START_TEXT,
            parse_mode="HTML",
            reply_markup=_open_app_keyboard(),
            disable_web_page_preview=True,
        )

    @bot.message_handler(commands=["support"])
    async def support_command(message: types.Message) -> None:
        await bot.send_message(
            message.chat.id,
            "🛠 Возникли вопросы или предложения? Напишите автору: kirwjb@gmail.com",
            parse_mode="HTML",
        )

    @bot.callback_query_handler(func=lambda call: call.data == "help_support")
    async def support_callback(call: types.CallbackQuery) -> None:
        await bot.answer_callback_query(call.id)
        await bot.send_message(
            call.message.chat.id,
            "🛠 Возникли вопросы или предложения? Напишите автору: kirwjb@gmail.com",
            parse_mode="HTML",
        )