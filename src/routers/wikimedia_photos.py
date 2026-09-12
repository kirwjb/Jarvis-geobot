from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import Place
from src.services.wikimedia_geo_service import find_photo_by_coordinates

router=APIRouter(prefix='/api/geo',tags=['photos'])

@router.get('/pois/{place_id}/wikimedia-photo')
async def wikimedia_photo(place_id:str):
    async with AsyncSessionLocal() as session:
        place=(await session.execute(select(Place).where(Place.place_id==place_id))).scalar_one_or_none()
        if not place: raise HTTPException(404,'Place not found')
    return {'photo':await find_photo_by_coordinates(float(place.lat),float(place.lon))}

@router.get('/pois/{place_id}/wikimedia-detail')
async def wikimedia_detail(place_id:str):
    async with AsyncSessionLocal() as session:
        place=(await session.execute(select(Place).where(Place.place_id==place_id))).scalar_one_or_none()
        if not place: raise HTTPException(404,'Place not found')
    return {'id':place.place_id,'name':place.name,'city':place.city,'region':place.region,'address':place.address or '','category':place.category,'lat':float(place.lat),'lon':float(place.lon),'hours':place.hours,'phone':place.phone,'photo':await find_photo_by_coordinates(float(place.lat),float(place.lon))}
