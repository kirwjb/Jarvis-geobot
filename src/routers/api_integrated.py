from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import hashlib
from datetime import datetime, timedelta
import asyncio

from src.config import REGIONS, LIMITS, DEFAULT_LIMIT, DEFAULT_LANGUAGE
from src.database.db import AsyncSessionLocal, get_db_session
from src.database.models import User, OsmCache, Favorite, History
from src.database.session_manager import user_sessions, redis_client
from src.services.parser_service import get_attractions_osm, get_city_coords
from src.services.weather_service import get_weather
from src.services.optimizer_service import optimizeRoutePoints
from src.services.map_service import build_google_maps_link
from src.utils.languages import get_text
from src.utils.utils import log, error, logger



class RegionResponse(BaseModel):
    id: str
    name: str
    cities: List[str]

class CityResponse(BaseModel):
    name: str
    region: str

class WeatherResponse(BaseModel):
    city: str
    temp: Optional[float] = None
    description: str
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    pressure: Optional[int] = None
    cached: bool = False

class POIQuery(BaseModel):
    region: str
    city: Optional[str] = None
    tags: List[str] = []
    limit: int = 15

class POI(BaseModel):
    id: str
    name: str
    city: str
    region: str
    address: str
    category: str
    rating: float
    lat: float
    lon: float
    hours: Optional[str] = None
    phone: Optional[str] = None
    image_url: Optional[str] = None

class RouteRequest(BaseModel):
    poi_ids: List[str]
    optimize: bool = True

class RouteResponse(BaseModel):
    poi_ids: List[str]
    google_maps_url: str
    total_distance_km: Optional[float] = None
    optimized: bool

class FavoriteToggle(BaseModel):
    user_id: int
    poi_id: str

class FavoriteList(BaseModel):
    user_id: int


app = FastAPI(
    title="JARVIS GEO-APP API",
    description="Backend for Belarus Travel Telegram Mini App",
    version="2.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db():
  
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def check_weather_cache(city: str):
  
    cache_key = f"weather:{city}"
    cached = await redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        if datetime.fromisoformat(data["timestamp"]) > datetime.utcnow() - timedelta(minutes=30):
            return data
    return None

async def set_weather_cache(city: str, data: dict):
   
    cache_key = f"weather:{city}"
    data["timestamp"] = datetime.utcnow().isoformat()
    await redis_client.setex(cache_key, 1800, json.dumps(data))

async def get_cached_osm(city: str, category: str = None):
  
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        query = select(OsmCache).where(OsmCache.city == city)
        result = await session.execute(query)
        cached = result.scalars().all()
        if cached:
            return [{
                "id": c.id,
                "name": c.name,
                "address": c.address,
                "lat": c.lat,
                "lon": c.lon,
                "sights_data": c.sights_data
            } for c in cached]
    return None

async def save_to_osm_cache(city: str, attractions: list):
    async with AsyncSessionLocal() as session:
        for attr in attractions:
            cache_entry = OsmCache(
                city=city,
                name=attr.get("name"),
                address=attr.get("address"),
                lat=attr.get("lat"),
                lon=attr.get("lon"),
                sights_data=json.dumps(attr, ensure_ascii=False)
            )
            session.add(cache_entry)
        await session.commit()


@app.get("/")
async def root():
    return {"status": "JARVIS GEO-APP API", "version": "2.0.0"}


@app.get("/api/regions", response_model=List[RegionResponse])
async def get_regions():

    result = []
    for region_name, cities in REGIONS.items():
        region_id = region_name.lower().replace(" область", "").replace(" ", "_")
        result.append(RegionResponse(
            id=region_id,
            name=region_name,
            cities=cities
        ))
    return result


@app.get("/api/cities/{region_id}", response_model=List[CityResponse])
async def get_cities(region_id: str):

    for region_name, cities in REGIONS.items():
        rid = region_name.lower().replace(" область", "").replace(" ", "_")
        if rid == region_id:
            return [CityResponse(name=c, region=region_name) for c in cities]
    raise HTTPException(status_code=404, detail=get_text("choose_city_empty"))

@app.get("/api/weather/{city}", response_model=WeatherResponse)
async def get_weather_endpoint(city: str):

    cached = await check_weather_cache(city)
    if cached:
        return WeatherResponse(
            city=city,
            description=cached.get("description", ""),
            cached=True
        )
 
    try:
        weather_text = await get_weather(city)
    
        result = WeatherResponse(
            city=city,
            description=weather_text,
            cached=False
        )
        
       
        await set_weather_cache(city, {"description": weather_text})
        
        return result
    except Exception as e:
        error(f"Weather API error for {city}: {e}")
        raise HTTPException(status_code=500, detail=get_text("internal_error"))


@app.post("/api/pois/query")
async def query_pois(query: POIQuery):
  
    if not query.city:
        raise HTTPException(status_code=400, detail="City required")
    

    limit = LIMITS.get(query.city, DEFAULT_LIMIT)
    if query.limit:
        limit = min(query.limit, limit)
    
   
    cached = await get_cached_osm(query.city)
    
    if cached and len(cached) > 0:
        log(f"OSM cache hit for {query.city}: {len(cached)} items")
 
        attractions = []
        for item in cached:
            if item["sights_data"]:
                attr = json.loads(item["sights_data"])
         
                if query.tags:
                    attr_type = attr.get("type", "").lower()
                    tag_match = any(t.lower() in attr_type for t in query.tags)
                    if not tag_match:
                        continue
                attractions.append(attr)
    else:

        log(f"Fetching OSM data for {query.city}")
        attractions = await get_attractions_osm(
            city=query.city,
            category=None,  
            limit=limit
        )
        
        
        if attractions:
            await save_to_osm_cache(query.city, attractions)
    
    
    pois = []
    for attr in attractions[:limit]:
 
        cat = attr.get("type", "misc").lower()
        if "castle" in cat or "замок" in cat:
            category = "castle"
        elif "church" in cat or "cathedral" in cat or "храм" in cat:
            category = "church"
        elif "museum" in cat or "музей" in cat:
            category = "museum"
        elif "monument" in cat or "памятник" in cat:
            category = "monument"
        elif "park" in cat or "парк" in cat or "nature" in cat:
            category = "park"
        elif "architecture" in cat or "building" in cat:
            category = "architecture"
        else:
            category = "misc"
        
        pois.append(POI(
            id=attr.get("id", ""),
            name=attr.get("name", get_text("no_name")),
            city=query.city,
            region=query.region,
            address=attr.get("address", get_text("no_address")),
            category=category,
            rating=attr.get("rating", 3.5),
            lat=attr.get("lat", 0.0),
            lon=attr.get("lon", 0.0),
            hours=attr.get("hours"),
            phone=attr.get("phone"),
            image_url=attr.get("image_url")
        ))
    
    return {
        "count": len(pois),
        "region": query.region,
        "city": query.city,
        "tags": query.tags,
        "pois": [p.model_dump() for p in pois]
    }


@app.get("/api/pois")
async def get_all_pois(
    region: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
):
  
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        query = select(OsmCache)
        if city:
            query = query.where(OsmCache.city == city)
        result = await session.execute(query)
        items = result.scalars().all()
        
        pois = []
        for item in items[:limit]:
            if item.sights_data:
                data = json.loads(item.sights_data)
                pois.append(data)
        
        return {"pois": pois, "count": len(pois)}

@app.post("/api/route/build", response_model=RouteResponse)
async def build_route(req: RouteRequest):

    if len(req.poi_ids) < 2:
        raise HTTPException(status_code=400, detail=get_text("min_points_error", count=len(req.poi_ids)))
    

    route_points = []
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        for poi_id in req.poi_ids:
            query = select(OsmCache).where(OsmCache.id == int(poi_id) if poi_id.isdigit() else 0)
            result = await session.execute(query)
            item = result.scalar_one_or_none()
            if item and item.lat and item.lon:
                route_points.append({
                    "lat": item.lat,
                    "lon": item.lon,
                    "name": item.name or ""
                })
    
    if len(route_points) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 points with coordinates")
    
    if req.optimize:
        optimized = optimizeRoutePoints(route_points)
    else:
        optimized = route_points
  
    google_url = build_google_maps_link(optimized)
    
   
    total_km = 0.0
    for i in range(len(optimized) - 1):
        lat1, lon1 = optimized[i]["lat"], optimized[i]["lon"]
        lat2, lon2 = optimized[i + 1]["lat"], optimized[i + 1]["lon"]
        
        import math
        dx = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2)) * 111.32
        dy = math.radians(lat2 - lat1) * 111.32
        total_km += math.sqrt(dx**2 + dy**2)
    
    return RouteResponse(
        poi_ids=req.poi_ids,
        google_maps_url=google_url,
        total_distance_km=round(total_km, 1),
        optimized=req.optimize
    )


@app.post("/api/favorites/toggle")
async def toggle_favorite(data: FavoriteToggle):

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, delete
        
        query = select(Favorite).where(
            Favorite.user_id == data.user_id,
            Favorite.place_id == data.poi_id
        )
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            await session.execute(
                delete(Favorite).where(Favorite.id == existing.id)
            )
            await session.commit()
            return {"poi_id": data.poi_id, "user_id": data.user_id, "favorited": False}
        else:
            new_fav = Favorite(
                user_id=data.user_id,
                place_id=data.poi_id,
                place_name="",  
                address="",
                lat=0.0,
                lon=0.0
            )
            session.add(new_fav)
            await session.commit()
            return {"poi_id": data.poi_id, "user_id": data.user_id, "favorited": True}

@app.get("/api/favorites/{user_id}")
async def get_favorites(user_id: int):
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        query = select(Favorite).where(Favorite.user_id == user_id)
        result = await session.execute(query)
        favs = result.scalars().all()
        return {
            "user_id": user_id,
            "favorites": [
                {
                    "id": f.id,
                    "place_id": f.place_id,
                    "place_name": f.place_name,
                    "address": f.address,
                    "lat": f.lat,
                    "lon": f.lon
                } for f in favs
            ]
        }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/auth/telegram")
async def auth_telegram(request: Request):

    data = await request.json()
    init_data = data.get("initData", "")
    
    
    if "user=" in init_data:
        import urllib.parse
        parsed = urllib.parse.parse_qs(init_data)
        user_json = parsed.get("user", ["{}"])[0]
        user_data = json.loads(urllib.parse.unquote(user_json))
        
        user_id = user_data.get("id")
        username = user_data.get("username", "")
        
        # Создаём/обновляем пользователя
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            query = select(User).where(User.user_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(user_id=user_id, username=username)
                session.add(user)
                await session.commit()
            
            return {
                "user_id": user_id,
                "username": username,
                "is_new": user is None,
                "tokens": user.tokens if user else 5
            }
    
    raise HTTPException(status_code=401, detail="Invalid initData")


if __name__ == "__main__":
    import uvicorn
