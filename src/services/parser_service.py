import hashlib

import aiohttp

from src.config import OVERPASS_URLS
from src.utils.API_codes import get_api_error_message
from src.utils.utils import error, log
from src.services.wiki_service import get_wiki_photo


TOURISM_TYPES = "attraction|museum|viewpoint|gallery|theme_park"
HISTORIC_TYPES = "monument|memorial|castle|ruins|church|cathedral|manor"

TYPE_MAP = {
    "museum": "Музей",
    "attraction": "Достопримечательность",
    "gallery": "Галерея",
    "viewpoint": "Смотровая площадка",
    "monument": "Памятник",
    "memorial": "Мемориал",
    "castle": "Замок",
    "ruins": "Руины",
    "church": "Церковь",
    "cathedral": "Собор",
    "manor": "Усадьба",
    "theme_park": "Парк аттракционов",
}


async def get_city_coords(city: str) -> tuple[float | None, float | None]:
    url = OVERPASS_URLS[0] if OVERPASS_URLS else "https://nominatim.openstreetmap.org/search"

    params = {
        "q": city,
        "format": "json",
        "limit": 1,
        "accept-language": "ru",
    }

    headers = {
        "User-Agent": "JARVIS-Travel-Bot/1.0",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=10,
            ) as response:

                if response.status != 200:
                    error(
                        f"Ошибка Nominatim {response.status}: "
                        f"{get_api_error_message(response.status)}"
                    )
                    return None, None

                data = await response.json()

                if not data:
                    return None, None

                return float(data[0]["lat"]), float(data[0]["lon"])

    except Exception as exc:
        error(f"Ошибка получения координат города: {exc}")
        return None, None


async def get_attractions_osm(
    city: str,
    limit: int = 100,
) -> list[dict]:

    lat, lon = await get_city_coords(city)

    if lat is None or lon is None:
        return []

    bbox = f"{lat - 0.1},{lon - 0.15},{lat + 0.1},{lon + 0.15}"

    query = f"""
    [out:json][timeout:15];
    (
        node["tourism"~"{TOURISM_TYPES}"]({bbox});
        way["tourism"~"{TOURISM_TYPES}"]({bbox});

        node["historic"~"{HISTORIC_TYPES}"]({bbox});
        way["historic"~"{HISTORIC_TYPES}"]({bbox});
    );
    out tags center;
    """

    async with aiohttp.ClientSession() as session:

        for url in OVERPASS_URLS:
            try:
                log(f"Overpass: {city} → {url}")

                async with session.post(
                    url,
                    data={"data": query},
                    timeout=20,
                ) as response:

                    if response.status != 200:
                        error(
                            f"Overpass {response.status}: "
                            f"{get_api_error_message(response.status)}"
                        )
                        continue

                    data = await response.json()
                    attractions = _parse_attractions(
                        data.get("elements", [])
                    )

                    attractions.sort(
                        key=lambda item: item["name"]
                    )

                    log(
                        f"Получено {len(attractions)} "
                        f"достопримечательностей для {city}"
                    )

                    return attractions[:limit]

            except Exception as exc:
                error(f"Overpass {url}: {exc}")

    error(f"Все зеркала Overpass недоступны для {city}")
    return []


def _parse_attractions(elements: list[dict]) -> list[dict]:
    attractions = []
    seen = set()

    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name")

        if not name:
            continue

        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")

        if lat is None or lon is None:
            continue

        key = (name, round(lat, 4), round(lon, 4))

        if key in seen:
            continue

        seen.add(key)

        raw_id = str(element.get("id", ""))
        place_id = (
            raw_id
            if raw_id.isdigit()
            else hashlib.md5(
                f"{name}|{lat}|{lon}".encode()
            ).hexdigest()[:12]
        )

        object_type = (
            tags.get("tourism")
            or tags.get("historic")
            or "attraction"
        )

        address = ", ".join(
            filter(
                None,
                (
                    tags.get("addr:street"),
                    tags.get("addr:housenumber"),
                    tags.get("addr:city"),
                ),
            )
        )

        attractions.append({
            "id": place_id,
            "name": name,
            "address": address or tags.get("addr:full", ""),
            "lat": lat,
            "lon": lon,
            "type": TYPE_MAP.get(
                object_type,
                object_type.replace("_", " ").capitalize(),
            ),
            "hours": tags.get("opening_hours", ""),
            "phone": tags.get("phone", ""),
            "image_url": _get_osm_image(tags),
        })

    return attractions


def _get_osm_image(tags: dict) -> str:
    image = tags.get("image")

    if image and image.startswith("http"):
        return image

    return ""