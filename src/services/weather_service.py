import json
import re
from datetime import datetime
from typing import Any, List, Optional
from urllib.parse import quote

import aiohttp
from pydantic import BaseModel, ConfigDict, Field

from src.utils.API_codes import get_api_error_message
from src.utils.utils import error

WTTR_URL = "https://wttr.in/{city}?format=j1&lang={lang}"

_EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50\u2b55\u203c\u2049\u2122\u2139\u25aa\u25ab\u25b6\u25c0\u25fb-\u25fe]"
)

def strip_emojis(text: Optional[str]) -> str:
    """Removes any unicode emojis/stickers from text to guarantee clean typography."""
    if not text:
        return ""
    return _EMOJI_PATTERN.sub("", str(text)).strip()

CITY_SELECTION_REMINDERS = {
    "ru": "Сначала выберите город в разделе «Путешествия».",
    "by": "Спачатку выберыце горад у раздзеле «Падарожжы».",
    "be": "Спачатку выберыце горад у раздзеле «Падарожжы».",
}

class WeatherHourlyItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    time: str
    temp: Optional[float] = None
    chance_of_rain: Optional[int] = None
    chanceofrain: Optional[int] = None
    description: str = ""

class WeatherDaySummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: str
    max_temp: Optional[float] = None
    min_temp: Optional[float] = None
    maxtempC: Optional[float] = None
    mintempC: Optional[float] = None

class WeatherDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    city: str
    temp: Optional[float] = None
    feels_like: Optional[float] = None
    description: str = ""
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    pressure: Optional[int] = None
    uv_index: Optional[float] = None
    visibility: Optional[float] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    hourly: List[WeatherHourlyItem] = Field(default_factory=list)
    forecast: List[WeatherDaySummary] = Field(default_factory=list)
    cached: bool = False
    requires_city_selection: bool = False

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

def format_time_12_to_24(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    cleaned = str(val).strip()
    try:
        return datetime.strptime(cleaned, "%I:%M %p").strftime("%H:%M")
    except Exception:
        return cleaned

def format_hourly_time(val: Any) -> str:
    if val is None:
        return ""
    try:
        num = int(val)
        hours = (num // 100) % 24
        minutes = num % 100
        return f"{hours:02d}:{minutes:02d}"
    except (ValueError, TypeError):
        return str(val).strip()

def extract_description(item: dict) -> str:
    for key in ("lang_be", "lang_ru", "lang_xx", "weatherDesc"):
        val_list = item.get(key)
        if isinstance(val_list, list) and len(val_list) > 0:
            first = val_list[0]
            if isinstance(first, dict):
                text = str(first.get("value") or "").strip()
                if text:
                    return strip_emojis(text)
            elif isinstance(first, str) and first.strip():
                return strip_emojis(first.strip())
    return ""

def to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def to_int(value: Any) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

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
                "feels_like": None,
                "description": reminder,
                "humidity": None,
                "wind_speed": None,
                "pressure": None,
                "uv_index": None,
                "visibility": None,
                "sunrise": None,
                "sunset": None,
                "hourly": [],
                "forecast": [],
                "reminder": reminder,
                "requires_city_selection": True,
            },
            ensure_ascii=False,
        )

    city_cleaned = str(city).strip()
    if "{lang}" in WTTR_URL:
        api_lang = "be" if (lang or "").lower() in ("by", "be") else (lang or "ru").lower()
        url = WTTR_URL.format(city=quote(city_cleaned), lang=api_lang)
    else:
        url = WTTR_URL.format(city=quote(city_cleaned))

    try:
        timeout = aiohttp.ClientTimeout(total=8)
        headers = {
            "User-Agent": "Jarvis-GeoBot/1.0",
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

        weather_days = payload.get("weather") or []
        first_day = weather_days[0] if (isinstance(weather_days, list) and len(weather_days) > 0 and isinstance(weather_days[0], dict)) else {}
        astronomy_list = first_day.get("astronomy") or []
        astronomy = astronomy_list[0] if (isinstance(astronomy_list, list) and len(astronomy_list) > 0 and isinstance(astronomy_list[0], dict)) else {}

        sunrise = format_time_12_to_24(astronomy.get("sunrise"))
        sunset = format_time_12_to_24(astronomy.get("sunset"))

        hourly_list = first_day.get("hourly") or []
        hourly = []
        if isinstance(hourly_list, list):
            for h in hourly_list:
                if not isinstance(h, dict):
                    continue
                h_rain = to_int(h.get("chanceofrain"))
                hourly.append({
                    "time": format_hourly_time(h.get("time")),
                    "temp": to_float(h.get("tempC")),
                    "chance_of_rain": h_rain,
                    "chanceofrain": h_rain,
                    "description": extract_description(h),
                })

        forecast = []
        if isinstance(weather_days, list):
            for day in weather_days[:3]:
                if not isinstance(day, dict):
                    continue
                d_max = to_float(day.get("maxtempC"))
                d_min = to_float(day.get("mintempC"))
                forecast.append({
                    "date": str(day.get("date") or ""),
                    "max_temp": d_max,
                    "min_temp": d_min,
                    "maxtempC": d_max,
                    "mintempC": d_min,
                })

        description = extract_description(current)

        wind_kmh = to_float(current.get("windspeedKmph"))
        wind_ms = round(wind_kmh / 3.6, 1) if wind_kmh is not None else None

        return json.dumps(
            {
                "city": city_cleaned,
                "temp": to_float(current.get("temp_C")),
                "feels_like": to_float(current.get("FeelsLikeC")),
                "description": strip_emojis(description) or "Нет данных",
                "humidity": to_int(current.get("humidity")),
                "wind_speed": wind_ms,
                "pressure": to_int(current.get("pressure")),
                "uv_index": to_float(current.get("uvIndex")),
                "visibility": to_float(current.get("visibility")),
                "sunrise": sunrise,
                "sunset": sunset,
                "hourly": hourly,
                "forecast": forecast,
                "requires_city_selection": False,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        error(f"Ошибка получения погоды для {city_cleaned}: {exc}")
        raise
