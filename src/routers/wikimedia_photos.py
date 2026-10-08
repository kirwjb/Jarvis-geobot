import aiohttp
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import Place, PlacePhoto
from src.database.repositories import photo_repo
from src.services.wiki_service import get_wikimedia_photo
from src.services.wikimedia_geo_service import find_photo_by_coordinates

router = APIRouter(prefix="/api/geo", tags=["photos"])


@router.get("/pois/{place_id}/wikimedia-photo")
async def wikimedia_photo(place_id: str):
    async with AsyncSessionLocal() as session:
        place = (
            await session.execute(
                select(Place).where(Place.place_id == place_id)
            )
        ).scalar_one_or_none()
        if not place:
            raise HTTPException(404, "Place not found")

        # 1. Check if we already have a cached photo in DB
        db_photo = (
            await session.execute(
                select(PlacePhoto)
                .where(PlacePhoto.place_id == place_id)
                .order_by(PlacePhoto.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if db_photo and (db_photo.local_url_thumb or db_photo.original_url):
            thumb = db_photo.local_url_thumb or db_photo.original_url
            orig = db_photo.original_url
            if thumb and thumb.startswith("http://"):
                thumb = "https://" + thumb[7:]
            if orig and orig.startswith("http://"):
                orig = "https://" + orig[7:]
            return {
                "photo": {
                    "source": db_photo.source or "cached",
                    "original_url": orig,
                    "thumbnail_url": thumb,
                    "author": db_photo.author,
                    "license": db_photo.license,
                }
            }

        # 2. Query Wikimedia via full cascading pipeline (OSM tags, Wikidata P18, categories, cascading normalized text)
        photo_data = await get_wikimedia_photo(
            name=place.name,
            city=place.city,
            place_id=place.place_id,
            lat=float(place.lat) if place.lat is not None else None,
            lon=float(place.lon) if place.lon is not None else None,
            category=place.category,
        )
        if photo_data:
            saved = await photo_repo.save_place_photo(
                session,
                place_id=place.place_id,
                source=photo_data.get("source", "wikimedia"),
                original_url=photo_data["original_url"],
                local_url_thumb=photo_data.get("local_url_thumb"),
                local_url_medium=photo_data.get("local_url_medium"),
                author=photo_data.get("author"),
                license=photo_data.get("license"),
            )
            await session.commit()
            thumb = saved.local_url_thumb or saved.original_url
            orig = saved.original_url
            if thumb and thumb.startswith("http://"):
                thumb = "https://" + thumb[7:]
            if orig and orig.startswith("http://"):
                orig = "https://" + orig[7:]
            return {
                "photo": {
                    "source": saved.source or "wikimedia",
                    "original_url": orig,
                    "thumbnail_url": thumb,
                    "author": saved.author,
                    "license": saved.license,
                }
            }

        # 3. Fallback to geocoordinates search
        if place.lat is not None and place.lon is not None:
            photo = await find_photo_by_coordinates(float(place.lat), float(place.lon))
            if photo:
                return {"photo": photo}
        return {"photo": None}


@router.get("/pois/{place_id}/wikimedia-detail")
async def wikimedia_detail(place_id: str):
    async with AsyncSessionLocal() as session:
        place = (
            await session.execute(
                select(Place).where(Place.place_id == place_id)
            )
        ).scalar_one_or_none()
        if not place:
            raise HTTPException(404, "Place not found")

        db_photo = (
            await session.execute(
                select(PlacePhoto)
                .where(PlacePhoto.place_id == place_id)
                .order_by(PlacePhoto.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

        photo = None
        if db_photo and (db_photo.local_url_thumb or db_photo.original_url):
            thumb = db_photo.local_url_thumb or db_photo.original_url
            orig = db_photo.original_url
            if thumb and thumb.startswith("http://"):
                thumb = "https://" + thumb[7:]
            if orig and orig.startswith("http://"):
                orig = "https://" + orig[7:]
            photo = {
                "source": db_photo.source or "cached",
                "original_url": orig,
                "thumbnail_url": thumb,
                "author": db_photo.author,
                "license": db_photo.license,
            }

        if not photo:
            photo_data = await get_wikimedia_photo(
                name=place.name,
                city=place.city,
                place_id=place.place_id,
                lat=float(place.lat) if place.lat is not None else None,
                lon=float(place.lon) if place.lon is not None else None,
                category=place.category,
            )
            if photo_data:
                saved = await photo_repo.save_place_photo(
                    session,
                    place_id=place.place_id,
                    source=photo_data.get("source", "wikimedia"),
                    original_url=photo_data["original_url"],
                    local_url_thumb=photo_data.get("local_url_thumb"),
                    local_url_medium=photo_data.get("local_url_medium"),
                    author=photo_data.get("author"),
                    license=photo_data.get("license"),
                )
                await session.commit()
                thumb = saved.local_url_thumb or saved.original_url
                orig = saved.original_url
                if thumb and thumb.startswith("http://"):
                    thumb = "https://" + thumb[7:]
                if orig and orig.startswith("http://"):
                    orig = "https://" + orig[7:]
                photo = {
                    "source": saved.source or "wikimedia",
                    "original_url": orig,
                    "thumbnail_url": thumb,
                    "author": saved.author,
                    "license": saved.license,
                }
            elif place.lat is not None and place.lon is not None:
                photo = await find_photo_by_coordinates(float(place.lat), float(place.lon))

        return {
            "id": place.place_id,
            "name": place.name,
            "city": place.city,
            "region": place.region,
            "address": place.address or "",
            "category": place.category,
            "lat": float(place.lat),
            "lon": float(place.lon),
            "hours": place.hours,
            "phone": place.phone,
            "photo": photo,
        }


@router.get("/photo-proxy")
async def photo_proxy(url: str = Query(...)):
    """Reverse proxy for Wikimedia Commons images to bypass Referer blocks and mixed content."""
    clean_url = url.strip()
    if clean_url.startswith("http://"):
        clean_url = "https://" + clean_url[7:]

    # Validate that target domain belongs to Wikimedia Commons
    is_wikimedia = (
        clean_url.startswith("https://upload.wikimedia.org/")
        or clean_url.startswith("https://commons.wikimedia.org/")
        or ".wikimedia.org/" in clean_url
    )
    if not is_wikimedia:
        raise HTTPException(400, "Only Wikimedia Commons images can be proxied")

    headers = {
        "User-Agent": "JARVIS-GEO-APP/2.0 (Wikimedia proxy; contact: kirwjb@gmail.com)",
        "Accept": "image/webp,image/avif,image/jpeg,image/png,*/*",
        "ngrok-skip-browser-warning": "true",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(clean_url) as upstream:
                if upstream.status != 200:
                    raise HTTPException(
                        upstream.status, f"Upstream photo fetch failed with status {upstream.status}"
                    )
                content = await upstream.read()
                content_type = upstream.headers.get("Content-Type", "image/jpeg")
                return Response(
                    content=content,
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=604800, immutable",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                        "ngrok-skip-browser-warning": "true",
                    },
                )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Proxy error: {exc}")
