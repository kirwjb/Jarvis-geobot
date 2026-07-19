import aiohttp
from src.utils.utils import error
from src.utils.API_codes import get_api_error_message
async def get_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{city}?format=%C+%t&lang=ru"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    return (await response.text()).strip()
                else:
                    error_msg = get_api_error_message(response.status)
                    error(f"Ошибка при получении погоды для города {city}: {error_msg}")

        return "Ошибка при получении данных о погоде. Пожалуйста, попробуйте позже."
    except Exception as e:
        error(f"Ошибка получения погоды: {e}")
        return "Ошибка при получении данных о погоде. Пожалуйста, попробуйте позже."