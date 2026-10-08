"""
Сервис получения фотографий конкретных объектов из Wikimedia Commons.

Логика:
1. Если доступен идентификатор OSM (osm:node:..., osm:way:..., osm:relation:...),
   разрешаем теги OSM и свойство P18 (image) / P373 (категория) из Wikidata.
2. Проверяем категории Wikimedia Commons (напрямую или через поиск категорий).
3. Геопоиск около координат объекта (в пределах Беларуси).
4. Каскадный поиск по очищенным нормализованным запросам (без инициалов, кавычек и мусорных слов).
5. Мягкая валидация: не отбрасывает экспонаты, картины или нелатинские имена,
   а переводит их во вторичный fallback (secondary candidates), чтобы не терять визуал.
6. Подходящая фотография скачивается локально и сохраняется в WebP (thumb/medium).
"""

import asyncio
import hashlib
import io
import re
import urllib.parse
from pathlib import Path

import aiohttp
from PIL import Image

from src.config import WIKIMEDIA_API_URL
from src.utils.utils import log, error
from src.utils.wiki_filters import (
    TYPE_QUERY_WORDS,
    city_variants,
    distance_score,
    generate_cascading_queries,
    generate_category_search_queries,
    is_in_belarus,
    is_secondary_visual,
    is_valid_photo,
    match_score,
    normalize_text,
    text_forms,
    translit,
)

WIKIMEDIA_API = (
    WIKIMEDIA_API_URL
    or "https://commons.wikimedia.org/w/api.php"
)

MEDIA_ROOT = Path("media/places")

HEADERS = {
    "User-Agent": (
        "JARVIS-Travel-Bot/1.0 "
        "(travel bot; contact: kirwjb@gmail.com)"
    ),
    "ngrok-skip-browser-warning": "true",
}

SIZES = {
    "thumb": (400, 300),
    "medium": (1200, 800),
}


# ---------------------------------------------------------------------------
# Парсинг и разрешение через OSM и Wikidata
# ---------------------------------------------------------------------------

def _parse_osm_id(place_id: str) -> tuple[str | None, int | None]:
    """Извлекает тип и числовой ID OSM из place_id."""
    if not place_id:
        return None, None
    m = re.match(r"(?:osm:)?(node|way|relation)[:/]?(\d+)", str(place_id), re.IGNORECASE)
    if m:
        return m.group(1).lower(), int(m.group(2))
    return None, None


async def _fetch_osm_tags(session: aiohttp.ClientSession, osm_type: str, osm_id: int) -> dict:
    """Получает теги OSM элемента через API OpenStreetMap с fallback на Overpass."""
    osm_url = f"https://api.openstreetmap.org/api/0.6/{osm_type}/{osm_id}.json"
    try:
        async with session.get(osm_url, timeout=6) as response:
            if response.status == 200:
                data = await response.json()
                elements = data.get("elements", [])
                if elements and "tags" in elements[0]:
                    return elements[0]["tags"]
    except Exception as exc:
        log(f"OSM API fetch failed for {osm_type}:{osm_id}: {exc}")

    # Fallback на Overpass
    overpass_urls = [
        "https://overpass-api.de/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    query = f"[out:json][timeout:10];{osm_type}({osm_id});out tags;"
    for op_url in overpass_urls:
        try:
            async with session.post(op_url, data={"data": query}, timeout=8) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    elements = data.get("elements", [])
                    if elements and "tags" in elements[0]:
                        return elements[0]["tags"]
        except Exception:
            continue
    return {}


async def _get_photo_by_title(
    session: aiohttp.ClientSession,
    title: str,
    place_id: str,
) -> dict | None:
    """Запрашивает конкретный файл Wikimedia Commons по точному имени."""
    if not title.startswith("File:") and not title.startswith("file:"):
        title = f"File:{title}"

    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1200,
    }
    try:
        async with session.get(WIKIMEDIA_API, params=params, timeout=15) as response:
            if response.status != 200:
                return None
            data = await response.json()
    except Exception as exc:
        error(f"Ошибка получения файла '{title}': {exc}")
        return None

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        image_info = page.get("imageinfo", [])
        if not image_info:
            continue
        info = image_info[0]
        if not is_valid_photo(info, title=title):
            log(f"Wikimedia REJECT invalid: {title}")
            continue
        photo = await _build_photo(session, info, place_id)
        if photo:
            return photo
    return None


async def _resolve_via_osm_and_wikidata(
    session: aiohttp.ClientSession,
    place_id: str,
    name: str,
    city: str,
) -> tuple[dict | None, dict, str | None]:
    """Разрешает фото или теги через OSM и свойство P18 (image) / P373 (категория) Wikidata.

    Возвращает:
        (photo_or_none, enriched_tags, category_or_none)
    """
    osm_type, osm_id = _parse_osm_id(place_id)
    if not osm_type or not osm_id:
        return None, {}, None

    tags = await _fetch_osm_tags(session, osm_type, osm_id)
    if not tags:
        return None, {}, None

    log(
        f"OSM tags for {place_id}: wikidata={tags.get('wikidata')}, "
        f"image={tags.get('image')}, commons={tags.get('wikimedia_commons')}"
    )

    # 1. Прямой тег 'image' на объекте OSM
    osm_image = tags.get("image")
    if osm_image:
        clean_img = osm_image.split("/")[-1].replace("File:", "").replace("file:", "")
        clean_img = urllib.parse.unquote(clean_img).strip()
        if clean_img:
            photo = await _get_photo_by_title(session, f"File:{clean_img}", place_id)
            if photo:
                log(f"Wikimedia ACCEPT from OSM 'image' tag: {clean_img}")
                return photo, tags, None

    # 2. Прямой тег 'wikimedia_commons' на объекте OSM
    found_category = None
    osm_commons = tags.get("wikimedia_commons")
    if osm_commons:
        clean_commons = urllib.parse.unquote(osm_commons.strip())
        if clean_commons.lower().startswith("file:"):
            photo = await _get_photo_by_title(session, clean_commons, place_id)
            if photo:
                log(f"Wikimedia ACCEPT from OSM 'wikimedia_commons' tag: {clean_commons}")
                return photo, tags, None
        elif clean_commons.lower().startswith("category:"):
            found_category = clean_commons

    # 3. Wikidata Q-ID -> свойство P18 (image) и P373 (Commons category)
    wikidata_id = tags.get("wikidata")
    if wikidata_id and re.match(r"^Q\d+$", wikidata_id.strip()):
        wikidata_id = wikidata_id.strip()
        w_url = (
            f"https://www.wikidata.org/w/api.php?action=wbgetentities"
            f"&ids={wikidata_id}&props=claims|labels&format=json"
        )
        try:
            async with session.get(w_url, timeout=10) as response:
                if response.status == 200:
                    w_data = await response.json()
                    entity = w_data.get("entities", {}).get(wikidata_id, {})
                    claims = entity.get("claims", {})

                    # P18 (image)
                    p18_claims = claims.get("P18", [])
                    for stmt in p18_claims:
                        p18_file = stmt.get("mainsnak", {}).get("datavalue", {}).get("value")
                        if p18_file:
                            photo = await _get_photo_by_title(session, f"File:{p18_file}", place_id)
                            if photo:
                                log(f"Wikimedia ACCEPT Wikidata P18 image: {p18_file} for {wikidata_id}")
                                return photo, tags, found_category

                    # P373 (commons category)
                    p373_claims = claims.get("P373", [])
                    for stmt in p373_claims:
                        p373_cat = stmt.get("mainsnak", {}).get("datavalue", {}).get("value")
                        if p373_cat:
                            found_category = f"Category:{p373_cat}"
                            break

        except Exception as exc:
            error(f"Wikidata resolution error for {wikidata_id}: {exc}")

    return None, tags, found_category


# ---------------------------------------------------------------------------
# Поиск по категориям Wikimedia Commons
# ---------------------------------------------------------------------------

async def _search_category_members(
    session: aiohttp.ClientSession,
    category_title: str,
    name: str,
    city: str,
    place_id: str,
    fallback_collector: list | None = None,
) -> dict | None:
    """Запрашивает файлы из указанной категории Wikimedia Commons."""
    if not category_title.startswith("Category:") and not category_title.startswith("category:"):
        category_title = f"Category:{category_title}"

    params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": category_title,
        "gcmnamespace": 6,
        "gcmlimit": 25,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1200,
    }
    try:
        async with session.get(WIKIMEDIA_API, params=params, timeout=15) as response:
            if response.status != 200:
                return None
            data = await response.json()
    except Exception as exc:
        error(f"Ошибка загрузки категории '{category_title}': {exc}")
        return None

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

    primary_candidates = []
    secondary_candidates = []

    for page in pages.values():
        title = page.get("title", "")
        image_info = page.get("imageinfo", [])
        if not image_info:
            continue
        info = image_info[0]
        if not is_valid_photo(info, title=title):
            log(f"Wikimedia REJECT invalid: {title}")
            continue

        score = match_score(
            title=title,
            name=name,
            city=city,
            metadata=info.get("extmetadata"),
        )
        effective_score = max(score, 50)

        if is_secondary_visual(info, title=title):
            log(f"Wikimedia CATEGORY CANDIDATE fallback: {title}")
            secondary_candidates.append((effective_score, title, info))
            if fallback_collector is not None:
                fallback_collector.append((effective_score, title, info))
        else:
            log(f"Wikimedia CATEGORY CANDIDATE primary: {title}")
            primary_candidates.append((effective_score, title, info))

    primary_candidates.sort(key=lambda x: x[0], reverse=True)
    for score, title, info in primary_candidates:
        photo = await _build_photo(session, info, place_id)
        if photo:
            log(f"Wikimedia ACCEPT CATEGORY primary: score={score} | {title}")
            return photo

    secondary_candidates.sort(key=lambda x: x[0], reverse=True)
    for score, title, info in secondary_candidates:
        photo = await _build_photo(session, info, place_id)
        if photo:
            log(f"Wikimedia ACCEPT CATEGORY fallback: score={score} | {title}")
            return photo

    return None


async def _search_categories_by_text(
    session: aiohttp.ClientSession,
    query: str,
) -> list[str]:
    """Ищет релевантные категории Commons в namespace 14."""
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srnamespace": 14,
        "srlimit": 5,
    }
    try:
        async with session.get(WIKIMEDIA_API, params=params, timeout=10) as response:
            if response.status != 200:
                return []
            data = await response.json()
            search_items = data.get("query", {}).get("search", [])
            return [item["title"] for item in search_items if item.get("title")]
    except Exception as exc:
        error(f"Ошибка поиска категорий для '{query}': {exc}")
        return []


# ---------------------------------------------------------------------------
# Проверка категорий и геотегов файла
# ---------------------------------------------------------------------------

async def _get_page_context(
    session: aiohttp.ClientSession,
    title: str,
) -> dict:
    """Получает категории и координаты конкретного файла."""
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "categories|coordinates",
        "cllimit": 100,
        "colimit": 10,
    }

    try:
        async with session.get(
            WIKIMEDIA_API,
            params=params,
            timeout=10,
        ) as response:
            if response.status != 200:
                log(f"Wikimedia context HTTP {response.status}: {title}")
                return {}
            return await response.json()

    except Exception as exc:
        error(f"Wikimedia context error '{title}': {exc}")
        return {}


async def _is_belarus_related(
    session: aiohttp.ClientSession,
    title: str,
) -> tuple[bool, list[tuple[float, float]]]:
    """Проверяет, относится ли файл к Беларуси."""
    data = await _get_page_context(session, title)
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return False, []

    coordinates: list[tuple[float, float]] = []

    for page in pages.values():
        categories = page.get("categories", []) or []
        for category in categories:
            category_title = normalize_text(category.get("title") or "")
            for c_variants in city_variants(""):
                if any(normalize_text(v) in category_title for v in c_variants):
                    return True, coordinates

            if (
                "belarus" in category_title
                or "беларус" in category_title
                or "белорус" in category_title
                or "брэсцк" in category_title
                or "магілёў" in category_title
                or "мінск" in category_title
            ):
                return True, coordinates

        for coord in page.get("coordinates", []) or []:
            lat = coord.get("lat")
            lon = coord.get("lon")
            if lat is None or lon is None:
                continue
            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                continue

            coordinates.append((lat, lon))
            if is_in_belarus(lat, lon):
                return True, coordinates

    return False, coordinates


# ---------------------------------------------------------------------------
# Главная функция поиска
# ---------------------------------------------------------------------------

async def get_wikimedia_photo(
    name: str,
    city: str,
    place_id: str,
    lat: float | None = None,
    lon: float | None = None,
    category: str | None = None,
) -> dict | None:
    """Главная функция поиска фотографии.

    Приоритет:
    1. Проверка OSM тегов и свойства P18 (image) / P373 (категория) из Wikidata.
    2. Поиск по известной категории объекта.
    3. Геопоиск около координат объекта (в Беларуси).
    4. Каскадный поиск по очищенным нормализованным запросам (без мусора и инициалов).
    5. Поиск по релевантным категориям Wikimedia.
    6. Вторичный fallback (экспонаты, картины, интерьеры), если фасад не найден.
    """
    name = (name or "").strip()
    city = (city or "").strip()
    category = (category or "").strip().lower()

    if not name:
        log("Wikimedia: пустое название объекта")
        return None

    log(
        f"Wikimedia START: name='{name}' | city='{city}' | "
        f"place_id='{place_id}' | category='{category}' | lat={lat} | lon={lon}"
    )

    fallback_candidates: list[tuple[int, str, dict]] = []

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            type_words = TYPE_QUERY_WORDS.get(category, "")

            # -----------------------------------------------------------
            # 1. OSM ТЕГИ И WIKIDATA P18 (IMAGE)
            # -----------------------------------------------------------
            osm_photo, osm_tags, osm_category = await _resolve_via_osm_and_wikidata(
                session=session,
                place_id=place_id,
                name=name,
                city=city,
            )
            if osm_photo:
                log(f"Wikimedia ACCEPT OSM/WIKIDATA: {name}")
                return osm_photo

            # -----------------------------------------------------------
            # 2. ПОИСК ПО ИЗВЕСТНОЙ КАТЕГОРИИ (ИЗ WIKIDATA / OSM)
            # -----------------------------------------------------------
            if osm_category:
                log(f"Wikimedia SEARCH KNOWN CATEGORY: {osm_category}")
                photo = await _search_category_members(
                    session=session,
                    category_title=osm_category,
                    name=name,
                    city=city,
                    place_id=place_id,
                    fallback_collector=fallback_candidates,
                )
                if photo:
                    log(f"Wikimedia ACCEPT KNOWN CATEGORY: {osm_category}")
                    return photo

            # -----------------------------------------------------------
            # 3. ГЕОПОИСК ОКОЛО КООРДИНАТ
            # -----------------------------------------------------------
            if lat is not None and lon is not None:
                log(f"Wikimedia GEO SEARCH: {lat},{lon}")
                photo = await _search_by_coordinates(
                    session=session,
                    name=name,
                    city=city,
                    lat=lat,
                    lon=lon,
                    place_id=place_id,
                    extra_words=type_words,
                    fallback_collector=fallback_candidates,
                )
                if photo:
                    log(f"Wikimedia ACCEPT GEO: {name}")
                    return photo

            # -----------------------------------------------------------
            # 4. КАСКАДНЫЕ ТЕКСТОВЫЕ ЗАПРОСЫ
            # -----------------------------------------------------------
            queries = generate_cascading_queries(
                name=name,
                city=city,
                category=category,
                osm_tags=osm_tags,
            )
            log(f"Wikimedia CASCADING QUERIES ({len(queries)}): {queries[:4]}")

            for query in queries:
                log(f"Wikimedia TEXT SEARCH: '{query}'")
                photo = await _search_by_text(
                    session=session,
                    query=query,
                    name=name,
                    city=city,
                    place_id=place_id,
                    extra_words=type_words,
                    object_lat=lat,
                    object_lon=lon,
                    fallback_collector=fallback_candidates,
                )
                if photo:
                    log(f"Wikimedia ACCEPT TEXT: '{query}' -> {name}")
                    return photo

            # -----------------------------------------------------------
            # 5. ПОИСК КАТЕГОРИЙ WIKIMEDIA COMMONS ПО ОЧИЩЕННЫМ ТЕРМИНАМ
            # -----------------------------------------------------------
            cat_queries = generate_category_search_queries(
                name=name,
                city=city,
                category=category,
                osm_tags=osm_tags,
            )
            for cq in cat_queries[:3]:
                found_cats = await _search_categories_by_text(session, cq)
                for fc in found_cats[:2]:
                    log(f"Wikimedia CATEGORY SEARCH FALLBACK: '{fc}' for query '{cq}'")
                    photo = await _search_category_members(
                        session=session,
                        category_title=fc,
                        name=name,
                        city=city,
                        place_id=place_id,
                        fallback_collector=fallback_candidates,
                    )
                    if photo:
                        log(f"Wikimedia ACCEPT CATEGORY FALLBACK: '{fc}'")
                        return photo

            # -----------------------------------------------------------
            # 6. ВТОРИЧНЫЙ FALLBACK (КАРТИНЫ, ЭКСПОНАТЫ, ИНТЕРЬЕРЫ)
            # -----------------------------------------------------------
            if fallback_candidates:
                log(f"Wikimedia EVALUATE FALLBACK CANDIDATES: {len(fallback_candidates)} items")
                fallback_candidates.sort(key=lambda x: x[0], reverse=True)
                for score, title, info in fallback_candidates[:6]:
                    related, _ = await _is_belarus_related(session, title)
                    if not related and score < 60:
                        log(f"Wikimedia REJECT fallback not-Belarus: score={score} | {title}")
                        continue

                    photo = await _build_photo(session, info, place_id)
                    if photo:
                        log(f"Wikimedia ACCEPT FALLBACK (exhibit/artwork): score={score} | {title}")
                        return photo

    except Exception as exc:
        error(f"Ошибка Wikimedia pipeline: {exc}")

    log(f"Wikimedia FINAL: фото не найдено: {name} | {city} | {place_id}")
    return None


# ---------------------------------------------------------------------------
# Текстовый поиск Wikimedia
# ---------------------------------------------------------------------------

async def _search_by_text(
    session: aiohttp.ClientSession,
    query: str,
    name: str,
    city: str,
    place_id: str,
    extra_words: str = "",
    object_lat: float | None = None,
    object_lon: float | None = None,
    fallback_collector: list | None = None,
) -> dict | None:
    """Текстовый поиск изображений с разделением на первичные и fallback-кандидаты."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 20,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1200,
    }

    try:
        async with session.get(
            WIKIMEDIA_API,
            params=params,
            timeout=20,
        ) as response:
            if response.status != 200:
                error(f"Wikimedia search HTTP {response.status}: {query}")
                return None
            data = await response.json()

    except Exception as exc:
        error(f"Ошибка Wikimedia search '{query}': {exc}")
        return None

    pages = data.get("query", {}).get("pages", {})
    log(f"Wikimedia RESULTS: {len(pages)} | query='{query}'")

    if not pages:
        return None

    candidates: list[tuple[int, str, dict]] = []

    for page in pages.values():
        title = page.get("title", "")
        image_info = page.get("imageinfo", [])

        if not image_info:
            log(f"Wikimedia REJECT no-imageinfo: {title}")
            continue

        info = image_info[0]

        if not info.get("url"):
            log(f"Wikimedia REJECT no-url: {title}")
            continue

        if not is_valid_photo(info, title=title):
            log(f"Wikimedia REJECT invalid: {title}")
            continue

        score = match_score(
            title=title,
            name=name,
            city=city,
            extra_words=extra_words,
            metadata=info.get("extmetadata"),
        )

        if score <= 0:
            log(f"Wikimedia REJECT score=0: {title}")
            continue

        # Вторичные визуалы (картины, экспонаты, интерьеры) сохраняем в fallback
        if is_secondary_visual(info, title=title):
            log(f"Wikimedia CANDIDATE fallback (exhibit/artwork): score={score} | {title}")
            if fallback_collector is not None:
                fallback_collector.append((score, title, info))
            continue

        candidates.append((score, title, info))
        log(f"Wikimedia CANDIDATE primary: score={score} | {title}")

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)

    for score, title, info in candidates[:8]:
        if score >= 100:
            log(f"Wikimedia ACCEPT STRONG: score={score} | {title}")
            photo = await _build_photo(session, info, place_id)
            if photo:
                return photo
            log(f"Wikimedia DOWNLOAD FAILED: {title}")

        related, coordinates = await _is_belarus_related(session, title)
        if not related:
            log(f"Wikimedia REJECT not-Belarus: score={score} | {title}")
            continue

        geo_bonus = 0
        if object_lat is not None and object_lon is not None and coordinates:
            for photo_lat, photo_lon in coordinates:
                geo_bonus = max(
                    geo_bonus,
                    distance_score(object_lat, object_lon, photo_lat, photo_lon),
                )

        total_score = score + geo_bonus
        log(f"Wikimedia RELATED: score={score} geo_bonus={geo_bonus} total={total_score} | {title}")

        if total_score < 45:
            log(f"Wikimedia REJECT weak: total={total_score} | {title}")
            continue

        photo = await _build_photo(session, info, place_id)
        if photo:
            return photo

        log(f"Wikimedia DOWNLOAD FAILED: {title}")

    return None


# ---------------------------------------------------------------------------
# Геопоиск
# ---------------------------------------------------------------------------

async def _search_by_coordinates(
    session: aiohttp.ClientSession,
    name: str,
    city: str,
    lat: float,
    lon: float,
    place_id: str,
    extra_words: str = "",
    fallback_collector: list | None = None,
) -> dict | None:
    """Ищет фотографии рядом с координатами объекта."""
    if not is_in_belarus(lat, lon):
        log(f"Wikimedia GEO SKIP outside Belarus: {lat},{lon}")
        return None

    for radius in (100, 500):
        params = {
            "action": "query",
            "format": "json",
            "generator": "geosearch",
            "ggsprimary": "all",
            "ggsnamespace": 6,
            "ggscoord": f"{lat}|{lon}",
            "ggsradius": radius,
            "ggslimit": 30,
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": 1200,
        }

        log(f"Wikimedia GEO QUERY: radius={radius}m | {name} | {lat},{lon}")

        try:
            async with session.get(WIKIMEDIA_API, params=params, timeout=20) as response:
                if response.status != 200:
                    error(f"Wikimedia geo HTTP {response.status}")
                    continue
                data = await response.json()
        except Exception as exc:
            error(f"Ошибка Wikimedia geosearch: {exc}")
            continue

        pages = data.get("query", {}).get("pages", {})
        log(f"Wikimedia GEO RESULTS: {len(pages)} | radius={radius}")

        if not pages:
            continue

        candidates = []

        for page in pages.values():
            title = page.get("title", "")
            image_info = page.get("imageinfo", [])
            if not image_info:
                log(f"Wikimedia GEO REJECT no-imageinfo: {title}")
                continue

            info = image_info[0]
            if not info.get("url"):
                log(f"Wikimedia GEO REJECT no-url: {title}")
                continue

            if not is_valid_photo(info, title=title):
                log(f"Wikimedia GEO REJECT invalid: {title}")
                continue

            name_score = match_score(
                title=title,
                name=name,
                city=city,
                extra_words=extra_words,
                metadata=info.get("extmetadata"),
            )

            geo_score = 50
            if radius <= 100:
                geo_score += 40

            total_score = name_score + geo_score

            if is_secondary_visual(info, title=title):
                if fallback_collector is not None:
                    fallback_collector.append((total_score, title, info))
                continue

            candidates.append((total_score, name_score, title, info))
            log(f"Wikimedia GEO CANDIDATE: total={total_score} name={name_score} | {title}")

        if not candidates:
            continue

        candidates.sort(key=lambda item: item[0], reverse=True)

        for total_score, name_score, title, info in candidates[:10]:
            if name_score >= 25:
                log(f"Wikimedia GEO ACCEPT: total={total_score} name={name_score} | {title}")
                photo = await _build_photo(session, info, place_id)
                if photo:
                    return photo
                log(f"Wikimedia GEO DOWNLOAD FAILED: {title}")
                continue

            related, _ = await _is_belarus_related(session, title)
            if not related:
                log(f"Wikimedia GEO REJECT unrelated: {title}")
                continue

            if radius > 100:
                log(f"Wikimedia GEO REJECT weak-name: {title}")
                continue

            log(f"Wikimedia GEO ACCEPT nearby: {title}")
            photo = await _build_photo(session, info, place_id)
            if photo:
                return photo

        if radius == 100:
            continue

    return None


# ---------------------------------------------------------------------------
# Скачивание и сохранение
# ---------------------------------------------------------------------------

async def _build_photo(
    session: aiohttp.ClientSession,
    info: dict,
    place_id: str,
) -> dict | None:
    """Скачивает изображение и создаёт thumb/medium WebP."""
    original_url = info.get("url")
    download_url = info.get("thumburl") or original_url
    if not download_url:
        return None

    data = await _download_bytes(session, download_url)
    if not data and download_url != original_url and original_url:
        data = await _download_bytes(session, original_url)

    if not data:
        return None

    try:
        urls = await asyncio.to_thread(
            _process_and_save_image,
            data,
            place_id,
            original_url,
        )
    except Exception as exc:
        error(f"Ошибка обработки изображения: {exc}")
        return None

    if not urls:
        return None

    metadata = info.get("extmetadata", {})

    return {
        "source": "wikimedia",
        "original_url": original_url,
        "local_url_thumb": urls.get("thumb"),
        "local_url_medium": urls.get("medium"),
        "author": _metadata_value(metadata, "Artist"),
        "license": (
            _metadata_value(metadata, "LicenseShortName")
            or _metadata_value(metadata, "UsageTerms")
        ),
    }


async def _download_bytes(
    session: aiohttp.ClientSession,
    original_url: str,
) -> bytes | None:
    """Скачивает изображение по URL."""
    try:
        async with session.get(original_url, timeout=30) as response:
            if response.status != 200:
                error(f"Ошибка загрузки фото: HTTP {response.status} | {original_url}")
                return None

            content_type = response.headers.get("Content-Type", "").lower()
            if (
                content_type
                and not content_type.startswith("image/")
                and "octet-stream" not in content_type
            ):
                log(f"Wikimedia DOWNLOAD WARNING: Content-Type={content_type} | {original_url}")

            data = await response.read()
            if not data:
                error(f"Пустой ответ при загрузке фото: {original_url}")
                return None
            return data

    except asyncio.TimeoutError:
        error(f"Таймаут загрузки фотографии: {original_url}")
        return None
    except Exception as exc:
        error(f"Ошибка загрузки фотографии: {exc}")
        return None


def _process_and_save_image(
    data: bytes,
    place_id: str,
    original_url: str,
) -> dict[str, str]:
    """Синхронная обработка изображения в WebP (thumb и medium)."""
    clean_pid = re.sub(r"[^\w\-]", "_", place_id)
    directory = MEDIA_ROOT / clean_pid
    directory.mkdir(parents=True, exist_ok=True)

    base_hash = hashlib.sha256(original_url.encode("utf-8")).hexdigest()[:16]

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        image = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        error(f"Не удалось открыть изображение: {exc}")
        return {}

    urls: dict[str, str] = {}

    for size_name, dimensions in SIZES.items():
        copy = image.copy()
        copy.thumbnail(dimensions, Image.Resampling.LANCZOS)
        filename = f"{base_hash}_{size_name}.webp"
        filepath = directory / filename

        try:
            if not filepath.exists():
                copy.save(filepath, "WEBP", quality=80, optimize=True)
        except Exception as exc:
            error(f"Не удалось сохранить {filepath}: {exc}")
            continue

        urls[size_name] = f"/media/places/{clean_pid}/{filename}"

    return urls


def _metadata_value(metadata: dict, key: str) -> str | None:
    """Извлекает значение из extmetadata Wikimedia."""
    value = metadata.get(key)
    if not value:
        return None
    if isinstance(value, dict):
        result = value.get("value")
    else:
        result = value
    if result is None:
        return None
    result = str(result).strip()
    return result or None
