import re
import shutil
from pathlib import Path
from pydantic import BaseModel, Field
import aiohttp
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import Place, PlacePhoto
from src.database.repositories import photo_repo
from src.services.wiki_service import get_wikimedia_photo
from src.services.wikimedia_geo_service import find_photo_by_coordinates
from src.utils.wiki_filters import is_sensitive_or_blocked_content
from src.utils.utils import log

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

        db_photo = (
            await session.execute(
                select(PlacePhoto)
                .where(PlacePhoto.place_id == place_id)
                .order_by(PlacePhoto.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if db_photo and db_photo.source == "blocked":
            return {"photo": None, "blocked": True}

        if db_photo and (db_photo.local_url_thumb or db_photo.original_url):
            if is_sensitive_or_blocked_content(f"{db_photo.original_url} {db_photo.author or ''}"):
                await photo_repo.block_place_photo(session, place_id)
                await session.commit()
                return {"photo": None, "blocked": True}
            thumb = db_photo.local_url_thumb or db_photo.original_url
            medium = db_photo.local_url_medium or db_photo.original_url or thumb
            orig = db_photo.original_url or medium
            if thumb and thumb.startswith("http://"):
                thumb = "https://" + thumb[7:]
            if medium and medium.startswith("http://"):
                medium = "https://" + medium[7:]
            if orig and orig.startswith("http://"):
                orig = "https://" + orig[7:]
            return {
                "photo": {
                    "source": db_photo.source or "cached",
                    "original_url": orig,
                    "medium_url": medium,
                    "thumbnail_url": thumb,
                    "author": db_photo.author,
                    "license": db_photo.license,
                }
            }

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
            medium = saved.local_url_medium or saved.original_url or thumb
            orig = saved.original_url or medium
            if thumb and thumb.startswith("http://"):
                thumb = "https://" + thumb[7:]
            if medium and medium.startswith("http://"):
                medium = "https://" + medium[7:]
            if orig and orig.startswith("http://"):
                orig = "https://" + orig[7:]
            return {
                "photo": {
                    "source": saved.source or "wikimedia",
                    "original_url": orig,
                    "medium_url": medium,
                    "thumbnail_url": thumb,
                    "author": saved.author,
                    "license": saved.license,
                }
            }

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
        if db_photo and db_photo.source == "blocked":
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
                "photo": None,
                "images": None,
                "image_url": None,
            }

        if db_photo and (db_photo.local_url_thumb or db_photo.original_url):
            if is_sensitive_or_blocked_content(f"{db_photo.original_url} {db_photo.author or ''}"):
                await photo_repo.block_place_photo(session, place_id)
                await session.commit()
                db_photo = None
            else:
                thumb = db_photo.local_url_thumb or db_photo.original_url
                medium = db_photo.local_url_medium or db_photo.original_url or thumb
                orig = db_photo.original_url or medium
                if thumb and thumb.startswith("http://"):
                    thumb = "https://" + thumb[7:]
                if medium and medium.startswith("http://"):
                    medium = "https://" + medium[7:]
                if orig and orig.startswith("http://"):
                    orig = "https://" + orig[7:]
                photo = {
                    "source": db_photo.source or "cached",
                    "original_url": orig,
                    "medium_url": medium,
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
                medium = saved.local_url_medium or saved.original_url or thumb
                orig = saved.original_url or medium
                if thumb and thumb.startswith("http://"):
                    thumb = "https://" + thumb[7:]
                if medium and medium.startswith("http://"):
                    medium = "https://" + medium[7:]
                if orig and orig.startswith("http://"):
                    orig = "https://" + orig[7:]
                photo = {
                    "source": saved.source or "wikimedia",
                    "original_url": orig,
                    "medium_url": medium,
                    "thumbnail_url": thumb,
                    "author": saved.author,
                    "license": saved.license,
                }
            elif place.lat is not None and place.lon is not None:
                coord_photo = await find_photo_by_coordinates(float(place.lat), float(place.lon))
                if coord_photo:
                    photo = coord_photo

        high_res = (
            photo.get("medium_url")
            or photo.get("original_url")
            or photo.get("thumbnail_url")
        ) if photo else None

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
            "images": {
                "thumb": photo.get("thumbnail_url"),
                "medium": photo.get("medium_url") or photo.get("original_url"),
                "original": photo.get("original_url"),
            } if photo else None,
            "image_url": high_res,
        }

@router.get("/photo-proxy")
async def photo_proxy(url: str = Query(...)):
    """Reverse proxy for Wikimedia Commons images to bypass Referer blocks and mixed content."""
    clean_url = url.strip()
    if clean_url.startswith("http://"):
        clean_url = "https://" + clean_url[7:]

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

class ReportPhotoRequest(BaseModel):
    reason: str = Field(default="inappropriate", description="Причина жалобы")
    details: str | None = Field(default=None, description="Дополнительные детали")
    photo_url: str | None = Field(default=None, description="URL фотографии")

class BlockPhotoRequest(BaseModel):
    reason: str | None = Field(default="user_blocked", description="Причина удаления/блокировки")

@router.post("/pois/{place_id}/report-photo")
async def report_photo(place_id: str, body: ReportPhotoRequest = ReportPhotoRequest()):
    async with AsyncSessionLocal() as session:
        place = (
            await session.execute(
                select(Place).where(Place.place_id == place_id)
            )
        ).scalar_one_or_none()
        if not place:
            raise HTTPException(404, "Place not found")

        photo_url = body.photo_url
        if not photo_url:
            db_photo = (
                await session.execute(
                    select(PlacePhoto).where(PlacePhoto.place_id == place_id).limit(1)
                )
            ).scalar_one_or_none()
            if db_photo:
                photo_url = db_photo.original_url

        try:
            await photo_repo.save_photo_report(
                session,
                place_id=place_id,
                photo_url=photo_url,
                reason=body.reason or "inappropriate",
                details=body.details,
            )
            await session.commit()
        except Exception as exc:
            await session.rollback()
            log(f"Warning: could not save report to DB: {exc}")

        log(f"Photo reported for place {place_id}: reason='{body.reason}', details='{body.details}'")
        return {
            "status": "success",
            "place_id": place_id,
            "message": "Жалоба принята на рассмотрение. Спасибо!",
        }

@router.post("/pois/{place_id}/block-photo")
@router.post("/pois/{place_id}/delete-photo")
@router.delete("/pois/{place_id}/photo")
async def block_photo(place_id: str, body: BlockPhotoRequest = BlockPhotoRequest()):
    async with AsyncSessionLocal() as session:
        place = (
            await session.execute(
                select(Place).where(Place.place_id == place_id)
            )
        ).scalar_one_or_none()
        if not place:
            raise HTTPException(404, "Place not found")

        clean_pid = re.sub(r"[^\w\-]", "_", place_id)
        place_media_dir = Path("media/places") / clean_pid
        if place_media_dir.exists() and place_media_dir.is_dir():
            try:
                shutil.rmtree(place_media_dir, ignore_errors=True)
            except Exception as exc:
                log(f"Warning: Could not remove media cache files for {place_id}: {exc}")

        await photo_repo.block_place_photo(session, place_id, reason=body.reason or "user_blocked")
        await session.commit()

        log(f"Photo blocked and removed for place {place_id} (reason: {body.reason})")
        return {
            "status": "success",
            "place_id": place_id,
            "message": "Фотография успешно удалена и заблокирована.",
            "photo": None,
        }

poi_router = APIRouter(prefix="/api/pois", tags=["photos"])

@poi_router.post("/{place_id}/report-photo")
async def report_photo_pois_alias(place_id: str, body: ReportPhotoRequest = ReportPhotoRequest()):
    return await report_photo(place_id, body)

@poi_router.post("/{place_id}/block-photo")
@poi_router.post("/{place_id}/delete-photo")
@poi_router.delete("/{place_id}/photo")
async def block_photo_pois_alias(place_id: str, body: BlockPhotoRequest = BlockPhotoRequest()):
    return await block_photo(place_id, body)

