import asyncio
import hashlib
import json

import aiohttp

from src.config import NOMINATIM_URLS, OVERPASS_URLS
from src.database.session_manager import redis_client
from src.utils.API_codes import get_api_error_message
from src.utils.utils import error, log

TOURISM_TYPES = "attraction|museum|viewpoint|gallery|theme_park"
HISTORIC_TYPES = "monument|memorial|castle|ruins|church|cathedral|manor|fort|fortification|city_gate"
AMENITY_TYPES = "place_of_worship"
HEADERS = {"User-Agent": "JarvisTravelBot/2.4 (https://t.me/jarvis_travel_bot; travel-geobot-edu)"}
TYPE_MAP = {
    "museum": "Музей",
    "attraction": "Достопримечательность",
    "gallery": "Галерея",
    "viewpoint": "Смотровая площадка",
    "monument": "Памятник",
    "memorial": "Мемориал",
    "castle": "Замок",
    "fort": "Форт",
    "fortification": "Укрепление",
    "city_gate": "Городские ворота",
    "ruins": "Руины",
    "church": "Церковь",
    "cathedral": "Собор",
    "place_of_worship": "Храм",
    "manor": "Усадьба",
    "theme_park": "Парк аттракционов",
}

async def _fetch_with_fallback(urls: list[str], params: dict = None, data: dict = None, method: str = "GET", timeout_sec: int = 20, cache_key: str = None, cache_ttl: int = 86400):
    if cache_key:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                log(f"Redis cache hit for {cache_key}")
                return json.loads(cached)
        except Exception as e:
            error(f"Redis get error for {cache_key}: {e}")

    timeout = aiohttp.ClientTimeout(total=timeout_sec, connect=5)

    pool = list(urls)

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        for url in pool:
            for attempt in range(3):
                try:
                    log(f"OSM fetch: {method} {url} (attempt {attempt+1}/3)")
                    if method.upper() == "GET":
                        request_ctx = session.get(url, params=params)
                    else:
                        request_ctx = session.post(url, data=data)

                    async with request_ctx as response:
                        if response.status == 200:
                            resp_data = await response.json(content_type=None)
                            if cache_key:
                                try:
                                    await redis_client.setex(cache_key, cache_ttl, json.dumps(resp_data, ensure_ascii=False))
                                except Exception as e:
                                    error(f"Redis set error for {cache_key}: {e}")
                            return resp_data
                        else:
                            error(f"OSM error {response.status} from {url}: {get_api_error_message(response.status)}")
                            if response.status in {429, 500, 502, 503, 504} and attempt < 2:
                                await asyncio.sleep(1.5 * (2 ** attempt))
                                continue
                            break
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                    error(f"OSM network/timeout error on {url} (attempt {attempt+1}/3): {exc}")
                    if attempt < 2:
                        await asyncio.sleep(1.5 * (2 ** attempt))
                    else:
                        break
                except Exception as exc:
                    error(f"OSM unexpected error on {url}: {exc}")
                    break

    error(f"All OSM mirrors exhausted for {method}")
    return None

async def get_city_coords(city: str) -> tuple[float | None, float | None]:
    cache_key = f"osm:coords:{city}"
    params = {"q": f"{city}, Belarus", "format": "json", "limit": 1, "accept-language": "ru"}

    data = await _fetch_with_fallback(
        urls=NOMINATIM_URLS,
        params=params,
        method="GET",
        timeout_sec=15,
        cache_key=cache_key,
        cache_ttl=86400 * 7
    )

    if data and isinstance(data, list) and len(data) > 0:
        return float(data[0]["lat"]), float(data[0]["lon"])

    log(f"Nominatim: город не найден или ошибка: {city}")
    return None, None

async def get_attractions_osm(city: str, limit: int = 500, bbox_scale: float = 1.0) -> list[dict]:
    lat, lon = await get_city_coords(city)
    if lat is None or lon is None:
        return []

    cache_key = f"osm:attractions:{city}" if bbox_scale == 1.0 else f"osm:attractions:{city}:scale_{bbox_scale}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            log(f"Redis cache hit for {cache_key}")
            attractions = json.loads(cached)
            return attractions[:limit]
    except Exception as e:
        error(f"Redis get error for {cache_key}: {e}")

    d_lat = 0.1 * bbox_scale
    d_lon = 0.15 * bbox_scale
    bbox = f"{lat-d_lat},{lon-d_lon},{lat+d_lat},{lon+d_lon}"
    query = (
        f"[out:json][timeout:35];("
        f'node["tourism"~"{TOURISM_TYPES}"]({bbox});'
        f'way["tourism"~"{TOURISM_TYPES}"]({bbox});'
        f'node["historic"~"{HISTORIC_TYPES}"]({bbox});'
        f'way["historic"~"{HISTORIC_TYPES}"]({bbox});'
        f'node["amenity"~"{AMENITY_TYPES}"]({bbox});'
        f'way["amenity"~"{AMENITY_TYPES}"]({bbox});'
        f");out tags center;"
    )

    data = await _fetch_with_fallback(
        urls=OVERPASS_URLS,
        data={"data": query},
        method="POST",
        timeout_sec=35,
        cache_key=None
    )

    if data:
        attractions = _parse_attractions(data.get("elements", []))
        attractions.sort(key=lambda x: x["name"].lower())
        log(f"Получено {len(attractions)} достопримечательностей для {city}")

        if attractions:
            try:
                await redis_client.setex(cache_key, 86400 * 7, json.dumps(attractions, ensure_ascii=False))
            except Exception as e:
                error(f"Redis set error for {cache_key}: {e}")

        return attractions[:limit]

    error(f"Все зеркала Overpass недоступны для {city}")
    return []

def _parse_attractions(elements: list[dict]) -> list[dict]:
    attractions = []
    seen = set()
    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name:ru") or tags.get("name")
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
        place_id = _build_place_id(element, name, lat, lon)
        if tags.get("tourism") in {"museum", "gallery", "viewpoint", "theme_park"}:
            object_type = tags.get("tourism")
        else:
            object_type = tags.get("historic") or tags.get("amenity") or tags.get("tourism") or "attraction"
        attractions.append({
            "id": place_id,
            "name": name,
            "address": _build_address(tags),
            "lat": lat,
            "lon": lon,
            "type": TYPE_MAP.get(object_type, object_type.replace("_", " ").capitalize()),
            "hours": tags.get("opening_hours") or None,
            "phone": tags.get("phone") or None,
        })
    return attractions

def _build_place_id(element: dict, name: str, lat: float, lon: float) -> str:
    raw_id = element.get("id")
    if raw_id is not None:
        return f"osm:{element.get('type', 'place')}:{raw_id}"
    digest = hashlib.sha256(f"{name}|{lat}|{lon}".encode("utf-8")).hexdigest()[:16]
    return f"osm:{digest}"

def _build_address(tags: dict) -> str:
    return ", ".join(filter(None, (tags.get("addr:street"), tags.get("addr:housenumber"), tags.get("addr:city")))) or tags.get("addr:full", "")
