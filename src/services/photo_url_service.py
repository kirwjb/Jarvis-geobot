"""Lightweight Wikimedia image lookup.

Unlike the legacy photo service this module never downloads image bytes.
Only the remote Wikimedia URL and attribution metadata are returned.
"""
import aiohttp

from src.config import WIKIMEDIA_API_URL
from src.utils.utils import error
from src.utils.wiki_filters import TYPE_QUERY_WORDS, is_valid_photo, match_score

WIKIMEDIA_API = WIKIMEDIA_API_URL or "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "JARVIS-Travel-Bot/2.0 (external image URLs only)"}

async def find_photo_url(*, name: str, city: str, lat: float | None = None, lon: float | None = None, category: str = "") -> dict | None:
    name = (name or "").strip()
    city = (city or "").strip()
    if not name:
        return None
    type_words = TYPE_QUERY_WORDS.get((category or "").lower(), "")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        candidates = []
        if lat is not None and lon is not None:
            candidates.extend(await _query(session, {
                "generator": "geosearch", "ggsprimary": "all", "ggsnamespace": 6,
                "ggscoord": f"{lat}|{lon}", "ggsradius": 500, "ggslimit": 30,
            }))
        if not candidates:
            for query in (f'"{name}" "{city}" Belarus', f'"{name}" {city} Belarus', f'"{name}" Belarus'):
                candidates.extend(await _query(session, {
                    "generator": "search", "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 20,
                }))
                if candidates:
                    break
        scored = []
        for page in candidates:
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("url")
            if not url or not is_valid_photo(info):
                continue
            title = page.get("title", "")
            score = match_score(title=title, name=name, city=city, extra_words=type_words)
            if score > 0:
                scored.append((score, title, info))
        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        score, title, info = scored[0]
        metadata = info.get("extmetadata") or {}
        def meta(key: str) -> str | None:
            value = metadata.get(key, {})
            return value.get("value") if isinstance(value, dict) else None
        return {
            "source": "wikimedia",
            "original_url": info["url"],
            "author": meta("Artist"),
            "license": meta("LicenseShortName") or meta("UsageTerms"),
            "title": title,
            "score": score,
        }

async def _query(session: aiohttp.ClientSession, params: dict) -> list[dict]:
    payload = {"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|extmetadata", **params}
    try:
        async with session.get(WIKIMEDIA_API, params=payload, timeout=15) as response:
            if response.status != 200:
                return []
            data = await response.json(content_type=None)
            return list(data.get("query", {}).get("pages", {}).values())
    except Exception as exc:
        error(f"Wikimedia URL lookup failed: {exc}")
        return []
