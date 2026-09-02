import hashlib
from pathlib import Path
from src.config import WIKIMEDIA_API_URL
import aiohttp

from src.utils.utils import log, error


WIKIMEDIA_API = WIKIMEDIA_API_URL or "https://commons.wikimedia.org/w/api.php"
MEDIA_ROOT = Path("media/places")

HEADERS = {
    "User-Agent": "JARVIS-Travel-Bot/1.0"
}


async def get_wikimedia_photo(
    name: str,
    city: str,
    place_id: str,
) -> dict | None:

    query = f'"{name}" {city} Belarus'

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 5,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
    }

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(
                WIKIMEDIA_API,
                params=params,
                timeout=15,
            ) as response:

                if response.status != 200:
                    error(
                        f"Wikimedia API вернул HTTP {response.status}"
                    )
                    return None

                data = await response.json()

            pages = data.get("query", {}).get("pages", {})

            for page in pages.values():
                image_info = page.get("imageinfo", [])

                if not image_info:
                    continue

                info = image_info[0]
                original_url = info.get("url")

                if not original_url:
                    continue

                local_url = await _download_photo(
                    session=session,
                    original_url=original_url,
                    place_id=place_id,
                )

                if not local_url:
                    continue

                metadata = info.get("extmetadata", {})

                return {
                    "source": "wikimedia",
                    "original_url": original_url,
                    "local_url": local_url,
                    "author": _metadata_value(
                        metadata,
                        "Artist",
                    ),
                    "license": (
                        _metadata_value(metadata, "LicenseShortName")
                        or _metadata_value(metadata, "UsageTerms")
                    ),
                }

    except Exception as exc:
        error(f"Ошибка Wikimedia: {exc}")

    return None


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
                return None

            content_type = response.headers.get(
                "Content-Type",
                ""
            )

            if not content_type.startswith("image/"):
                return None

            data = await response.read()

    except Exception as exc:
        error(f"Ошибка загрузки фотографии: {exc}")
        return None

    extension = _get_extension(content_type)

    filename = (
        hashlib.sha256(
            original_url.encode("utf-8")
        ).hexdigest()[:16]
        + extension
    )

    directory = MEDIA_ROOT / place_id
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filepath = directory / filename

    if not filepath.exists():
        filepath.write_bytes(data)
        log(f"Фото сохранено: {filepath}")

    return f"/media/places/{place_id}/{filename}"


def _metadata_value(
    metadata: dict,
    key: str,
) -> str | None:

    value = metadata.get(key)

    if not value:
        return None

    return value.get("value")


def _get_extension(content_type: str) -> str:

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