"""
Основной API-слой приложения.
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import case, delete, func, or_, select
from src.config import REGIONS, TOKEN
from src.database.db import AsyncSessionLocal
from src.database.models import Favorite, Place, PlacePhoto, User
from src.database.session_manager import redis_client
from src.database.repositories import photo_repo
from src.middleware.telegram_auth import TelegramAuthError, TelegramAuthMiddleware, validate_init_data
from src.middleware.http_rate_limiter import HttpDDoSProtectionMiddleware
from src.services.token_service import token_service, UNLIMITED_TOKEN_COUNT
from src.services.map_service import build_google_maps_link
from src.services.optimizer_service import optimizeRoutePoints
from src.services.parser_service import get_attractions_osm
from src.services.routes_service import get_distance_osrm
from src.services.weather_service import (
    CityNotSelectedError,
    WeatherDTO,
    WeatherDaySummary,
    WeatherHourlyItem,
    get_city_selection_reminder,
    get_weather,
    is_city_missing,
)
from src.services.wiki_service import get_wikimedia_photo
from src.utils.languages import get_text
from src.utils.utils import error, info, log, logger

class RegionResponse(BaseModel): id:str; name:str; cities:List[str]
class CityResponse(BaseModel): name:str; region:str
class WeatherResponse(WeatherDTO):
    pass
class POIQuery(BaseModel):
    region: Optional[str] = None
    city: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    limit: int = 30
    offset: int = 0
    search: Optional[str] = None
    shuffle: Optional[str] = None
class POIResearchQuery(BaseModel):
    city: str
    region: Optional[str] = None
    scale: float = 2.5
class POI(BaseModel):
    id:str; name:str; city:str; region:str; address:str; category:str; lat:float; lon:float; hours:Optional[str]=None; phone:Optional[str]=None; image_url:Optional[str]=None; images:Optional[dict]=None
class POIDetail(POI): photo:Optional[dict]=None
class RouteRequest(BaseModel): poi_ids:List[str]; optimize:bool=True
class RouteResponse(BaseModel): poi_ids:List[str]; google_maps_url:str; total_distance_km:Optional[float]=None; optimized:bool
class FavoriteToggle(BaseModel): poi_id:str

app=FastAPI(title="JARVIS GEO-APP API",description="Backend for Belarus Travel Telegram Mini App",version="3.0.22102026")
app.mount("/media",StaticFiles(directory="media"),name="media")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
app.add_middleware(HttpDDoSProtectionMiddleware)
app.add_middleware(TelegramAuthMiddleware,bot_token=TOKEN,max_age=86400)
MAX_POI_LIMIT=30; DEFAULT_POI_LIMIT=30

def normalize_region_id(region_name:str)->str:return region_name.lower().replace(" область","").replace(" ","_")
CASTLE_KEYWORDS = (
    "замок", "замак", "крепость", "крепост", "крэпасць", "крэпасц", "форт",
    "цитадель", "цитадел", "цытадэль", "цытадэл", "бастион", "палац",
    "castle", "fortress", "fort", "fortification"
)
CHURCH_KEYWORDS = (
    "церк", "храм", "собор", "костел", "костёл", "касцёл", "касцел", "царква", "сабор",
    "монастыр", "манастыр", "капліца", "часовн", "синагог", "сінагог",
    "church", "cathedral", "place_of_worship", "monastery", "chapel", "synagogue"
)
MUSEUM_KEYWORDS = ("museum", "музей")
GALLERY_KEYWORDS = ("gallery", "галере")
VIEWPOINT_KEYWORDS = ("viewpoint", "смотров")
MONUMENT_KEYWORDS = ("monument", "памятник")
RUINS_KEYWORDS = ("ruins", "руины")
MANOR_KEYWORDS = ("manor", "усадь", "сядзіб")
THEME_PARK_KEYWORDS = ("theme_park", "аттракцион")
PARK_KEYWORDS = ("park", "парк", "сквер")
MEMORIAL_KEYWORDS = ("memorial", "мемориал")

def normalize_category(value: str = "", name: str = "") -> str:
    combined = f"{value or ''} {name or ''}".lower()
    if any(k in combined for k in CASTLE_KEYWORDS):
        return "castle"
    if any(k in combined for k in CHURCH_KEYWORDS):
        return "church"
    if any(k in combined for k in MUSEUM_KEYWORDS):
        return "museum"
    if any(k in combined for k in GALLERY_KEYWORDS):
        return "gallery"
    if any(k in combined for k in VIEWPOINT_KEYWORDS):
        return "viewpoint"
    if any(k in combined for k in MONUMENT_KEYWORDS):
        return "monument"
    if any(k in combined for k in RUINS_KEYWORDS):
        return "ruins"
    if any(k in combined for k in MANOR_KEYWORDS):
        return "manor"
    if any(k in combined for k in THEME_PARK_KEYWORDS):
        return "theme_park"
    if any(k in combined for k in PARK_KEYWORDS):
        return "park"
    if any(k in combined for k in MEMORIAL_KEYWORDS):
        return "memorial"
    return "misc"

TAG_CATEGORY_MAP = {
    "castle": {"castle"},
    "architecture": {"castle", "church", "monument", "manor", "ruins", "gallery"},
    "church": {"church"},
    "monument": {"monument", "memorial"},
    "nature": {"park", "viewpoint"},
    "museum": {"museum", "gallery"},
    "park": {"park", "theme_park"},
}
def expand_poi_tags(tags:list[str])->set[str]:
    categories=set()
    for tag in tags:
        key=str(tag or "").strip().lower();categories.update(TAG_CATEGORY_MAP.get(key,{normalize_category(key)}))
    return categories
def normalize_limit(value:int)->int:return min(max(value,1),MAX_POI_LIMIT)
def normalize_offset(value:int)->int:return max(value,0)

def _normalize_asset_url(url: str | None) -> str | None:
    if not url: return None
    url = url.strip()
    if url.startswith("http://localhost:8000"):
        url = url.replace("http://localhost:8000", "")
    elif url.startswith("http://127.0.0.1:8000"):
        url = url.replace("http://127.0.0.1:8000", "")
    elif url.startswith("http://"):
        url = "https://" + url[7:]
    return url

def _photo_images(photo:PlacePhoto|None)->dict|None:
    if not photo or photo.source == "blocked" or photo.original_url == "blocked":
        return None
    thumb=_normalize_asset_url(photo.local_url_thumb or photo.original_url)
    medium=_normalize_asset_url(photo.local_url_medium or photo.original_url)
    orig=_normalize_asset_url(photo.original_url)
    if thumb == "blocked" or orig == "blocked":
        return None
    return {"thumb":thumb,"medium":medium,"original":orig}
def place_to_dict(place:Place,photo:PlacePhoto|None=None)->dict:
    images=_photo_images(photo)
    return {"id":place.place_id,"name":place.name,"city":place.city,"region":place.region,"address":place.address or "","category":place.category,"lat":float(place.lat),"lon":float(place.lon),"hours":place.hours,"phone":place.phone,"image_url":images.get("thumb") if images else None,"images":images}
def photo_to_dict(photo:PlacePhoto|None)->Optional[dict]:
    if photo is None or photo.source == "blocked" or photo.original_url == "blocked":
        return None
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
    if photo:
        if photo.source == "blocked" or photo.original_url == "blocked":
            return None
        return photo
    try:
        photo_data=await get_wikimedia_photo(name=place.name,city=place.city,place_id=place.place_id,lat=place.lat,lon=place.lon,category=place.category)
        if not photo_data:return None
        return await photo_repo.save_place_photo(session,place_id=place.place_id,source=photo_data["source"],original_url=photo_data["original_url"],local_url_thumb=photo_data.get("local_url_thumb"),local_url_medium=photo_data.get("local_url_medium"),author=photo_data.get("author"),license=photo_data.get("license"))
    except Exception as exc:
        error(f"Photo hydration failed for {place.place_id}: {exc}")
        return None
GRAVE_WORDS = ("могила", "магіла", "кладбище", "могілк", "погребение")

async def get_places_from_db(
    session,
    *,
    region: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str | list[str] | set[str]] = None,
    search: Optional[str] = None,
    shuffle: Optional[str] = None,
    offset: int = 0,
    limit: int = MAX_POI_LIMIT,
) -> list[Place]:
    query = select(Place)
    if city and str(city).strip():
        query = query.where(func.lower(Place.city) == str(city).strip().lower())
    if region and str(region).strip():
        clean_reg = str(region).strip().lower().replace(" область", "").replace(" вобласць", "").strip()
        query = query.where(
            or_(
                func.lower(Place.region) == clean_reg,
                func.lower(Place.region) == str(region).strip().lower(),
                func.lower(Place.region).ilike(f"%{clean_reg}%"),
            )
        )
    if category:
        query = query.where(
            Place.category.in_(category)
            if isinstance(category, (list, set, tuple))
            else Place.category == category
        )
    if search and str(search).strip():
        term = f"%{str(search).strip()}%"
        query = query.where(or_(Place.name.ilike(term), Place.address.ilike(term)))

    if shuffle and str(shuffle).strip():
        query = query.order_by(func.md5(Place.place_id.op("||")(str(shuffle).strip())))
    else:
        order_criteria = []
        user_searching_grave = False
        if search and str(search).strip():
            s_lower = str(search).strip().lower()
            if any(w in s_lower for w in GRAVE_WORDS):
                user_searching_grave = True

        if not user_searching_grave:
            is_grave = case(
                (
                    or_(
                        Place.name.ilike("%могила%"),
                        Place.name.ilike("%магіла%"),
                        Place.name.ilike("%кладбище%"),
                        Place.name.ilike("%могілк%"),
                        Place.name.ilike("%погребение%"),
                    ),
                    1,
                ),
                else_=0,
            )
            order_criteria.append(is_grave.asc())

        category_priority = case(
            (Place.category == "castle", 1),
            (Place.category == "museum", 2),
            (Place.category == "church", 3),
            (Place.category == "park", 4),
            (Place.category == "viewpoint", 5),
            (Place.category.in_(["architecture", "monument", "gallery", "manor", "ruins"]), 6),
            (Place.category == "misc", 7),
            (Place.category == "memorial", 8),
            else_=7,
        )
        order_criteria.append(category_priority.asc())
        order_criteria.append(Place.name.asc())
        query = query.order_by(*order_criteria)

    result = await session.execute(query.offset(offset).limit(limit))
    return list(result.scalars().all())

async def get_place_by_id(session,place_id:str)->Optional[Place]:
    result=await session.execute(select(Place).where(Place.place_id==place_id).limit(1));return result.scalar_one_or_none()
async def upsert_osm_places(session,attractions:list[dict],*,city:str,region:str)->list[Place]:
    result=[]
    for attr in attractions:
        pid,name,lat,lon=attr.get("id"),attr.get("name"),attr.get("lat"),attr.get("lon")
        if not pid or not name or lat is None or lon is None:continue
        category=normalize_category(attr.get("type",""), name=name);existing=await session.execute(select(Place).where(Place.place_id==pid).limit(1));place=existing.scalar_one_or_none()
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
async def root():return {"status":"JARVIS GEO-APP API","version":"3.0.22102026"}
@app.get("/api/regions",response_model=List[RegionResponse])
async def get_regions():return [RegionResponse(id=normalize_region_id(n),name=n,cities=c) for n,c in REGIONS.items()]
@app.get("/api/cities/{region_id}",response_model=List[CityResponse])
async def get_cities(region_id:str):
    for name,cities in REGIONS.items():
        if normalize_region_id(name)==region_id:return [CityResponse(name=c,region=name) for c in cities]
    raise HTTPException(status_code=404,detail=get_text("choose_city_empty"))
def _extract_lang(request: Optional[Request] = None, lang_param: Optional[str] = None) -> str:
    if lang_param and lang_param.strip().lower() in ("by", "be", "ru"):
        return lang_param.strip().lower()
    if request:
        accept = request.headers.get("accept-language", "").lower()
        if "be" in accept or "by" in accept:
            return "by"
    return "ru"

@app.get("/api/weather", response_model=WeatherResponse)
@app.get("/api/weather/", response_model=WeatherResponse)
@app.get("/api/weather/{city}", response_model=WeatherResponse)
async def get_weather_endpoint(city: Optional[str] = None, request: Request = None, lang: Optional[str] = None):
    resolved_lang = _extract_lang(request, lang)
    if is_city_missing(city):
        weather = json.loads(await get_weather(city, lang=resolved_lang))
        return WeatherResponse(**{**weather, "cached": False})

    cached = await check_weather_cache(city)
    if cached:
        return WeatherResponse(**{**cached, "cached": True})
    try:
        weather = json.loads(await get_weather(city, lang=resolved_lang))
        if weather.get("temp") is not None:
            await set_weather_cache(city, weather)
        return WeatherResponse(**{**weather, "cached": False})
    except Exception as exc:
        error(f"Weather API error for {city}: {exc}")
        raise HTTPException(status_code=500, detail=get_text("internal_error"))

@app.post("/api/pois/query")
async def query_pois(query:POIQuery):
    if not query.city and not query.region and not query.search:
        raise HTTPException(status_code=400,detail="City, region, or search required")
    limit,offset=normalize_limit(query.limit),normalize_offset(query.offset);cats=expand_poi_tags(query.tags) if query.tags else None
    search=query.search.strip() if query.search else None
    shuffle=str(query.shuffle).strip() if query.shuffle else None
    async with AsyncSessionLocal() as session:
        places=await get_places_from_db(session,region=query.region,city=query.city,category=cats,search=search,shuffle=shuffle,offset=offset,limit=limit)
        if not places and offset==0 and query.city:
            city_count = await session.scalar(
                select(func.count(Place.id)).where(func.lower(Place.city) == query.city.strip().lower())
            )
            if not city_count:
                osm = await get_attractions_osm(query.city, limit=500)
                if osm:
                    await upsert_osm_places(session, osm, city=query.city, region=query.region or "")
                    await session.commit()
                    places = await get_places_from_db(session, region=query.region, city=query.city, category=cats, search=search, shuffle=shuffle, offset=offset, limit=limit)
        if not places and query.city and not search and not places:
            places=await get_places_from_db(session,city=query.city,category=cats,search=search,shuffle=shuffle,offset=offset,limit=limit)
        photos=await get_photos_map(session,[p.place_id for p in places])
        pois=[place_to_dict(p,photos.get(p.place_id)) for p in places]
        await session.commit();return {"count":len(pois),"region":query.region,"city":query.city,"tags":query.tags,"search":search,"shuffle":shuffle,"offset":offset,"limit":limit,"pois":pois}

@app.post("/api/pois/research")
async def research_pois(query: POIResearchQuery):
    if not query.city:
        raise HTTPException(status_code=400, detail="City required")
    city_clean = query.city.strip()
    scale = min(max(query.scale, 1.2), 4.0)

    async with AsyncSessionLocal() as session:
        stmt = select(Place.place_id, func.lower(Place.name)).where(
            func.lower(Place.city) == city_clean.lower()
        )
        res = await session.execute(stmt)
        rows = res.all()
        existing_ids = {r[0] for r in rows}
        existing_names = {r[1] for r in rows if r[1]}

        osm = await get_attractions_osm(city_clean, limit=500, bbox_scale=scale)
        new_attractions = [
            attr for attr in osm
            if attr.get("id") not in existing_ids and attr.get("name", "").strip().lower() not in existing_names
        ]

        if new_attractions:
            await upsert_osm_places(session, new_attractions, city=city_clean, region=query.region or "")
            await session.commit()

        total_in_db = await session.scalar(
            select(func.count(Place.id)).where(func.lower(Place.city) == city_clean.lower())
        )

        return {
            "city": city_clean,
            "found_in_surroundings": len(osm),
            "new_added": len(new_attractions),
            "total_places": total_in_db or 0,
        }

@app.get("/api/pois")
async def get_all_pois(region:Optional[str]=None,city:Optional[str]=None,category:Optional[str]=None,search:Optional[str]=None,shuffle:Optional[str]=None,offset:int=0,limit:int=30):
    limit,offset=normalize_limit(limit),normalize_offset(offset)
    async with AsyncSessionLocal() as session:
        places=await get_places_from_db(session,region=region,city=city,category=normalize_category(category) if category else None,search=search,shuffle=shuffle,offset=offset,limit=limit)
        for place in places:await ensure_place_photo(session,place)
        photos=await get_photos_map(session,[p.place_id for p in places]);await session.commit();return {"pois":[place_to_dict(p,photos.get(p.place_id)) for p in places],"count":len(places),"offset":offset,"limit":limit,"search":search,"shuffle":shuffle}
@app.get("/api/pois/{place_id}",response_model=POIDetail)
async def get_poi_detail(place_id:str):
    async with AsyncSessionLocal() as session:
        place=await get_place_by_id(session,place_id)
        if place is None:raise HTTPException(status_code=404,detail="Place not found")
        photo=await ensure_place_photo(session,place);await session.commit();return POIDetail(**place_to_dict(place,photo),photo=photo_to_dict(photo))
@app.get("/api/pois/{place_id}/photos")
async def get_poi_photos(place_id:str):
    async with AsyncSessionLocal() as session:
        if await get_place_by_id(session,place_id) is None:raise HTTPException(status_code=404,detail="Place not found")
        result=await session.execute(select(PlacePhoto).where(PlacePhoto.place_id==place_id).order_by(PlacePhoto.id.asc()));return {"place_id":place_id,"photos":[photo_to_dict(p) for p in result.scalars().all()]}

@app.post("/api/route/build",response_model=RouteResponse)
async def build_route(req:RouteRequest, request: Request = None):
    ids=list(dict.fromkeys(x for x in req.poi_ids if x))
    if len(ids)<2:raise HTTPException(status_code=400,detail="Need at least 2 unique points")

    uid = getattr(request.state, "telegram_user_id", None) if request and hasattr(request, "state") else None
    if uid:
        allowed, rem = await token_service.consume_tokens(uid, cost=1)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Дневной лимит токенов исчерпан. Токены обновляются раз в сутки.",
            )

    async with AsyncSessionLocal() as session:
        result=await session.execute(select(Place).where(Place.place_id.in_(ids)))
        places=list(result.scalars().all())
    by_id={p.place_id:p for p in places}
    points=[{"id":i,"lat":float(by_id[i].lat),"lon":float(by_id[i].lon),"name":by_id[i].name} for i in ids if i in by_id and by_id[i].lat is not None and by_id[i].lon is not None]
    if len(points)<2:
        if uid: await token_service.refund_tokens(uid, 1)
        raise HTTPException(status_code=400,detail="Need at least 2 points with coordinates")
    if req.optimize:points=optimizeRoutePoints(points)
    url=build_google_maps_link(points)
    if not url:
        if uid: await token_service.refund_tokens(uid, 1)
        raise HTTPException(status_code=500,detail="Unable to build Google Maps route")
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
async def get_favorites(request:Request,page:Optional[int]=None,page_size:int=8,limit:Optional[int]=None,offset:Optional[int]=None):
    uid=request.state.telegram_user_id
    async with AsyncSessionLocal() as session:
        if page is not None or limit is not None:
            l=limit if limit is not None else page_size
            o=offset if offset is not None else (max(page,0)*l if page is not None else 0)
            count_res=await session.execute(select(func.count(Favorite.id)).where(Favorite.user_id==uid))
            total=count_res.scalar_one_or_none() or 0
            stmt=select(Favorite).where(Favorite.user_id==uid).order_by(Favorite.created_at.desc()).offset(o).limit(l)
            r=await session.execute(stmt);favorites=r.scalars().all()
            pages=(total+l-1)//l if l>0 else 1
            has_next=(o+len(favorites))<total
            return {"user_id":uid,"favorites":[{"id":f.id,"place_id":f.place_id,"place_name":f.place_name,"address":f.address,"lat":f.lat,"lon":f.lon} for f in favorites],"total":total,"page":page if page is not None else (o//l if l>0 else 0),"page_size":l,"pages":pages,"has_next":has_next}
        else:
            r=await session.execute(select(Favorite).where(Favorite.user_id==uid).order_by(Favorite.created_at.desc()));favorites=r.scalars().all()
            return {"user_id":uid,"favorites":[{"id":f.id,"place_id":f.place_id,"place_name":f.place_name,"address":f.address,"lat":f.lat,"lon":f.lon} for f in favorites],"total":len(favorites),"page":0,"page_size":len(favorites),"pages":1,"has_next":False}
@app.get("/health")
async def health():return {"status":"ok","timestamp":datetime.utcnow().isoformat()}
@app.post("/api/auth/telegram")
async def auth_telegram(request:Request):
    mock_auth = os.getenv("MOCK_AUTH") == "1" or os.getenv("JARVIS_MOCK_AUTH") == "1"
    authorization=request.headers.get("Authorization","")
    if mock_auth and (not authorization.startswith("tma ") or authorization == "tma mock_auth"):
        user_data = {"id": 999999999, "username": "mock_admin", "first_name": "Admin"}
    else:
        if not authorization.startswith("tma "):
            if mock_auth:
                user_data = {"id": 999999999, "username": "mock_admin", "first_name": "Admin"}
            else:
                raise HTTPException(status_code=401,detail="Telegram authentication required")
        else:
            try:
                user_data=validate_init_data(authorization[4:].strip(),TOKEN,max_age=86400)
            except TelegramAuthError as exc:
                if mock_auth:
                    user_data = {"id": 999999999, "username": "mock_admin", "first_name": "Admin"}
                else:
                    raise HTTPException(status_code=401,detail=str(exc)) from exc
    uid=int(user_data["id"]);username=user_data.get("username","")
    async with AsyncSessionLocal() as session:
        r=await session.execute(select(User).where(User.user_id==uid));user=r.scalar_one_or_none();new=user is None
        if new:user=User(user_id=uid,username=username);session.add(user)
        else:user.username=username
        await session.commit()
    tokens = await token_service.get_token_balance(uid)
    return {"user_id":uid,"username":username,"is_new":new,"tokens":tokens}

@app.get("/api/tokens/balance")
async def get_my_tokens(request: Request):
    uid = getattr(request.state, "telegram_user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    balance = await token_service.get_token_balance(uid)
    return {
        "user_id": uid,
        "tokens": balance,
        "daily_quota": token_service.default_quota,
        "is_unlimited": balance >= UNLIMITED_TOKEN_COUNT,
    }

if __name__=="__main__":
    import uvicorn;uvicorn.run(app,host="0.0.0.0",port=8000)
