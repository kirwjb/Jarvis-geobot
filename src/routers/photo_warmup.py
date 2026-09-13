from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import Place
from src.services.wikimedia_geo_service import find_photo_by_coordinates

router=APIRouter(prefix='/api/pois',tags=['photos'])

@router.post('/{place_id}/photo')
async def warmup_place_photo(place_id:str):
    async with AsyncSessionLocal() as session:
        place=(await session.execute(select(Place).where(Place.place_id==place_id))).scalar_one_or_none()
        if not place:raise HTTPException(404,'Place not found')
    photo=await find_photo_by_coordinates(float(place.lat),float(place.lon))
    return {'place_id':place_id,'photo':photo}
