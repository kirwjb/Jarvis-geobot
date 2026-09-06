# api_integrated.py
"""
Основной API-слой приложения.
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from src.config import REGIONS, TOKEN
from src.database.db import AsyncSessionLocal
from src.database.models import Favorite, Place, PlacePhoto, User
from src.database.session_manager import redis_client
from src.database.repositories import photo_repo
from src.middleware.telegram_auth import TelegramAuthError, TelegramAuthMiddleware, validate_init_data
from src.services.map_service import build_google_maps_link
from src.services.optimizer_service import optimizeRoutePoints
from src.services.parser_service import get_attractions_osm
from src.services.routes_service import get_distance_osrm
from src.services.weather_service import get_weather
from src.services.wiki_service import get_wikimedia_photo
from src.utils.languages import get_text
from src.utils.utils import error, info, log, logger

class RegionResponse(BaseModel): id:str; name:str; cities:List[str]
class CityResponse(BaseModel): name:str; region:str
class WeatherResponse(BaseModel):
    city:str; temp:Optional[float]=None; description:str; humidity:Optional[int]=None; wind_speed:Optional[float]=None; pressure:Optional[int]=None; cached:bool=False
class POIQuery(BaseModel): region:str; city:Optional[str]=None; tags:List[str]=Field(default_factory=list); limit:int=30; offset:int=0
class POI(BaseModel):
    id:str; name:str; city:str; region:str; address:str; category:str; lat:float; lon:float; hours:Optional[str]=None; phone:Optional[str]=None; image_url:Optional[str]=None; images:Optional[dict]=None
class POIDetail(POI): photo:Optional[dict]=None
class RouteRequest(BaseModel): poi_ids:List[str]; optimize:bool=True
class RouteResponse(BaseModel): poi_ids:List[str]; google_maps_url:str; total_distance_km:Optional[float]=None; optimized:bool
class FavoriteToggle(BaseModel): poi_id:str

app=FastAPI(title="JARVIS GEO-APP API",description="Backend for Belarus Travel Telegram Mini App",version="2.2.0")
app.mount("/media",StaticFiles(directory="media"),name="media")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
app.add_middleware(TelegramAuthMiddleware,bot_token=TOKEN,max_age=86400)
MAX_POI_LIMIT=30; DEFAULT_POI_LIMIT=30

def normalize_region_id(region_name:str)->str:return region_name.lower().replace(" область","").replace(" ","_")
def normalize_category(value:str)->str:
    value=(value or "").lower()
    if "castle" in value or "замок" in value:return "castle"
    if any(x in value for x in ("church","cathedral","церк","собор","храм")):return "church"
    if "museum" in value or "музей" in value:return "museum"
    if "monument" in value or "памятник" in value:return "monument"
    if "park" in value or "парк" in value:return "park"
    if "gallery" in value or "галере" in value:return "gallery"
    if "viewpoint" in value or "смотров" in value:return "viewpoint"
    if "memorial" in value or "мемориал" in value:return "memorial"
    if "ruins" in value or "руины" in value:return "ruins"
    if "manor" in value or "усадь" in value:return "manor"
    if "theme_park" in value or "аттракцион" in value:return "theme_park"
    return "misc"
TAG_CATEGORY_MAP={"architecture":{"castle","church","monument","manor","gallery","ruins"},"nature":{"park","viewpoint","ruins"},"museum":{"museum"},"church":{"church"},"castle":{"castle"},"monument":{"monument"},"park":{"park"}}
def expand_poi_tags(tags:list[str])->set[str]:
    categories=set()
    for tag in tags:
        key=str(tag or "").strip().lower();categories.update(TAG_CATEGORY_MAP.get(key,{normalize_category(key)}))
    return categories
def normalize_limit(value:int)->int:return min(max(value,1),MAX_POI_LIMIT)
def normalize_offset(value:int)->int:return max(value,0)

def _photo_images(photo:PlacePhoto|None)->dict|None:
    if not photo:return None
    return {"thumb":photo.local_url_thumb or photo.original_url,"medium":photo.local_url_medium or photo.original_url,"original":photo.original_url}
def place_to_dict(place:Place,photo:PlacePhoto|None=None)->dict:
    images=_photo_images(photo)
    return {"id":place.place_id,"name":place.name,"city":place.city,"region":place.region,"address":place.address or "","category":place.category,"lat":float(place.lat),"lon":float(place.lon),"hours":place.hours,"phone":place.phone,"image_url":images.get("thumb") if images else None,"images":images}
def photo_to_dict(photo:PlacePhoto|None)->Optional[dict]:
    if photo is None:return None
    return {"source":photo.source,"original_url":photo.original_url,"local_url_thumb":photo.local_url_thumb,"local_url_medium":photo.local_url_medium,"author":photo.author,"license":photo.license}
async def get_photos_map(session,place_ids:list[str])->dict[str,PlacePhoto]:
    if not place_ids:return {}
    result=await session.execute(select(PlacePhoto).where(PlacePhoto.place_id.in_(place_ids)).order_by(PlacePhoto.id.asc()))
    result_map={}
    for photo in result.scalars().all():
        if photo.place_id not in result_map:result_map[photo.place_id]=photo
    return result_map
async def ensure_place_photo(session,place:Place)->PlacePhoto|None:
    result=await session.execute(select(PlacePhoto).where(PlacePhoto.place_id==place.place_id).order_by(PlacePhoto.id.asc()).limit(1));photo=result.scalar_one_or_none()
    if photo:return photo
    photo_data=await get_wikimedia_photo(name=place.name,city=place.city,place_id=place.place_id,lat=place.lat,lon=place.lon,category=place.category)
    if not photo_data:return None
    return await photo_repo.save_place_photo(session,place_id=place.place_id,source=photo_data["source"],original_url=photo_data["original_url"],local_url_thumb=photo_data.get("local_url_thumb"),local_url_medium=photo_data.get("local_url_medium"),author=photo_data.get("author"),license=photo_data.get("license"))
async def get_places_from_db(session,*,region:Optional[str]=None,city:Optional[str]=None,category:Optional[str|list[str]|set[str]]=None,offset:int=0,limit:int=MAX_POI_LIMIT)->list[Place]:
    query=select(Place)
    if region:query=query.where(Place.region==region)
    if city:query=query.where(Place.city==city)
    if category:query=query.where(Place.category.in_(category) if isinstance(category,(list,set,tuple)) else Place.category==category)
    result=await session.execute(query.order_by(Place.name.asc()).offset(offset).limit(limit));return list(result.scalars().all())
async def get_place_by_id(session,place_id:str)->Optional[Place]:
    result=await session.execute(select(Place).where(Place.place_id==place_id).limit(1));return result.scalar_one_or_none()
async def upsert_osm_places(session,attractions:list[dict],*,city:str,region:str)->list[Place]:
    result=[]
    for attr in attractions:
        pid,name,lat,lon=attr.get("id"),attr.get("name"),attr.get("lat"),attr.get("lon")
        if not pid or not name or lat is None or lon is None:continue
        category=normalize_category(attr.get("type",""));existing=await session.execute(select(Place).where(Place.place_id==pid).limit(1));place=existing.scalar_one_or_none()
        if place is None:
            place=Place(place_id=pid,name=name,city=city,region=region,address=attr.get("address") or "",category=category,lat=float(lat),lon=float(lon),hours=attr.get("hours"),phone=attr.get("phone"));session.add(place)
        else:
            place.name=name;place.city=city;place.region=region;place.address=attr.get("address") or "";place.category=category;place.lat=float(lat);place.lon=float(lon);place.hours=attr.get("hours");place.phone=attr.get("phone")
        result.append(place)
    await session.flush();return result
async def check_weather_cache(city:str)->Optional[dict]:
    cached=await redis_client.get(f"weather:{city}")
    if not cached:return None
    try:
        data=json.loads(cached);timestamp=datetime.fromisoformat(data["timestamp"])
        return data if timestamp>datetime.utcnow()-timedelta(minutes=30) else None
    except (json.JSONDecodeError,KeyError,ValueError,TypeError) as exc:error(f"Ошибка чтения weather cache для {city}: {exc}")
    return None
async def set_weather_cache(city:str,data:dict)->None:
    await redis_client.setex(f"weather:{city}",1800,json.dumps({**data,"timestamp":datetime.utcnow().isoformat()},ensure_ascii=False))

@app.get("/")
async def root():return {"status":"JARVIS GEO-APP API","version":"2.2.0"}
@app.get("/api/regions",response_model=List[RegionResponse])
async def get_regions():return [RegionResponse(id=normalize_region_id(n),name=n,cities=c) for n,c in REGIONS.items()]
@app.get("/api/cities/{region_id}",response_model=List[CityResponse])
async def get_cities(region_id:str):
    for name,cities in REGIONS.items():
        if normalize_region_id(name)==region_id:return [CityResponse(name=c,region=name) for c in cities]
    raise HTTPException(status_code=404,detail=get_text("choose_city_empty"))
@app.get("/api/weather/{city}",response_model=WeatherResponse)
async def get_weather_endpoint(city:str):
    cached=await check_weather_cache(city)
    if cached:return WeatherResponse(city=city,temp=cached.get("temp"),description=cached.get("description",""),humidity=cached.get("humidity"),wind_speed=cached.get("wind_speed"),pressure=cached.get("pressure"),cached=True)
    try:
        weather=json.loads(await get_weather(city));await set_weather_cache(city,weather);return WeatherResponse(city=city,temp=weather.get("temp"),description=weather.get("description",""),humidity=weather.get("humidity"),wind_speed=weather.get("wind_speed"),pressure=weather.get("pressure"))
    except Exception as exc:error(f"Weather API error for {city}: {exc}");raise HTTPException(status_code=500,detail=get_text("internal_error"))

@app.post("/api/pois/query")
async def query_pois(query:POIQuery):
    if not query.city:raise HTTPException(status_code=400,detail="City required")
    limit,offset=normalize_limit(query.limit),normalize_offset(query.offset);cats=expand_poi_tags(query.tags) if query.tags else None
    async with AsyncSessionLocal() as session:
        places=await get_places_from_db(session,region=query.region,city=query.city,category=cats,offset=offset,limit=limit)
        if not places and offset==0:
            osm=await get_attractions_osm(query.city,limit=100)
            if osm:
                await upsert_osm_places(session,osm,city=query.city,region=query.region);await session.commit()
                places=await get_places_from_db(session,region=query.region,city=query.city,category=cats,offset=offset,limit=limit)
        for place in places:await ensure_place_photo(session,place)
        photos=await get_photos_map(session,[p.place_id for p in places]);pois=[place_to_dict(p,photos.get(p.place_id)) for p in places]
        await session.commit();return {"count":len(pois),"region":query.region,"city":query.city,"tags":query.tags,"offset":offset,"limit":limit,"pois":pois}

@app.get("/api/pois")
async def get_all_pois(region:Optional[str]=None,city:Optional[str]=None,category:Optional[str]=None,offset:int=0,limit:int=30):
    limit,offset=normalize_limit(limit),normalize_offset(offset)
    async with AsyncSessionLocal() as session:
        places=await get_places_from_db(session,region=region,city=city,category=normalize_category(category) if category else None,offset=offset,limit=limit);photos=await get_photos_map(session,[p.place_id for p in places]);return {"pois":[place_to_dict(p,photos.get(p.place_id)) for p in places],"count":len(places),"offset":offset,"limit":limit}
@app.get("/api/pois/{place_id}",response_model=POIDetail)
async def get_poi_detail(place_id:str):
    async with AsyncSessionLocal() as session:
        place=await get_place_by_id(session,place_id)
        if place is None:raise HTTPException(status_code=404,detail="Place not found")
        result=await session.execute(select(PlacePhoto).where(PlacePhoto.place_id==place_id).order_by(PlacePhoto.id.asc()).limit(1));photo=result.scalar_one_or_none();return POIDetail(**place_to_dict(place,photo),photo=photo_to_dict(photo))
@app.get("/api/pois/{place_id}/photos")
async def get_poi_photos(place_id:str):
    async with AsyncSessionLocal() as session:
        if await get_place_by_id(session,place_id) is None:raise HTTPException(status_code=404,detail="Place not found")
        result=await session.execute(select(PlacePhoto).where(PlacePhoto.place_id==place_id).order_by(PlacePhoto.id.asc()));return {"place_id":place_id,"photos":[photo_to_dict(p) for p in result.scalars().all()]}

@app.post("/api/route/build",response_model=RouteResponse)
async def build_route(req:RouteRequest):
    ids=list(dict.fromkeys(x for x in req.poi_ids if x))
    if len(ids)<2:raise HTTPException(status_code=400,detail=get_text("min_points_error",count=len(ids)))
    async with AsyncSessionLocal() as session:result=await session.execute(select(Place).where(Place.place_id.in_(ids)));places=list(result.scalars().all())
    by_id={p.place_id:p for p in places};points=[{"id":i,"lat":float(by_id[i].lat),"lon":float(by_id[i].lon),"name":by_id[i].name} for i in ids if i in by_id and by_id[i].lat is not None and by_id[i].lon is not None]
    if len(points)<2:raise HTTPException(status_code=400,detail="Need at least 2 points with coordinates")
    if req.optimize:points=optimizeRoutePoints(points)
    url=build_google_maps_link(points)
    if not url:raise HTTPException(status_code=500,detail="Unable to build Google Maps route")
    total=0.0
    for a,b in zip(points,points[1:]):
        d=await get_distance_osrm(a["lat"],a["lon"],b["lat"],b["lon"])
        if d is None:total=None;break
        total+=d
    return RouteResponse(poi_ids=[p["id"] for p in points],google_maps_url=url,total_distance_km=round(total,1) if total is not None else None,optimized=req.optimize)

@app.post("/api/favorites/toggle")
async def toggle_favorite(data:FavoriteToggle,request:Request):
    uid=request.state.telegram_user_id
    async with AsyncSessionLocal() as session:
        r=await session.execute(select(User).where(User.user_id==uid));user=r.scalar_one_or_none()
        if user is None:user=User(user_id=uid,username=request.state.telegram_user.get("username",""));session.add(user);await session.flush()
        r=await session.execute(select(Favorite).where(Favorite.user_id==uid,Favorite.place_id==data.poi_id).limit(1));existing=r.scalar_one_or_none()
        if existing:await session.execute(delete(Favorite).where(Favorite.id==existing.id));await session.commit();return {"poi_id":data.poi_id,"user_id":uid,"favorited":False}
        place=await get_place_by_id(session,data.poi_id)
        if place is None:raise HTTPException(status_code=404,detail="Place not found")
        session.add(Favorite(user_id=uid,place_id=place.place_id,place_name=place.name,address=place.address or "",lat=float(place.lat),lon=float(place.lon)));await session.commit();return {"poi_id":data.poi_id,"user_id":uid,"favorited":True}
@app.get("/api/favorites/me")
async def get_favorites(request:Request):
    uid=request.state.telegram_user_id
    async with AsyncSessionLocal() as session:
        r=await session.execute(select(Favorite).where(Favorite.user_id==uid).order_by(Favorite.created_at.desc()));favorites=r.scalars().all();return {"user_id":uid,"favorites":[{"id":f.id,"place_id":f.place_id,"place_name":f.place_name,"address":f.address,"lat":f.lat,"lon":f.lon} for f in favorites]}
@app.get("/health")
async def health():return {"status":"ok","timestamp":datetime.utcnow().isoformat()}
@app.post("/api/auth/telegram")
async def auth_telegram(request:Request):
    authorization=request.headers.get("Authorization","")
    if not authorization.startswith("tma "):raise HTTPException(status_code=401,detail="Telegram authentication required")
    try:user_data=validate_init_data(authorization[4:].strip(),TOKEN,max_age=86400)
    except TelegramAuthError as exc:raise HTTPException(status_code=401,detail=str(exc)) from exc
    uid=int(user_data["id"]);username=user_data.get("username","")
    async with AsyncSessionLocal() as session:
        r=await session.execute(select(User).where(User.user_id==uid));user=r.scalar_one_or_none();new=user is None
        if new:user=User(user_id=uid,username=username);session.add(user)
        else:user.username=username
        await session.commit();return {"user_id":uid,"username":username,"is_new":new,"tokens":user.tokens}
if __name__=="__main__":
    import uvicorn;uvicorn.run(app,host="0.0.0.0",port=8000)
