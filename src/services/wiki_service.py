from pathlib import Path
from src.config import WIKIMEDIA_API_URL
import aiohttp


WIKI_API = WIKIMEDIA_API_URL
PHOTO_DIR = Path("media/wiki")


async def get_wiki_photo(
    name: str,
    place_id: str,
) -> dict | None:

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": name,
        "gsrnamespace": 6,
        "gsrlimit": 1,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 1200,
    }

    try:
        async with aiohttp.ClientSession() as session:

            async with session.get(
                WIKI_API,
                params=params,
                timeout=10,
            ) as response:

                if response.status != 200:
                    return None

                data = await response.json()

            pages = data.get("query", {}).get("pages", {})

            if not pages:
                return None

            page = next(iter(pages.values()))
            info = page.get("imageinfo")

            if not info:
                return None

            url = info[0].get("thumburl") or info[0].get("url")

            if not url:
                return None

            PHOTO_DIR.mkdir(parents=True, exist_ok=True)

            path = PHOTO_DIR / f"{place_id}.jpg"

            async with session.get(url, timeout=20) as image:

                if image.status != 200:
                    return None

                path.write_bytes(await image.read())

            return {
                "url": url,
                "path": str(path),
            }

    except Exception:
        return None