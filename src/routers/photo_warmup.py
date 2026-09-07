import asyncio
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import Place, PlacePhoto
from src.services.photo_url_service import find_photo_url

router = APIRouter(prefix="/api/pois", tags=["photos"])
_photo_locks: dict[str, asyncio.Lock] = {}

def _lock_for(place_id: str) -> asyncio.Lock:
    lock = _photo_locks.get(place_id)
    if lock is None:
        lock = asyncio.Lock(); _photo_locks[place_id] = lock
    return lock

@router.post("/{place_id}/photo")
async def warmup_place_photo(place_id: str):
    async with _lock_for(place_id):
        async with AsyncSessionLocal() as session:
            row = await session.execute(select(Place).where(Place.place_id == place_id).limit(1)); place = row.scalar_one_or_none()
            if place is None: raise HTTPException(status_code=404, detail="Place not found")
            row = await session.execute(select(PlacePhoto).where(PlacePhoto.place_id == place_id).order_by(PlacePhoto.id.asc()).limit(1)); photo = row.scalar_one_or_none()
            if photo and photo.original_url: return {"place_id": place_id, "photo": {"source": photo.source, "original_url": photo.original_url, "author": photo.author, "license": photo.license}}
            data = await find_photo_url(name=place.name, city=place.city, lat=place.lat, lon=place.lon, category=place.category)
            if data:
                if photo is None:
                    photo = PlacePhoto(place_id=place_id, source=data["source"], original_url=data["original_url"], local_url_thumb=None, local_url_medium=None, author=data.get("author"), license=data.get("license")); session.add(photo)
                else:
                    photo.source=data["source"]; photo.original_url=data["original_url"]; photo.local_url_thumb=None; photo.local_url_medium=None; photo.author=data.get("author"); photo.license=data.get("license")
                await session.commit()
                return {"place_id": place_id, "photo": {"source": photo.source, "original_url": photo.original_url, "author": photo.author, "license": photo.license}}
            return {"place_id": place_id, "photo": None}
