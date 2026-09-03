"""
Сервис получения фотографий конкретных объектов из Wikimedia Commons.

Логика:
1. Сначала ищем фотографии около координат объекта.
2. Затем ищем по названию объекта + городу.
3. Проверяем название файла, описание, категории и координаты.
4. Отбрасываем карты, схемы, гербы, флаги и прочий мусор.
5. Не подставляем случайную фотографию только потому, что она из Минска.
6. Подходящая фотография скачивается локально и сохраняется в WebP.
"""

import asyncio
import hashlib
import io
import re
from pathlib import Path

import aiohttp
from PIL import Image

from src.config import WIKIMEDIA_API_URL
from src.utils.utils import log, error


WIKIMEDIA_API = (
    WIKIMEDIA_API_URL
    or "https://commons.wikimedia.org/w/api.php"
)

MEDIA_ROOT = Path("media/places")

HEADERS = {
    "User-Agent": (
        "JARVIS-Travel-Bot/1.0 "
        "(travel bot; contact: kirwjb@gmail.com)"
    )
}


# ---------------------------------------------------------------------------
# Размеры локальных изображений
# ---------------------------------------------------------------------------

SIZES = {
    "thumb": (400, 300),
    "medium": (1200, 800),
}


# ---------------------------------------------------------------------------
# Беларусь — только быстрый bbox.
# Это НЕ используется как доказательство того, что фото относится
# к конкретному объекту.
# ---------------------------------------------------------------------------

BELARUS_BBOX = {
    "min_lat": 51.25,
    "max_lat": 56.17,
    "min_lon": 23.17,
    "max_lon": 32.77,
}


# ---------------------------------------------------------------------------
# Явно плохие типы изображений
# ---------------------------------------------------------------------------

BAD_EXTENSIONS = (
    ".svg",
    ".pdf",
    ".djvu",
    ".tiff",
    ".tif",
)

BAD_DESCRIPTION_WORDS = (
    "map of",
    "locator map",
    "location map",
    "map showing",
    "карта ",
    "карта:",
    "схема ",
    "схема:",
    "план ",
    "план:",
    "герб ",
    "герб:",
    "coat of arms",
    "flag of",
    "флаг ",
    "флаг:",
)


# ---------------------------------------------------------------------------
# Города и синонимы
# ---------------------------------------------------------------------------

CITY_SYNONYMS = {
    "минск": (
        "минск",
        "мінск",
        "minsk",
        "minsk",
    ),
    "брест": (
        "брест",
        "брэст",
        "brest",
    ),
    "гродно": (
        "гродно",
        "гродна",
        "grodno",
        "hrodna",
    ),
    "гомель": (
        "гомель",
        "homiel",
        "gomel",
    ),
    "витебск": (
        "витебск",
        "віцебск",
        "vitebsk",
    ),
    "могилев": (
        "могилев",
        "магілёў",
        "mogilev",
        "mogilyov",
    ),
    "полоцк": (
        "полоцк",
        "полацк",
        "polotsk",
    ),
    "пинск": (
        "пинск",
        "пінск",
        "pinsk",
    ),
    "борисов": (
        "борисов",
        "барысаў",
        "borisov",
        "barysaw",
    ),
    "несвиж": (
        "несвиж",
        "нясвіж",
        "nesvizh",
    ),
    "слуцк": (
        "слуцк",
        "слуцак",
        "slutsk",
    ),
}


# ---------------------------------------------------------------------------
# Типы объектов
# ---------------------------------------------------------------------------

TYPE_QUERY_WORDS = {
    "memorial": (
        "memorial памятник помнік "
        "monument мемориал мемарыял"
    ),
    "monument": (
        "monument памятник помнік "
        "мемориал мемарыял"
    ),
    "church": (
        "church church building "
        "церковь царква касцёл костёл храм собор"
    ),
    "castle": (
        "castle замок замак "
        "palace дворец палац"
    ),
    "museum": (
        "museum музей"
    ),
    "manor": (
        "manor усадьба сядзіба "
        "palace дворец палац"
    ),
    "ruins": (
        "ruins руины руіны"
    ),
    "park": (
        "park парк"
    ),
    "viewpoint": (
        "viewpoint панорама "
        "смотровая площадка"
    ),
    "gallery": (
        "gallery галерея"
    ),
    "theme_park": (
        "theme park парк аттракционов"
    ),
}


# ---------------------------------------------------------------------------
# Транслитерация.
#
# Нужна потому, что OSM может дать:
#
#   А.І. Лур'е
#
# а Wikimedia:
#
#   Lurie
#   A. I. Lurie
#   Лурье
#
# ---------------------------------------------------------------------------

TRANSLIT_TABLE = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "j",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",

        # Белорусские буквы
        "ў": "u",
        "і": "i",
        "ґ": "g",
    }
)


def _normalize_text(value: str) -> str:
    """
    Нормализация текста для поиска.

    Сохраняем и кириллическую форму, и возможность сравнивать
    через транслитерацию.
    """
    if not value:
        return ""

    value = str(value).lower()
    value = value.replace("file:", "")
    value = value.replace("&quot;", " ")
    value = value.replace("&#39;", "'")

    value = re.sub(
        r"[^a-zа-яёіўґ0-9\s]",
        " ",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _translit(value: str) -> str:
    """Простая транслитерация кириллицы в латиницу."""
    value = _normalize_text(value)

    if not value:
        return ""

    return value.translate(TRANSLIT_TABLE)


def _text_forms(value: str) -> set[str]:
    """
    Возвращает варианты строки для сравнения:
    - нормализованная кириллица;
    - транслитерация.
    """
    normalized = _normalize_text(value)

    if not normalized:
        return set()

    forms = {normalized}

    transliterated = _translit(normalized)
    if transliterated:
        forms.add(transliterated)

    return forms


# ---------------------------------------------------------------------------
# География
# ---------------------------------------------------------------------------

def is_in_belarus(lat: float, lon: float) -> bool:
    """Быстрая проверка координат по bbox Беларуси."""
    return (
        BELARUS_BBOX["min_lat"] <= lat <= BELARUS_BBOX["max_lat"]
        and BELARUS_BBOX["min_lon"] <= lon <= BELARUS_BBOX["max_lon"]
    )


def _distance_score(
    object_lat: float,
    object_lon: float,
    photo_lat: float | None,
    photo_lon: float | None,
) -> int:
    """
    Грубая оценка близости фотографии к объекту.

    Используем градусы, потому что для ранжирования этого достаточно.
    """
    if photo_lat is None or photo_lon is None:
        return 0

    try:
        distance = (
            (float(object_lat) - float(photo_lat)) ** 2
            + (float(object_lon) - float(photo_lon)) ** 2
        ) ** 0.5
    except (TypeError, ValueError):
        return 0

    if distance <= 0.001:
        return 120

    if distance <= 0.003:
        return 100

    if distance <= 0.01:
        return 70

    if distance <= 0.03:
        return 40

    if distance <= 0.08:
        return 20

    return 0


# ---------------------------------------------------------------------------
# Проверка изображения
# ---------------------------------------------------------------------------

def _is_valid_photo(info: dict) -> bool:
    """
    Отбрасываем технический мусор и слишком маленькие изображения.
    """
    url = (info.get("url") or "").lower()

    if not url:
        return False

    if url.endswith(BAD_EXTENSIONS):
        return False

    metadata = info.get("extmetadata", {})

    description = (
        metadata.get("ImageDescription", {}).get("value")
        or metadata.get("ObjectName", {}).get("value")
        or ""
    )

    description = str(description).lower()

    if any(word in description for word in BAD_DESCRIPTION_WORDS):
        return False

    width = info.get("width", 0) or 0
    height = info.get("height", 0) or 0

    try:
        width = int(width)
        height = int(height)
    except (TypeError, ValueError):
        return False

    if width < 600 or height < 400:
        return False

    return True


# ---------------------------------------------------------------------------
# Проверка категорий Wikimedia
# ---------------------------------------------------------------------------

async def _get_page_context(
    session: aiohttp.ClientSession,
    title: str,
) -> dict:
    """
    Получает категории и координаты конкретного файла.
    """
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
                log(
                    f"Wikimedia context HTTP {response.status}: "
                    f"{title}"
                )
                return {}

            return await response.json()

    except Exception as exc:
        error(
            f"Wikimedia context error '{title}': {exc}"
        )
        return {}


async def _is_belarus_related(
    session: aiohttp.ClientSession,
    title: str,
) -> tuple[bool, list[tuple[float, float]]]:
    """
    Проверяет, относится ли файл к Беларуси.

    Возвращает:
        (True/False, координаты файла)
    """
    data = await _get_page_context(session, title)

    pages = data.get("query", {}).get("pages", {})

    if not pages:
        return False, []

    coordinates: list[tuple[float, float]] = []

    for page in pages.values():

        # ---------------------------------------------------------------
        # Категории
        # ---------------------------------------------------------------

        categories = page.get("categories", []) or []

        for category in categories:
            category_title = (
                category.get("title") or ""
            ).lower()

            category_title = _normalize_text(category_title)

            for city_variants in CITY_SYNONYMS.values():
                if any(
                    _normalize_text(v) in category_title
                    for v in city_variants
                ):
                    return True, coordinates

            if (
                "belarus" in category_title
                or "беларус" in category_title
                or "белорус" in category_title
            ):
                return True, coordinates

        # ---------------------------------------------------------------
        # Геотеги файла
        # ---------------------------------------------------------------

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
# Поиск
# ---------------------------------------------------------------------------

async def get_wikimedia_photo(
    name: str,
    city: str,
    place_id: str,
    lat: float | None = None,
    lon: float | None = None,
    category: str | None = None,
) -> dict | None:
    """
    Главная функция поиска фотографии.

    Приоритет:

    1. Геопоиск около координат объекта.
    2. Поиск по названию + городу.
    3. Более свободные текстовые запросы.
    """

    name = (name or "").strip()
    city = (city or "").strip()
    category = (category or "").strip().lower()

    if not name:
        log("Wikimedia: пустое название объекта")
        return None

    log(
        f"Wikimedia START: "
        f"name='{name}' | city='{city}' | "
        f"category='{category}' | "
        f"lat={lat} | lon={lon}"
    )

    try:
        async with aiohttp.ClientSession(
            headers=HEADERS
        ) as session:

            type_words = TYPE_QUERY_WORDS.get(
                category,
                "",
            )

            # -----------------------------------------------------------
            # 1. СНАЧАЛА ГЕОПОИСК
            # -----------------------------------------------------------

            if lat is not None and lon is not None:
                log(
                    f"Wikimedia GEO SEARCH: "
                    f"{lat},{lon}"
                )

                photo = await _search_by_coordinates(
                    session=session,
                    name=name,
                    city=city,
                    lat=lat,
                    lon=lon,
                    place_id=place_id,
                    extra_words=type_words,
                )

                if photo:
                    log(
                        f"Wikimedia ACCEPT GEO: "
                        f"{name}"
                    )
                    return photo

            # -----------------------------------------------------------
            # 2. ТЕКСТОВЫЕ ЗАПРОСЫ
            # -----------------------------------------------------------

            raw_queries = [
                f'"{name}" "{city}" Belarus',
                f'"{name}" {city} Belarus',
                f'"{name}" {type_words} {city}',
                f'"{name}" Belarus',
                f"{name} {city} Belarus",
                f"{name} {city}",
            ]

            queries: list[str] = []

            for query in raw_queries:
                query = re.sub(
                    r"\s+",
                    " ",
                    query,
                ).strip()

                if query and query not in queries:
                    queries.append(query)

            for query in queries:
                log(
                    f"Wikimedia TEXT SEARCH: "
                    f"{query}"
                )

                photo = await _search_by_text(
                    session=session,
                    query=query,
                    name=name,
                    city=city,
                    place_id=place_id,
                    extra_words=type_words,
                    object_lat=lat,
                    object_lon=lon,
                )

                if photo:
                    log(
                        f"Wikimedia ACCEPT TEXT: "
                        f"{name}"
                    )
                    return photo

    except Exception as exc:
        error(
            f"Ошибка Wikimedia: {exc}"
        )

    log(
        f"Wikimedia FINAL: фото не найдено: "
        f"{name} | {city} | {place_id}"
    )

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
) -> dict | None:
    """Текстовый поиск изображений."""

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 20,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
    }

    try:
        async with session.get(
            WIKIMEDIA_API,
            params=params,
            timeout=20,
        ) as response:

            if response.status != 200:
                error(
                    f"Wikimedia search HTTP "
                    f"{response.status}: {query}"
                )
                return None

            data = await response.json()

    except Exception as exc:
        error(
            f"Ошибка Wikimedia search "
            f"'{query}': {exc}"
        )
        return None

    pages = data.get("query", {}).get("pages", {})

    log(
        f"Wikimedia RESULTS: "
        f"{len(pages)} | query='{query}'"
    )

    if not pages:
        return None

    candidates = []

    for page in pages.values():

        title = page.get("title", "")

        image_info = page.get("imageinfo", [])

        if not image_info:
            log(
                f"Wikimedia REJECT no-imageinfo: "
                f"{title}"
            )
            continue

        info = image_info[0]

        if not info.get("url"):
            log(
                f"Wikimedia REJECT no-url: "
                f"{title}"
            )
            continue

        if not _is_valid_photo(info):
            log(
                f"Wikimedia REJECT invalid: "
                f"{title}"
            )
            continue

        score = _match_score(
            title=title,
            name=name,
            city=city,
            extra_words=extra_words,
        )

        if score <= 0:
            log(
                f"Wikimedia REJECT score=0: "
                f"{title}"
            )
            continue

        candidates.append(
            (
                score,
                title,
                info,
            )
        )

        log(
            f"Wikimedia CANDIDATE: "
            f"score={score} | {title}"
        )

    if not candidates:
        log(
            f"Wikimedia NO CANDIDATES: "
            f"{query}"
        )
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # Проверяем максимум 8 лучших кандидатов.
    for score, title, info in candidates[:8]:

        # ---------------------------------------------------------------
        # Если название файла очень хорошо совпадает с объектом,
        # это сильный кандидат.
        # ---------------------------------------------------------------

        if score >= 100:
            log(
                f"Wikimedia ACCEPT STRONG: "
                f"score={score} | {title}"
            )

            photo = await _build_photo(
                session,
                info,
                place_id,
            )

            if photo:
                return photo

            log(
                f"Wikimedia DOWNLOAD FAILED: "
                f"{title}"
            )

        # ---------------------------------------------------------------
        # Для менее сильного совпадения нужна дополнительная проверка.
        # ---------------------------------------------------------------

        related, coordinates = await _is_belarus_related(
            session,
            title,
        )

        if not related:
            log(
                f"Wikimedia REJECT not-Belarus: "
                f"score={score} | {title}"
            )
            continue

        # Если у файла есть геотег и координаты объекта известны,
        # дополнительно оцениваем расстояние.
        geo_bonus = 0

        if (
            object_lat is not None
            and object_lon is not None
            and coordinates
        ):
            for photo_lat, photo_lon in coordinates:
                geo_bonus = max(
                    geo_bonus,
                    _distance_score(
                        object_lat,
                        object_lon,
                        photo_lat,
                        photo_lon,
                    ),
                )

        total_score = score + geo_bonus

        log(
            f"Wikimedia RELATED: "
            f"score={score} "
            f"geo_bonus={geo_bonus} "
            f"total={total_score} | "
            f"{title}"
        )

        # Не берём слабое совпадение только потому,
        # что картинка находится в Беларуси.
        if total_score < 45:
            log(
                f"Wikimedia REJECT weak: "
                f"total={total_score} | {title}"
            )
            continue

        photo = await _build_photo(
            session,
            info,
            place_id,
        )

        if photo:
            return photo

        log(
            f"Wikimedia DOWNLOAD FAILED: "
            f"{title}"
        )

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
) -> dict | None:
    """
    Ищет фотографии рядом с координатами объекта.

    Радиус сначала 100 м, затем 500 м.
    """

    if not is_in_belarus(lat, lon):
        log(
            f"Wikimedia GEO SKIP outside Belarus: "
            f"{lat},{lon}"
        )
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
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1200,
        }

        log(
            f"Wikimedia GEO QUERY: "
            f"radius={radius}m | "
            f"{name} | {lat},{lon}"
        )

        try:
            async with session.get(
                WIKIMEDIA_API,
                params=params,
                timeout=20,
            ) as response:

                if response.status != 200:
                    error(
                        f"Wikimedia geo HTTP "
                        f"{response.status}"
                    )
                    continue

                data = await response.json()

        except Exception as exc:
            error(
                f"Ошибка Wikimedia geosearch: "
                f"{exc}"
            )
            continue

        pages = data.get(
            "query",
            {},
        ).get(
            "pages",
            {},
        )

        log(
            f"Wikimedia GEO RESULTS: "
            f"{len(pages)} | radius={radius}"
        )

        if not pages:
            continue

        candidates = []

        for page in pages.values():

            title = page.get(
                "title",
                "",
            )

            image_info = page.get(
                "imageinfo",
                [],
            )

            if not image_info:
                log(
                    f"Wikimedia GEO REJECT no-imageinfo: "
                    f"{title}"
                )
                continue

            info = image_info[0]

            if not info.get("url"):
                log(
                    f"Wikimedia GEO REJECT no-url: "
                    f"{title}"
                )
                continue

            if not _is_valid_photo(info):
                log(
                    f"Wikimedia GEO REJECT invalid: "
                    f"{title}"
                )
                continue

            name_score = _match_score(
                title=title,
                name=name,
                city=city,
                extra_words=extra_words,
            )

            geo_score = 0

            # Geosearch уже говорит, что файл находится рядом,
            # поэтому даём существенный бонус.
            geo_score += 50

            # Очень близкие результаты получают ещё больше.
            if radius <= 100:
                geo_score += 40

            total_score = name_score + geo_score

            candidates.append(
                (
                    total_score,
                    name_score,
                    title,
                    info,
                )
            )

            log(
                f"Wikimedia GEO CANDIDATE: "
                f"total={total_score} "
                f"name={name_score} | "
                f"{title}"
            )

        if not candidates:
            continue

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        for (
            total_score,
            name_score,
            title,
            info,
        ) in candidates[:10]:

            # -----------------------------------------------------------
            # Очень важное правило:
            #
            # Геопоиск НЕ означает автоматически,
            # что это нужный объект.
            #
            # Но если имя объекта совпадает хотя бы частично,
            # результат очень сильный.
            # -----------------------------------------------------------

            if name_score >= 25:
                log(
                    f"Wikimedia GEO ACCEPT: "
                    f"total={total_score} "
                    f"name={name_score} | "
                    f"{title}"
                )

                photo = await _build_photo(
                    session,
                    info,
                    place_id,
                )

                if photo:
                    return photo

                log(
                    f"Wikimedia GEO DOWNLOAD FAILED: "
                    f"{title}"
                )

                continue

            # -----------------------------------------------------------
            # Если название вообще не совпало, проверяем файл
            # отдельно через категории/геотег.
            # -----------------------------------------------------------

            related, coordinates = await _is_belarus_related(
                session,
                title,
            )

            if not related:
                log(
                    f"Wikimedia GEO REJECT unrelated: "
                    f"{title}"
                )
                continue

            # Если файл находится прямо рядом с объектом,
            # но название не совпало, разрешаем только для очень
            # маленького радиуса.
            if radius > 100:
                log(
                    f"Wikimedia GEO REJECT weak-name: "
                    f"{title}"
                )
                continue

            log(
                f"Wikimedia GEO ACCEPT nearby: "
                f"{title}"
            )

            photo = await _build_photo(
                session,
                info,
                place_id,
            )

            if photo:
                return photo

        # Если нашли что-то в 100 м — не надо сразу
        # расширять поиск до 500 м.
        if radius == 100:
            continue

    return None


# ---------------------------------------------------------------------------
# Скоринг названия
# ---------------------------------------------------------------------------

def _match_score(
    title: str,
    name: str,
    city: str,
    extra_words: str = "",
) -> int:
    """
    Оценивает связь имени файла с объектом.

    Важно:
    высокий score означает сходство названий,
    но не гарантирует 100% идентичность.
    """

    title_forms = _text_forms(title)
    name_forms = _text_forms(name)

    if not title_forms or not name_forms:
        return 0

    score = 0

    # ---------------------------------------------------------------
    # Полное название
    # ---------------------------------------------------------------

    for name_form in name_forms:
        if not name_form:
            continue

        for title_form in title_forms:
            if name_form in title_form:
                score = max(score, 100)

    # ---------------------------------------------------------------
    # Существенные слова названия
    # ---------------------------------------------------------------

    name_normalized = _normalize_text(name)

    name_words = [
        word
        for word in name_normalized.split()
        if len(word) >= 3
    ]

    # Убираем слишком общие слова.
    stop_words = {
        "год",
        "года",
        "годдзе",
        "годов",
        "лет",
        "the",
        "and",
        "for",
        "in",
        "of",
        "на",
        "в",
        "из",
        "и",
        "імя",
        "имени",
    }

    name_words = [
        word
        for word in name_words
        if word not in stop_words
    ]

    if name_words:

        matched = 0

        for word in name_words:

            word_forms = _text_forms(word)

            found = False

            for word_form in word_forms:
                for title_form in title_forms:
                    if word_form in title_form:
                        found = True
                        break

                if found:
                    break

            if found:
                matched += 1

        ratio = matched / len(name_words)

        if ratio >= 0.75:
            score += 80
        elif ratio >= 0.50:
            score += 55
        elif ratio >= 0.30:
            score += 30
        elif matched:
            score += 15

    # ---------------------------------------------------------------
    # Город
    # ---------------------------------------------------------------

    city_variants = _city_variants(city)

    for variant in city_variants:

        variant_forms = _text_forms(variant)

        if any(
            any(
                form in title_form
                for title_form in title_forms
            )
            for form in variant_forms
        ):
            score += 30
            break

    # ---------------------------------------------------------------
    # Тип объекта
    # ---------------------------------------------------------------

    if extra_words:

        type_words = [
            word
            for word in _normalize_text(extra_words).split()
            if len(word) >= 4
        ]

        for word in type_words:

            word_forms = _text_forms(word)

            if any(
                any(
                    form in title_form
                    for title_form in title_forms
                )
                for form in word_forms
            ):
                score += 15
                break

    return score


# ---------------------------------------------------------------------------
# Варианты города
# ---------------------------------------------------------------------------

def _city_variants(city: str) -> list[str]:
    """Возвращает варианты написания города."""

    normalized = _normalize_text(city)

    if not normalized:
        return []

    variants = {
        normalized,
    }

    transliterated = _translit(normalized)

    if transliterated:
        variants.add(transliterated)

    for base, synonyms in CITY_SYNONYMS.items():

        normalized_synonyms = {
            _normalize_text(item)
            for item in synonyms
        }

        if (
            normalized == base
            or normalized in normalized_synonyms
        ):
            variants.add(
                _normalize_text(base)
            )

            for synonym in synonyms:
                variants.add(
                    _normalize_text(synonym)
                )

    return [
        variant
        for variant in variants
        if variant
    ]


# ---------------------------------------------------------------------------
# Скачивание и сохранение
# ---------------------------------------------------------------------------

async def _build_photo(
    session: aiohttp.ClientSession,
    info: dict,
    place_id: str,
) -> dict | None:
    """
    Скачивает изображение и создаёт thumb/medium WebP.
    """

    original_url = info.get("url")

    if not original_url:
        return None

    data = await _download_bytes(
        session,
        original_url,
    )

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
        error(
            f"Ошибка обработки изображения: "
            f"{exc}"
        )
        return None

    if not urls:
        return None

    metadata = info.get(
        "extmetadata",
        {},
    )

    return {
        "source": "wikimedia",
        "original_url": original_url,
        "local_url_thumb": urls.get("thumb"),
        "local_url_medium": urls.get("medium"),
        "author": _metadata_value(
            metadata,
            "Artist",
        ),
        "license": (
            _metadata_value(
                metadata,
                "LicenseShortName",
            )
            or _metadata_value(
                metadata,
                "UsageTerms",
            )
        ),
    }


async def _download_bytes(
    session: aiohttp.ClientSession,
    original_url: str,
) -> bytes | None:
    """Скачивает изображение по URL."""

    try:
        async with session.get(
            original_url,
            timeout=30,
        ) as response:

            if response.status != 200:
                error(
                    f"Ошибка загрузки фото: "
                    f"HTTP {response.status} | "
                    f"{original_url}"
                )
                return None

            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
                .lower()
            )

            # Некоторые CDN Wikimedia могут вернуть
            # application/octet-stream.
            #
            # Поэтому НЕ отбрасываем файл только по Content-Type.
            if (
                content_type
                and not content_type.startswith("image/")
                and "octet-stream" not in content_type
            ):
                log(
                    f"Wikimedia DOWNLOAD WARNING: "
                    f"Content-Type={content_type} | "
                    f"{original_url}"
                )

            data = await response.read()

            if not data:
                error(
                    f"Пустой ответ при загрузке фото: "
                    f"{original_url}"
                )
                return None

            return data

    except asyncio.TimeoutError:
        error(
            f"Таймаут загрузки фотографии: "
            f"{original_url}"
        )
        return None

    except Exception as exc:
        error(
            f"Ошибка загрузки фотографии: "
            f"{exc}"
        )
        return None


def _process_and_save_image(
    data: bytes,
    place_id: str,
    original_url: str,
) -> dict[str, str]:
    """
    Синхронная обработка изображения.

    Создаёт:
        thumb 400x300
        medium 1200x800

    Фактическое соотношение сторон сохраняется.
    """

    directory = (
        MEDIA_ROOT
        / place_id
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    base_hash = hashlib.sha256(
        original_url.encode("utf-8")
    ).hexdigest()[:16]

    try:
        image = Image.open(
            io.BytesIO(data)
        )

        # Проверяем, что это действительно изображение.
        image.verify()

        image = Image.open(
            io.BytesIO(data)
        ).convert("RGB")

    except Exception as exc:
        error(
            f"Не удалось открыть изображение: "
            f"{exc}"
        )
        return {}

    urls: dict[str, str] = {}

    for size_name, dimensions in SIZES.items():

        copy = image.copy()

        copy.thumbnail(
            dimensions,
            Image.Resampling.LANCZOS,
        )

        filename = (
            f"{base_hash}_{size_name}.webp"
        )

        filepath = (
            directory
            / filename
        )

        try:
            if not filepath.exists():
                copy.save(
                    filepath,
                    "WEBP",
                    quality=80,
                    optimize=True,
                )

        except Exception as exc:
            error(
                f"Не удалось сохранить "
                f"{filepath}: {exc}"
            )
            continue

        urls[size_name] = (
            f"/media/places/"
            f"{place_id}/"
            f"{filename}"
        )

    return urls


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def _metadata_value(
    metadata: dict,
    key: str,
) -> str | None:
    """Достаёт значение из extmetadata Wikimedia."""

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

