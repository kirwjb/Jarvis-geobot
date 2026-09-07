import asyncio
import hashlib

import aiohttp

from src.config import NOMINATIM_URLS, OVERPASS_URLS
from src.utils.API_codes import get_api_error_message
from src.utils.utils import error, log

TOURISM_TYPES = "attraction|museum|viewpoint|gallery|theme_park"
HISTORIC_TYPES = "monument|memorial|castle|ruins|church|cathedral|manor"
NOMINATIM_URL = NOMINATIM_URLS[0] if NOMINATIM_URLS else "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "JARVIS-Travel-Bot/1.0"}
TYPE_MAP = {"museum":"Музей","attraction":"Достопримечательность","gallery":"Галерея","viewpoint":"Смотровая площадка","monument":"Памятник","memorial":"Мемориал","castle":"Замок","ruins":"Руины","church":"Церковь","cathedral":"Собор","manor":"Усадьба","theme_park":"Парк аттракционов"}

CITY_BBOXES = {
    # Municipal boundary fallback for cases where Nominatim returns a point-only result.
    "минск": (53.75, 27.35, 54.05, 27.75),
}

async def get_city_bounds(city: str, country: str = "Belarus") -> tuple[float, float, float, float] | None:
    key = city.strip().lower()
    if key in CITY_BBOXES:
        return CITY_BBOXES[key]
    params={"q":f"{city}, {country}","format":"json","limit":1,"addressdetails":1,"accept-language":"ru"}
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(NOMINATIM_URL,params=params,timeout=10) as response:
                if response.status != 200:
                    error(f"Nominatim {response.status}: {get_api_error_message(response.status)}"); return None
                data=await response.json()
                if not data: log(f"Nominatim: город не найден: {city}"); return None
                box=data[0].get("boundingbox")
                if box and len(box)==4:
                    south,north,west,east=map(float,box)
                    return south,west,north,east
                return None
    except Exception as exc:
        error(f"Ошибка получения границ города {city}: {exc}"); return None

async def get_city_coords(city: str, country: str = "Belarus") -> tuple[float | None, float | None]:
    bounds = await get_city_bounds(city, country)
    if bounds:
        south,west,north,east=bounds
        return (south+north)/2,(west+east)/2
    return None,None

async def get_attractions_osm(city: str, limit: int = 100, country: str = "Belarus") -> list[dict]:
    bounds = await get_city_bounds(city, country)
    if not bounds:return []
    south,west,north,east=bounds
    # Nominatim occasionally returns a very wide administrative box. Keep a sane
    # cap around the city while still covering large cities much better than the old fixed bbox.
    lat_span=min(max(north-south,0.02),0.45); lon_span=min(max(east-west,0.02),0.60)
    lat=(south+north)/2; lon=(west+east)/2
    if north-south>lat_span: south,north=lat-lat_span/2,lat+lat_span/2
    if east-west>lon_span: west,east=lon-lon_span/2,lon+lon_span/2
    bbox=f"{south},{west},{north},{east}"
    query=f'''[out:json][timeout:60];(node["tourism"~"{TOURISM_TYPES}"]({bbox});way["tourism"~"{TOURISM_TYPES}"]({bbox});node["historic"~"{HISTORIC_TYPES}"]({bbox});way["historic"~"{HISTORIC_TYPES}"]({bbox}););out tags center;'''
    timeout=aiohttp.ClientTimeout(total=90, connect=15)
    async with aiohttp.ClientSession(headers=HEADERS,timeout=timeout) as session:
        for url in OVERPASS_URLS:
            for attempt in range(3):
                try:
                    log(f"Overpass: {city} → {url} (attempt {attempt+1}/3, bbox={bbox})")
                    async with session.post(url,data={"data":query}) as response:
                        if response.status != 200:
                            error(f"Overpass {response.status}: {get_api_error_message(response.status)}")
                            if response.status in {400,429,500,502,503,504} and attempt<2:
                                await asyncio.sleep(1.5*(2**attempt)); continue
                            break
                        data=await response.json(content_type=None)
                        attractions=_parse_attractions(data.get("elements",[])); attractions.sort(key=lambda x:x["name"].lower())
                        log(f"Получено {len(attractions)} достопримечательностей для {city}")
                        return attractions if limit <= 0 else attractions[:limit]
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                    error(f"Ошибка Overpass {url} attempt {attempt+1}/3: {exc}")
                    if attempt<2: await asyncio.sleep(1.5*(2**attempt))
                except Exception as exc:
                    error(f"Ошибка Overpass {url}: {exc}"); break
    error(f"Все зеркала Overpass недоступны для {city}"); return []

def _parse_attractions(elements:list[dict])->list[dict]:
    attractions=[];seen=set()
    for element in elements:
        tags=element.get("tags",{});name=tags.get("name")
        if not name:continue
        lat=element.get("lat") or element.get("center",{}).get("lat");lon=element.get("lon") or element.get("center",{}).get("lon")
        if lat is None or lon is None:continue
        key=(name,round(lat,4),round(lon,4))
        if key in seen:continue
        seen.add(key);place_id=_build_place_id(element,name,lat,lon);object_type=tags.get("tourism") or tags.get("historic") or "attraction"
        attractions.append({"id":place_id,"name":name,"address":_build_address(tags),"lat":lat,"lon":lon,"type":TYPE_MAP.get(object_type,object_type.replace("_"," ").capitalize()),"hours":tags.get("opening_hours") or None,"phone":tags.get("phone") or None})
    return attractions

def _build_place_id(element:dict,name:str,lat:float,lon:float)->str:
    raw_id=element.get("id")
    if raw_id is not None:return f"osm:{element.get('type','place')}:{raw_id}"
    digest=hashlib.sha256(f"{name}|{lat}|{lon}".encode("utf-8")).hexdigest()[:16];return f"osm:{digest}"

def _build_address(tags:dict)->str:
    return ", ".join(filter(None,(tags.get("addr:street"),tags.get("addr:housenumber"),tags.get("addr:city")))) or tags.get("addr:full","")
