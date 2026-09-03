import aiohttp
import asyncio

from src.utils.utils import error
from src.utils.API_codes import get_api_error_message


OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


async def get_distance_osrm(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float | None:

    url = (
        f"{OSRM_URL}/"
        f"{lon1},{lat1};{lon2},{lat2}"
    )

    params = {
        "overview": "false",
        "annotations": "false",
    }

    try:
        async with aiohttp.ClientSession() as session:

            async with session.get(
                url,
                params=params,
                timeout=5,
            ) as response:

                if response.status != 200:

                    error(
                        f"Ошибка OSRM {response.status}: "
                        f"{get_api_error_message(response.status)}"
                    )

                    return None

                data = await response.json()

                routes = data.get("routes")

                if not routes:
                    error(
                        "OSRM не вернул маршруты"
                    )
                    return None

                distance_m = routes[0].get(
                    "distance"
                )

                if distance_m is None:
                    error(
                        "OSRM не вернул distance"
                    )
                    return None

                return float(distance_m) / 1000

    except asyncio.TimeoutError:

        error(
            "OSRM: превышено время ожидания"
        )
        return None

    except aiohttp.ClientError as exc:

        error(
            f"Ошибка HTTP при обращении к OSRM: {exc}"
        )
        return None

    except Exception as exc:

        error(
            f"Неожиданная ошибка OSRM: {exc}"
        )
        return None