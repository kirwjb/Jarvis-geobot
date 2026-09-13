from telebot import types
from telebot.async_telebot import AsyncTeleBot


# Public Telegram Mini App entry point. Keep this URL in one place so /start and
# /help always point to the same application instance.
MINI_APP_URL = "https://t.me/Jarvis67_676767bot/jarvis_geo"


START_TEXT = """🗺 <b>JARVIS GeoBot</b>

Твой помощник для путешествий по городам.

<b>Что умеет JARVIS</b>
• 🔎 искать интересные места и достопримечательности;
• ❤️ сохранять места в избранное;
• 🧭 собирать собственный маршрут;
• 🌤 смотреть погоду по выбранному городу;
• 👥 планировать поездки вместе с группой.

<b>Как начать</b>
Нажми <b>«Открыть JARVIS»</b>, выбери регион и город — дальше приложение проведёт тебя по основным функциям.

💡 <b>Совет:</b> если открываешь приложение впервые, начни с ленты мест — там проще всего подобрать точки для маршрута.

Нужна инструкция? Используй <code>/help</code>."""


HELP_TEXT = """❓ <b>Как пользоваться JARVIS</b>

<b>🗺 Как начать?</b>
Открой Mini App, выбери регион и город. После этого доступны места, погода, маршрут и избранное.

<b>🔎 Как найти достопримечательности?</b>
Открой ленту мест и используй категории или поиск. Карточка места открывает подробную информацию.

<b>❤️ Как сохранить место?</b>
Нажми кнопку избранного на карточке. Сохранённые места находятся во вкладке <b>«Избранное»</b>.

<b>🧭 Как построить маршрут?</b>
Добавляй понравившиеся точки в маршрут, затем открой экран маршрута и собери нужную последовательность мест.

<b>🌤 Где посмотреть погоду?</b>
Выбери город и открой раздел погоды. Данные показываются для выбранного города.

<b>👥 Зачем нужны группы?</b>
Группа предназначена для совместной поездки: можно указать дату, пригласить участников, предлагать места и голосовать за точки маршрута.

<b>📷 Почему у места может не быть фотографии?</b>
Фотографии берутся из Wikimedia Commons по координатам места. Если подходящего изображения рядом не найдено, показывается стандартная заглушка.

<b>↩️ Что делать, если экран завис?</b>
Вернись назад и открой раздел заново. Если проблема повторяется, запомни город и экран, на котором она возникла — это поможет найти причину.

<b>Команды</b>
<code>/start</code> — открыть приветствие
<code>/help</code> — показать эту памятку"""


def _open_app_keyboard() -> types.InlineKeyboardMarkup:
    """Create the single primary action used by both /start and /help."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            text="🗺 Открыть JARVIS",
            url=MINI_APP_URL,
        )
    )
    return keyboard


async def register_start_help_handlers(bot: AsyncTeleBot) -> None:
    """Register Telegram entry-point commands without duplicating handler logic."""

    @bot.message_handler(commands=["start", "help"])
    async def start_help(message: types.Message):
        """Send a focused welcome message for /start or the FAQ for /help."""
        command = (message.text or "").split(maxsplit=1)[0].lstrip("/").split("@")[0].lower()
        text = HELP_TEXT if command == "help" else START_TEXT

        await bot.send_message(
            message.chat.id,
            text,
            parse_mode="HTML",
            reply_markup=_open_app_keyboard(),
            disable_web_page_preview=True,
        )
