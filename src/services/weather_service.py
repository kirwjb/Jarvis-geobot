import aiohttp
from urllib.parse import quote

from src.utils.utils import error
from src.utils.API_codes import get_api_error_message


WTTR_URL = "https://wttr.in/{city}?format=j1&lang=ru"


async def get_weather(city: str) -> dict:
    """Получает структурированные текущие погодные данные из wttr.in."""
    city = (city or "").strip()
    if not city:
        raise ValueError("City is required")

    url = WTTR_URL.format(city=quote(city))

    try:
        timeout = aiohttp.ClientTimeout(total=8)
        headers = {"User-Agent": "Jarvis-GeoBot/1.0"}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    error_msg = get_api_error_message(response.status)
                    error(
                        f"Ошибка при получении погоды для города {city}: "
                        f"{error_msg}"
                    )
                    raise RuntimeError(
                        f"Weather provider returned HTTP {response.status}"
                    )

                payload = await response.json(content_type=None)

        current = (payload.get("current_condition") or [None])[0]
        if not current:
            raise RuntimeError("Weather provider returned no current conditions")

        description_items = current.get("weatherDesc") or []
        description = ""
        if description_items:
            description = str(description_items[0].get("value") or "").strip()

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

        # wttr.in отдаёт скорость ветра в км/ч; API Jarvis использует м/с.
        wind_kmh = to_float(current.get("windspeedKmph"))
        wind_ms = round(wind_kmh / 3.6, 1) if wind_kmh is not None else None

        return {
            "temp": to_float(current.get("temp_C")),
            "description": description or "Нет данных",
            "humidity": to_int(current.get("humidity")),
            "wind_speed": wind_ms,
            "pressure": to_int(current.get("pressure")),
        }
    except Exception as exc:
        error(f"Ошибка получения погоды для {city}: {exc}")
        raise
