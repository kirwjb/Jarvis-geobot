import hashlib

import aiohttp

from src.config import NOMINATIM_URLS
from src.utils.API_codes import get_api_error_message
from src.utils.utils import error, log


TOURISM_TYPES = "attraction|museum|viewpoint|gallery|theme_park"
HISTORIC_TYPES = "monument|memorial|castle|ruins|church|cathedral|manor"

NOMINATIM_URL = NOMINATIM_URLS[0] if OVERPASS_URLS else "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent": "JARVIS-Travel-Bot/1.0",
}

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


async def get_city_coords(
    city: str,
) -> tuple[float | None, float | None]:

    params = {
        "q": city,
        "format": "json",
        "limit": 1,
        "accept-language": "ru",
    }

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(
                NOMINATIM_URL,
                params=params,
                timeout=10,
            ) as response:

                if response.status != 200:
                    error(
                        f"Nominatim {response.status}: "
                        f"{get_api_error_message(response.status)}"
                    )
                    return None, None

                data = await response.json()

                if not data:
                    log(f"Nominatim: город не найден: {city}")
                    return None, None

                return (
                    float(data[0]["lat"]),
                    float(data[0]["lon"]),
                )

    except Exception as exc:
        error(f"Ошибка получения координат города {city}: {exc}")
        return None, None


async def get_attractions_osm(
    city: str,
    limit: int = 100,
) -> list[dict]:

    lat, lon = await get_city_coords(city)

    if lat is None or lon is None:
        return []

    bbox = (
        f"{lat - 0.1},"
        f"{lon - 0.15},"
        f"{lat + 0.1},"
        f"{lon + 0.15}"
    )

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

    async with aiohttp.ClientSession(headers=HEADERS) as session:

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
                        key=lambda item: item["name"].lower()
                    )

                    log(
                        f"Получено {len(attractions)} "
                        f"достопримечательностей для {city}"
                    )

                    return attractions[:limit]

            except Exception as exc:
                error(
                    f"Ошибка Overpass {url}: {exc}"
                )

    error(
        f"Все зеркала Overpass недоступны для {city}"
    )

    return []


def _parse_attractions(
    elements: list[dict],
) -> list[dict]:

    attractions = []
    seen = set()

    for element in elements:

        tags = element.get("tags", {})

        name = tags.get("name")

        if not name:
            continue

        lat = (
            element.get("lat")
            or element.get("center", {}).get("lat")
        )

        lon = (
            element.get("lon")
            or element.get("center", {}).get("lon")
        )

        if lat is None or lon is None:
            continue

        key = (
            name,
            round(lat, 4),
            round(lon, 4),
        )

        if key in seen:
            continue

        seen.add(key)

        place_id = _build_place_id(
            element,
            name,
            lat,
            lon,
        )

        object_type = (
            tags.get("tourism")
            or tags.get("historic")
            or "attraction"
        )

        address = _build_address(tags)

        attractions.append({
            "id": place_id,
            "name": name,
            "address": address,
            "lat": lat,
            "lon": lon,
            "type": TYPE_MAP.get(
                object_type,
                object_type.replace("_", " ").capitalize(),
            ),
            "hours": tags.get("opening_hours") or None,
            "phone": tags.get("phone") or None,
        })

    return attractions


def _build_place_id(
    element: dict,
    name: str,
    lat: float,
    lon: float,
) -> str:

    element_type = element.get("type", "place")
    raw_id = element.get("id")

    if raw_id is not None:
        return f"osm:{element_type}:{raw_id}"

    source = f"{name}|{lat}|{lon}"

    digest = hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()[:16]

    return f"osm:{digest}"


def _build_address(tags: dict) -> str:

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

    return address or tags.get("addr:full", "")