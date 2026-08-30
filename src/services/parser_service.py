import aiohttp
import json
import urllib.parse
import hashlib
from src.config import OVERPASS_URLS, LIMITS, DEFAULT_LIMIT
from src.utils.utils import log, error
from src.utils.API_codes import get_api_error_message

async def get_city_coords(city: str) -> tuple[float | None, float | None]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city, "format": "json", "limit": 1, "accept-language": "ru"}
    headers = {"User-Agent": "JARVIS-Travel-Bot/1.0"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        return float(data[0]["lat"]), float(data[0]["lon"])
                else:
                    error_msg = get_api_error_message(response.status)
                    error(f"Ошибка при получении координат города {city}: {error_msg}")
    except Exception as e:
        error(f"Ошибка получения координат города через aiohttp: {e}")
    return None, None

async def get_attractions_osm(
    city: str,
    category: str | None = None,
    limit: int = 100
) -> list:

    lat, lon = await get_city_coords(city)
    if not lat or not lon:
        return []
    
    log(f"CITY={city}")
    log(f"CATEGORY={category}")
    
    bbox = f"{lat-0.1}, {lon-0.15}, {lat+0.1}, {lon+0.15}"
    
    query = f"""
    [out:json][timeout:15];
    (
      node["tourism"~"attraction|museum|viewpoint|gallery|theme_park"]({bbox});
      way["tourism"~"attraction|museum|viewpoint|gallery|theme_park"]({bbox});
      node["historic"~"monument|memorial|castle|ruins|church|cathedral|manor"]({bbox});
      way["historic"~"monument|memorial|castle|ruins|church|cathedral|manor"]({bbox});
    );
    out tags center;
    """
    
    headers = {
        "User-Agent": "JARVIS-Travel-Bot/1.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    type_map = {
        "museum": "Музей", "attraction": "Достопримечательность", "gallery": "Галерея",
        "monument": "Памятник", "memorial": "Мемориал", "castle": "Замок",
        "ruins": "Руины", "archaeological_site": "Археологический объект", "fort": "Форт",
        "manor": "Усадьба", "park": "Пак", "garden": "Сад", "nature_reserve": "Заповедник",
        "zoo": "Зоопарк", "aquarium": "Океанариум", "theme_park": "Парк аттракционов",
        "cinema": "Кинотеатр", "theatre": "Театр", "library": "Библиотека",
        "place_of_worship": "Храм", "cathedral": "Собор", "church": "Церковь",
        "civic": "Гражданское здание", "townhall": "Ратуша", "community_centre": "Центр культуры",
        "arts_centre": "Центр искусств", "viewpoint": "Смотровая площадка",
        "information": "Информационный центр", "artwork": "Арт-объект", "battlefield": "Поле битвы",
        "city_gate": "Городские ворота", "tower": "Башня", "wall": "Стена",
        "playground": "Детская площадка", "sports_centre": "Спортивный центр",
        "stadium": "Стадион", "water_park": "Аквапарк", "marina": "Пристань",
        "fitness_centre": "Фитнес-центр", "hotel": "Отель", "commercial": "Торговый центр",
        "public": "Общественное здание"
    }

    async with aiohttp.ClientSession() as session:
        for url in OVERPASS_URLS:
            try:
                log(f"Отправка асинхронного запроса Overpass для города {city} на сервер: {url}")
                payload = f"data={urllib.parse.quote(query)}"
                
                async with session.post(url, data=payload, headers=headers, timeout=20) as response:
                    if response.status == 200:
                        data = await response.json()
                        elements = data.get("elements", [])
                        attractions = []
                        seen = set()
                        
                        for elem in elements:
                            tags = elem.get("tags", {})
                            name = tags.get("name", "")
                            if not name:
                                continue
                                
                            lat_obj = elem.get("lat") or elem.get("center", {}).get("lat")
                            lon_obj = elem.get("lon") or elem.get("center", {}).get("lon")
                            if not lat_obj or not lon_obj:
                                continue
                                
                            key = (name, round(lat_obj, 4), round(lon_obj, 4))
                            if key in seen:
                                continue
                            seen.add(key)
                            
                            raw_id = elem.get("id")
                            if raw_id and str(raw_id).isdigit() and len(str(raw_id)) <= 15:
                                uid = str(raw_id)
                            else:
                                unique_key = f"{name}|{lat_obj}|{lon_obj}"
                                uid = hashlib.md5(unique_key.encode('utf-8')).hexdigest()[:12]
                            
                            obj_type = tags.get("tourism") or tags.get("historic") or "достопримечательность"
                            normalized_type = type_map.get(obj_type, obj_type.capitalize())
                            
                            address = ", ".join(filter(None, [
                                tags.get("addr:street"),
                                tags.get("addr:housenumber"),
                                tags.get("addr:city")
                            ])) or tags.get("addr:full") or ""
                            
                            opening_hours = tags.get("opening_hours", "")
                            phone = tags.get("phone", "")
                            
                            image_url = ""
                            img_tag = tags.get("image") or tags.get("wikimedia_commons")
                            if img_tag:
                                if img_tag.startswith("http"):
                                    image_url = img_tag
                                elif img_tag.startswith("File:") or img_tag.startswith("commons:"):
                                    image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{img_tag.replace('File:', '').replace('commons:', '').strip()}"
                                else:
                                    image_url = f"https://commons.wikimedia.org/w/index.php?title=Special:Search&limit=1&offset=0&profile=default&search={name.replace(' ', '+')}"
                            
                            if tags.get("wikipedia") or tags.get("wikidata"):
                                rating = 4.8
                            elif phone and opening_hours:
                                rating = 4.2
                            elif phone or opening_hours:
                                rating = 3.8
                            else:
                                rating = 3.5
                            
                            attractions.append({
                                "id": uid,  # Теперь запекается строгий и неизменяемый ID
                                "name": name,
                                "address": address,
                                "lat": lat_obj,
                                "lon": lon_obj,
                                "type": normalized_type,
                                "hours": opening_hours,
                                "phone": phone,
                                "image_url": image_url,
                                "rating": rating
                            })
                        
                        attractions.sort(key=lambda x: x['rating'], reverse=True)
                        log(f"✅ Получено {len(attractions)} достопримечательностей для города {city}")
                        return attractions[:limit]
                        
                    else:
                        error_msg = get_api_error_message(response.status)
                        error(f"Ошибка Overpass API {response.status} для города {city}: {error_msg}")
                        continue
                        
            except Exception as e:
                error(f"Ошибка или таймаут на сервере {url}: {e}. Смена зеркала...")
                continue

    error(f"❌ Ни одно из зеркал Overpass API не ответило вовремя для города {city}")
    return []