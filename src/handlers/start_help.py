from telebot import types
from telebot.async_telebot import AsyncTeleBot


MINI_APP_URL = "https://t.me/Jarvis67_676767bot/jarvis_geo"


START_TEXT = """🤖 <b>JARVIS GeoBot</b>

Помогу исследовать города, находить интересные места, строить маршруты и смотреть погоду.

Открой Mini App кнопкой ниже.

<b>Частые вопросы</b>

<b>Как начать?</b>
Нажми «Открыть JARVIS» и выбери регион и город.

<b>Как найти места?</b>
После выбора города можно открыть ленту мест и отфильтровать её по категориям.

<b>Как добавить место в избранное?</b>
Нажми ❤️ на карточке места. Избранное доступно во вкладке «Избранное».

<b>Как построить маршрут?</b>
Добавляй интересные места кнопкой «＋» в маршрут, затем открой экран маршрута.

<b>Почему фотографии загружаются не сразу?</b>
Для некоторых мест изображение подгружается отдельно. Если источник фотографии не найден, останется стандартная заглушка.

<b>Можно ли открыть погоду?</b>
Да. Выбери город и перейди в раздел погоды.

<b>Что делать, если что-то не работает?</b>
Попробуй вернуться назад и открыть раздел заново. Если проблема повторяется — сообщи, что именно произошло и на каком экране.

Команда <code>/help</code> показывает эту же памятку."""


async def register_start_help_handlers(bot: AsyncTeleBot) -> None:
    @bot.message_handler(commands=["start", "help"])
    async def start_help(message: types.Message):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text="🗺 Открыть JARVIS",
                url=MINI_APP_URL,
            )
        )
        await bot.send_message(
            message.chat.id,
            START_TEXT,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
