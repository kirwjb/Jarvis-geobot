"""URL-only Wikimedia Commons photo lookup.

The service never downloads image bytes. It queries Commons for files geotagged
near an OSM point and returns Wikimedia's own image URLs to the frontend.
"""

from __future__ import annotations

import math
from typing import Any

import aiohttp

API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "JARVIS-GEO-APP/2.0 (Wikimedia Commons geosearch; contact: kirwjb@gmail.com)"
MIN_DISTANCE_M = 0.0
DEFAULT_SEARCH_RADIUS_M = 300
MAX_SEARCH_RADIUS_M = 600
MAX_RESULTS = 25


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance between two WGS84 coordinates in metres."""
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _image_info(page: dict[str, Any], distance_m: float) -> dict[str, Any] | None:
    """Convert a Commons file page into the URL-only API representation."""
    info = (page.get("imageinfo") or [None])[0]
    if not info or not info.get("url"):
        return None
    if not str(info.get("mime") or "").startswith("image/"):
        return None

    # Filter out SVG icons, maps, and coat of arms if identifiable
    title = str(page.get("title", "")).lower()
    if any(ext in title for ext in (".svg", "coat_of_arms", "flag_of", "map_", "locator")):
        return None

    metadata = info.get("extmetadata") or {}
    artist = metadata.get("Artist") or {}
    license_name = metadata.get("LicenseShortName") or {}

    raw_url = str(info["url"])
    raw_thumb = str(info.get("thumburl") or raw_url)

    # Force HTTPS to prevent mixed content errors over ngrok
    if raw_url.startswith("http://"):
        raw_url = "https://" + raw_url[7:]
    if raw_thumb.startswith("http://"):
        raw_thumb = "https://" + raw_thumb[7:]

    return {
        "source": "wikimedia",
        "original_url": raw_url,
        "thumbnail_url": raw_thumb,
        "author": artist.get("value"),
        "license": license_name.get("value"),
        "title": page.get("title", ""),
        "distance_m": round(distance_m, 2),
    }


async def find_photo_by_coordinates(
    lat: float,
    lon: float,
    *,
    radius_m: int = DEFAULT_SEARCH_RADIUS_M,
) -> dict[str, Any] | None:
    """Find the nearest usable Commons image geotagged within radius of POI."""
    radius = min(max(int(radius_m), 25), MAX_SEARCH_RADIUS_M)
    params = {
        "action": "query",
        "format": "json",
        "generator": "geosearch",
        "ggsprimary": "all",
        "ggsnamespace": 6,
        "ggscoord": f"{float(lat)},{float(lon)}",
        "ggsradius": radius,
        "ggslimit": MAX_RESULTS,
        "prop": "imageinfo|coordinates",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 800,
        "colimit": 1,
    }
    timeout = aiohttp.ClientTimeout(total=8)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "ngrok-skip-browser-warning": "true",
    }

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(API_URL, params=params) as response:
                if response.status != 200:
                    return None
                data = await response.json()
    except Exception:
        return None

    candidates: list[dict[str, Any]] = []
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        coords = page.get("coordinates") or []
        if not coords:
            continue
        try:
            photo_lat = float(coords[0]["lat"])
            photo_lon = float(coords[0]["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        distance = _distance_m(float(lat), float(lon), photo_lat, photo_lon)
        if distance > radius:
            continue
        image = _image_info(page, distance)
        if image:
            candidates.append(image)

    candidates.sort(key=lambda item: item["distance_m"])
    return candidates[0] if candidates else None
