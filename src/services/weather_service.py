import json
from typing import Optional
from urllib.parse import quote

import aiohttp

from src.utils.API_codes import get_api_error_message
from src.utils.utils import error

WTTR_URL = "https://wttr.in/{city}?format=j1&lang={lang}"

CITY_SELECTION_REMINDERS = {
    "ru": "Сначала выберите город в разделе «Путешествия».",
    "by": "Спачатку выберыце горад у раздзеле «Падарожжы».",
    "be": "Спачатку выберыце горад у раздзеле «Падарожжы».",
}


class CityNotSelectedError(ValueError):
    """Исключение: город не выбран или передан некорректный идентификатор."""

    def __init__(self, message: str, lang: str = "ru"):
        self.message = message
        self.lang = lang
        super().__init__(message)


def is_city_missing(city: Optional[str]) -> bool:
    """Проверяет, передан ли валидный город или пустое значение/плейсхолдер."""
    if city is None:
        return True
    cleaned = str(city).strip().lower()
    return cleaned in ("", "none", "null", "undefined", "nan", "0")


def get_city_selection_reminder(lang: str = "ru") -> str:
    """Возвращает локализованное напоминание о необходимости сначала выбрать город на RU или BY."""
    key = (lang or "ru").strip().lower()
    if key in ("by", "be"):
        return CITY_SELECTION_REMINDERS["by"]
    if key == "ru":
        return CITY_SELECTION_REMINDERS["ru"]
    return f"{CITY_SELECTION_REMINDERS['ru']} / {CITY_SELECTION_REMINDERS['by']}"


async def get_weather(
    city: Optional[str] = None,
    lang: str = "ru",
    raise_on_missing: bool = False,
) -> str:
    """Получает текущую погоду из wttr.in и возвращает JSON-строку.

    Если город не выбран (None, 'none', 'null', пустая строка), перехватывает это
    и возвращает напоминание на поддерживаемом языке (RU/BY) о необходимости выбрать город.
    """
    if is_city_missing(city):
        reminder = get_city_selection_reminder(lang)
        if raise_on_missing:
            raise CityNotSelectedError(reminder, lang=lang)
        return json.dumps(
            {
                "city": str(city) if city is not None else "",
                "temp": None,
                "description": reminder,
                "humidity": None,
                "wind_speed": None,
                "pressure": None,
                "reminder": reminder,
                "requires_city_selection": True,
            },
            ensure_ascii=False,
        )

    city_cleaned = str(city).strip()
    api_lang = "ru" if (lang or "").lower() in ("ru", "by", "be") else (lang or "ru").lower()
    url = WTTR_URL.format(city=quote(city_cleaned), lang=api_lang)

    try:
        timeout = aiohttp.ClientTimeout(total=8)
        headers = {
            "User-Agent": "Jarvis-GeoBot/1.0",
            "ngrok-skip-browser-warning": "true",
        }

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    error_msg = get_api_error_message(response.status)
                    error(
                        f"Ошибка при получении погоды для города {city_cleaned}: "
                        f"{error_msg}"
                    )
                    raise RuntimeError(
                        f"Weather provider returned HTTP {response.status}"
                    )

                payload = await response.json(content_type=None)

        current = (payload.get("current_condition") or [None])[0]
        if not current:
            raise RuntimeError("Weather provider returned no current conditions")

        descriptions = current.get("weatherDesc") or []
        description = ""
        if descriptions:
            description = str(descriptions[0].get("value") or "").strip()

        def to_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def to_int(value):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return None

        wind_kmh = to_float(current.get("windspeedKmph"))
        wind_ms = round(wind_kmh / 3.6, 1) if wind_kmh is not None else None

        return json.dumps(
            {
                "city": city_cleaned,
                "temp": to_float(current.get("temp_C")),
                "description": description or "Нет данных",
                "humidity": to_int(current.get("humidity")),
                "wind_speed": wind_ms,
                "pressure": to_int(current.get("pressure")),
                "requires_city_selection": False,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        error(f"Ошибка получения погоды для {city_cleaned}: {exc}")
        raise
