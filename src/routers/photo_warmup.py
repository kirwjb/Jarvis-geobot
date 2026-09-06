import asyncio

from fastapi import APIRouter, HTTPException

from src.database.db import AsyncSessionLocal
from src.database.models import Place
from src.routers.api_integrated import ensure_place_photo, photo_to_dict, get_place_by_id

router = APIRouter(prefix="/api/pois", tags=["photos"])

_photo_locks: dict[str, asyncio.Lock] = {}


def _lock_for(place_id: str) -> asyncio.Lock:
    lock = _photo_locks.get(place_id)
    if lock is None:
        lock = asyncio.Lock()
        _photo_locks[place_id] = lock
    return lock


@router.post("/{place_id}/photo")
async def warmup_place_photo(place_id: str):
    async with _lock_for(place_id):
        async with AsyncSessionLocal() as session:
            place = await get_place_by_id(session, place_id)
            if place is None:
                raise HTTPException(status_code=404, detail="Place not found")
            photo = await ensure_place_photo(session, place)
            await session.commit()
            return {"place_id": place_id, "photo": photo_to_dict(photo)}
