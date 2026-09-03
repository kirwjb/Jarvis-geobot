import hashlib
import re
from pathlib import Path

import aiohttp

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


async def get_wikimedia_photo(
    name: str,
    city: str,
    place_id: str,
    lat: float | None = None,
    lon: float | None = None,
) -> dict | None:
    """
    Ищет фотографию конкретного объекта в Wikimedia Commons.

    Порядок:
    1. точное/почти точное совпадение названия;
    2. название + город;
    3. поиск изображений рядом с координатами объекта.

    ВАЖНО:
    поиск только по городу НЕ используется. Поиск по городу может вернуть фотографии, которые не имеют отношения к объекту.
    ЗАМЕТКА: В Wikimedia Commons нет строгой привязки к географическим объектам, поэтому поиск по координатам может вернуть фотографии, которые не имеют отношения к объекту.
    стоит учитывать, что Wikimedia Commons - это в первую очередь хранилище изображений, а не база данных географических объектов.
    так же стоит учитывать, что Wikimedia Commons - это международный проект, и не все объекты могут быть представлены на нем. Поэтому поиск по названию и городу может быть более эффективным, чем поиск по координатам.
    в конце концов, поиск по координатам может быть полезен, если объект не имеет уникального названия или если название объекта может быть неоднозначным.

    слоп из wiki: https://ru.wikipedia.org/wiki/Wikimedia_Commons не забыть добавить ссылку и текст в нижний край сайта


    Привет, Даник, не читай это все <3
    """

    name = (name or "").strip()
    city = (city or "").strip()

    if not name:
        return None

    try:
        async with aiohttp.ClientSession(
            headers=HEADERS
        ) as session:

            # -------------------------------------------------
            # 1. Поиск по названию объекта + город
            # -------------------------------------------------
            queries = [
                f'"{name}" {city} Belarus',
                f'"{name}" Belarus',
                f'{name} {city} Belarus',
            ]

            for query in queries:
                photo = await _search_by_text(
                    session=session,
                    query=query,
                    name=name,
                    city=city,
                    place_id=place_id,
                )

                if photo:
                    return photo

            # -------------------------------------------------
            # 2. Поиск фотографий рядом с объектом
            # -------------------------------------------------
            if lat is not None and lon is not None:
                photo = await _search_by_coordinates(
                    session=session,
                    name=name,
                    city=city,
                    lat=lat,
                    lon=lon,
                    place_id=place_id,
                )

                if photo:
                    return photo

    except Exception as exc:
        error(f"Ошибка Wikimedia: {exc}")

    return None


async def _search_by_text(
    session: aiohttp.ClientSession,
    query: str,
    name: str,
    city: str,
    place_id: str,
) -> dict | None:

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 10,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
    }

    try:
        async with session.get(
            WIKIMEDIA_API,
            params=params,
            timeout=15,
        ) as response:

            if response.status != 200:
                error(
                    f"Wikimedia API HTTP {response.status}"
                )
                return None

            data = await response.json()

        pages = data.get("query", {}).get("pages", {})

        if not pages:
            return None

        candidates = []

        for page in pages.values():
            title = page.get("title", "")

            image_info = page.get("imageinfo", [])
            if not image_info:
                continue

            info = image_info[0]
            original_url = info.get("url")

            if not original_url:
                continue

            score = _match_score(
                title=title,
                name=name,
                city=city,
            )

            if score <= 0:
                continue

            candidates.append(
                (
                    score,
                    title,
                    info,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        score, title, info = candidates[0]

        log(
            f"Wikimedia candidate: {title} "
            f"(score={score})"
        )

        return await _build_photo(
            session=session,
            info=info,
            place_id=place_id,
        )

    except Exception as exc:
        error(
            f"Ошибка поиска Wikimedia '{query}': {exc}"
        )
        return None


async def _search_by_coordinates(
    session: aiohttp.ClientSession,
    name: str,
    city: str,
    lat: float,
    lon: float,
    place_id: str,
) -> dict | None:

    params = {
        "action": "query",
        "format": "json",
        "generator": "geosearch",
        "ggsprimary": "all",
        "ggsnamespace": 6,
        "ggscoord": f"{lat}|{lon}",
        "ggsradius": 500,
        "ggslimit": 20,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
    }

    try:
        async with session.get(
            WIKIMEDIA_API,
            params=params,
            timeout=15,
        ) as response:

            if response.status != 200:
                return None

            data = await response.json()

        pages = data.get("query", {}).get("pages", {})

        candidates = []

        for page in pages.values():
            title = page.get("title", "")

            image_info = page.get("imageinfo", [])
            if not image_info:
                continue

            info = image_info[0]

            if not info.get("url"):
                continue

            score = _match_score(
                title=title,
                name=name,
                city=city,
            )

            # Для геопоиска разрешаем слабое совпадение,
            # но только если название изображения
            # хоть как-то связано с объектом.
            if score < 20:
                continue

            candidates.append(
                (
                    score,
                    title,
                    info,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        score, title, info = candidates[0]

        log(
            f"Wikimedia geo candidate: {title} "
            f"(score={score})"
        )

        return await _build_photo(
            session=session,
            info=info,
            place_id=place_id,
        )

    except Exception as exc:
        error(
            f"Ошибка Wikimedia geosearch: {exc}"
        )
        return None


def _match_score(
    title: str,
    name: str,
    city: str,
) -> int:

    title_normalized = _normalize_text(title)
    name_normalized = _normalize_text(name)
    city_normalized = _normalize_text(city)

    if not name_normalized:
        return 0

    score = 0

    # Полное название объекта
    if name_normalized in title_normalized:
        score += 100

    # Все существенные слова названия
    name_words = [
        word
        for word in name_normalized.split()
        if len(word) >= 3
    ]

    if name_words:
        matched_words = sum(
            1
            for word in name_words
            if word in title_normalized
        )

        score += int(
            80 * matched_words / len(name_words)
        )

    # Город
    if city_normalized and city_normalized in title_normalized:
        score += 30

    return score


def _normalize_text(value: str) -> str:
    value = value.lower()

    # Убираем File:
    value = value.replace("file:", "")

    # Убираем знаки пунктуации
    value = re.sub(
        r"[^a-zа-яё0-9\s]",
        " ",
        value,
        flags=re.IGNORECASE,
    )

    # Схлопываем пробелы
    value = re.sub(r"\s+", " ", value)

    return value.strip()


async def _build_photo(
    session: aiohttp.ClientSession,
    info: dict,
    place_id: str,
) -> dict | None:

    original_url = info.get("url")

    if not original_url:
        return None

    local_url = await _download_photo(
        session=session,
        original_url=original_url,
        place_id=place_id,
    )

    if not local_url:
        return None

    metadata = info.get(
        "extmetadata",
        {},
    )

    return {
        "source": "wikimedia",
        "original_url": original_url,
        "local_url": local_url,
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


async def _download_photo(
    session: aiohttp.ClientSession,
    original_url: str,
    place_id: str,
) -> str | None:

    try:
        async with session.get(
            original_url,
            timeout=20,
        ) as response:

            if response.status != 200:
                error(
                    f"Ошибка загрузки фото: "
                    f"HTTP {response.status}"
                )
                return None

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            if not content_type.startswith("image/"):
                return None

            data = await response.read()

    except Exception as exc:
        error(
            f"Ошибка загрузки фотографии: {exc}"
        )
        return None

    extension = _get_extension(
        content_type
    )

    filename = (
        hashlib.sha256(
            original_url.encode("utf-8")
        ).hexdigest()[:16]
        + extension
    )

    directory = (
        MEDIA_ROOT / place_id
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filepath = directory / filename

    if not filepath.exists():
        filepath.write_bytes(data)

        log(
            f"Фото сохранено: {filepath}"
        )

    return (
        f"/media/places/"
        f"{place_id}/"
        f"{filename}"
    )


def _metadata_value(
    metadata: dict,
    key: str,
) -> str | None:

    value = metadata.get(key)

    if not value:
        return None

    return value.get("value")


def _get_extension(
    content_type: str,
) -> str:

    extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }

    return extensions.get(
        content_type.split(";")[0].strip(),
        ".jpg",
    )