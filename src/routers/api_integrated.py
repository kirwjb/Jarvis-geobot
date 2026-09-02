import json
import math
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import delete, select

from src.config import REGIONS, DEFAULT_LIMIT
from src.database.db import AsyncSessionLocal
from src.database.models import User, OsmCache, Favorite
from src.database.session_manager import redis_client
from src.services.parser_service import (
    get_attractions_osm,
    get_city_coords,
)
from src.services.weather_service import get_weather
from src.services.optimizer_service import optimizeRoutePoints
from src.services.map_service import build_google_maps_link
from src.utils.languages import get_text
from src.utils.utils import log, error


# ============================================================
# RESPONSE MODELS
# ============================================================

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


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="JARVIS GEO-APP API",
    description="Backend for Belarus Travel Telegram Mini App",
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def normalize_region_id(region_name: str) -> str:
    return (
        region_name
        .lower()
        .replace(" область", "")
        .replace(" ", "_")
    )


def normalize_category(value: str) -> str:

    value = value.lower()

    if "castle" in value or "замок" in value:
        return "castle"

    if (
        "church" in value
        or "cathedral" in value
        or "церк" in value
        or "собор" in value
        or "храм" in value
    ):
        return "church"

    if "museum" in value or "музей" in value:
        return "museum"

    if "monument" in value or "памятник" in value:
        return "monument"

    if "park" in value or "парк" in value:
        return "park"

    return "misc"


# ============================================================
# WEATHER CACHE
# ============================================================

async def check_weather_cache(
    city: str,
) -> Optional[dict]:

    cache_key = f"weather:{city}"

    cached = await redis_client.get(cache_key)

    if not cached:
        return None

    try:
        data = json.loads(cached)
        timestamp = datetime.fromisoformat(
            data["timestamp"]
        )

        if timestamp > datetime.utcnow() - timedelta(
            minutes=30
        ):
            return data

    except (
        json.JSONDecodeError,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:

        error(
            f"Ошибка чтения weather cache "
            f"для {city}: {exc}"
        )

    return None


async def set_weather_cache(
    city: str,
    data: dict,
) -> None:

    cache_key = f"weather:{city}"

    cache_data = {
        **data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    await redis_client.setex(
        cache_key,
        1800,
        json.dumps(
            cache_data,
            ensure_ascii=False,
        ),
    )


# ============================================================
# OSM CACHE
# ============================================================

async def get_cached_osm(
    city: str,
) -> Optional[list[dict]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(OsmCache)
            .where(OsmCache.city == city)
        )

        items = result.scalars().all()

        if not items:
            return None

        return [
            {
                "id": item.id,
                "name": item.name,
                "address": item.address,
                "lat": item.lat,
                "lon": item.lon,
                "sights_data": item.sights_data,
            }
            for item in items
        ]


async def save_to_osm_cache(
    city: str,
    attractions: list[dict],
) -> None:

    async with AsyncSessionLocal() as session:

        for attr in attractions:

            cache_entry = OsmCache(
                city=city,
                name=attr.get("name"),
                address=attr.get("address"),
                lat=attr.get("lat"),
                lon=attr.get("lon"),
                sights_data=json.dumps(
                    attr,
                    ensure_ascii=False,
                ),
            )

            session.add(cache_entry)

        await session.commit()


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "JARVIS GEO-APP API",
        "version": "2.0.0",
    }


# ============================================================
# REGIONS
# ============================================================

@app.get(
    "/api/regions",
    response_model=List[RegionResponse],
)
async def get_regions():

    result = []

    for region_name, cities in REGIONS.items():

        result.append(
            RegionResponse(
                id=normalize_region_id(region_name),
                name=region_name,
                cities=cities,
            )
        )

    return result


@app.get(
    "/api/cities/{region_id}",
    response_model=List[CityResponse],
)
async def get_cities(
    region_id: str,
):

    for region_name, cities in REGIONS.items():

        if normalize_region_id(region_name) == region_id:

            return [
                CityResponse(
                    name=city,
                    region=region_name,
                )
                for city in cities
            ]

    raise HTTPException(
        status_code=404,
        detail=get_text("choose_city_empty"),
    )


# ============================================================
# WEATHER
# ============================================================

@app.get(
    "/api/weather/{city}",
    response_model=WeatherResponse,
)
async def get_weather_endpoint(
    city: str,
):

    cached = await check_weather_cache(city)

    if cached:

        return WeatherResponse(
            city=city,
            description=cached.get(
                "description",
                "",
            ),
            cached=True,
        )

    try:

        weather_text = await get_weather(city)

        await set_weather_cache(
            city,
            {
                "description": weather_text,
            },
        )

        return WeatherResponse(
            city=city,
            description=weather_text,
            cached=False,
        )

    except Exception as exc:

        error(
            f"Weather API error for {city}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=get_text("internal_error"),
        )


# ============================================================
# POIS
# ============================================================

@app.post("/api/pois/query")
async def query_pois(
    query: POIQuery,
):

    if not query.city:

        raise HTTPException(
            status_code=400,
            detail="City required",
        )

    limit = min(
        max(query.limit, 1),
        DEFAULT_LIMIT,
    )

    cached = await get_cached_osm(
        query.city
    )

    if cached:

        log(
            f"OSM cache hit for {query.city}: "
            f"{len(cached)} items"
        )

        attractions = []

        for item in cached:

            raw_data = item.get(
                "sights_data"
            )

            if not raw_data:
                continue

            try:
                attr = json.loads(raw_data)

            except json.JSONDecodeError:

                error(
                    "Некорректный JSON в OSM cache: "
                    f"{item.get('id')}"
                )

                continue

            if query.tags:

                attr_type = attr.get(
                    "type",
                    "",
                ).lower()

                if not any(
                    tag.lower() in attr_type
                    for tag in query.tags
                ):
                    continue

            attractions.append(attr)

    else:

        log(
            f"Fetching OSM data for {query.city}"
        )

        attractions = await get_attractions_osm(
            city=query.city,
            limit=limit,
        )

        if attractions:

            await save_to_osm_cache(
                query.city,
                attractions,
            )

    pois = []

    for attr in attractions[:limit]:

        if not attr.get("id"):
            continue

        if not attr.get("name"):
            continue

        if attr.get("lat") is None:
            continue

        if attr.get("lon") is None:
            continue

        pois.append(
            POI(
                id=attr["id"],
                name=attr["name"],
                city=query.city,
                region=query.region,
                address=attr.get(
                    "address",
                    "",
                ),
                category=normalize_category(
                    attr.get("type", "")
                ),
                lat=attr["lat"],
                lon=attr["lon"],
                hours=attr.get("hours"),
                phone=attr.get("phone"),
                image_url=None,
            )
        )

    return {
        "count": len(pois),
        "region": query.region,
        "city": query.city,
        "tags": query.tags,
        "pois": [
            poi.model_dump()
            for poi in pois
        ],
    }


@app.get("/api/pois")
async def get_all_pois(
    region: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
):

    limit = max(limit, 1)

    async with AsyncSessionLocal() as session:

        query = select(OsmCache)

        if city:
            query = query.where(
                OsmCache.city == city
            )

        result = await session.execute(query)

        items = result.scalars().all()

    pois = []

    for item in items[:limit]:

        if not item.sights_data:
            continue

        try:
            data = json.loads(
                item.sights_data
            )

        except json.JSONDecodeError:

            error(
                f"Некорректный JSON OSM cache: "
                f"{item.id}"
            )

            continue

        if category:

            current_category = normalize_category(
                data.get("type", "")
            )

            if current_category != category:
                continue

        pois.append(data)

    return {
        "pois": pois,
        "count": len(pois),
    }


# ============================================================
# ROUTES
# ============================================================

@app.post(
    "/api/route/build",
    response_model=RouteResponse,
)
async def build_route(
    req: RouteRequest,
):

    if len(req.poi_ids) < 2:

        raise HTTPException(
            status_code=400,
            detail=get_text(
                "min_points_error",
                count=len(req.poi_ids),
            ),
        )

    route_points = []

    async with AsyncSessionLocal() as session:

        for poi_id in req.poi_ids:

            if not poi_id:
                continue

            result = await session.execute(
                select(OsmCache)
                .where(
                    OsmCache.sights_data.contains(
                        f'"id": "{poi_id}"'
                    )
                )
            )

            item = result.scalar_one_or_none()

            if not item:
                continue

            if item.lat is None or item.lon is None:
                continue

            route_points.append(
                {
                    "lat": item.lat,
                    "lon": item.lon,
                    "name": item.name or "",
                }
            )

    if len(route_points) < 2:

        raise HTTPException(
            status_code=400,
            detail="Need at least 2 points with coordinates",
        )

    if req.optimize:
        optimized = optimizeRoutePoints(
            route_points
        )
    else:
        optimized = route_points

    google_url = build_google_maps_link(
        optimized
    )

    total_km = 0.0

    for index in range(
        len(optimized) - 1
    ):

        lat1 = optimized[index]["lat"]
        lon1 = optimized[index]["lon"]

        lat2 = optimized[index + 1]["lat"]
        lon2 = optimized[index + 1]["lon"]

        dx = (
            math.radians(lon2 - lon1)
            * math.cos(
                math.radians(
                    (lat1 + lat2) / 2
                )
            )
            * 111.32
        )

        dy = (
            math.radians(lat2 - lat1)
            * 111.32
        )

        total_km += math.sqrt(
            dx ** 2 + dy ** 2
        )

    return RouteResponse(
        poi_ids=req.poi_ids,
        google_maps_url=google_url,
        total_distance_km=round(
            total_km,
            1,
        ),
        optimized=req.optimize,
    )


# ============================================================
# FAVORITES
# ============================================================

@app.post("/api/favorites/toggle")
async def toggle_favorite(
    data: FavoriteToggle,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Favorite).where(
                Favorite.user_id == data.user_id,
                Favorite.place_id == data.poi_id,
            )
        )

        existing = result.scalar_one_or_none()

        if existing:

            await session.execute(
                delete(Favorite).where(
                    Favorite.id == existing.id
                )
            )

            await session.commit()

            return {
                "poi_id": data.poi_id,
                "user_id": data.user_id,
                "favorited": False,
            }

        result = await session.execute(
            select(OsmCache)
            .where(
                OsmCache.sights_data.contains(
                    f'"id": "{data.poi_id}"'
                )
            )
        )

        place = result.scalar_one_or_none()

        if not place:

            raise HTTPException(
                status_code=404,
                detail="Place not found",
            )

        favorite = Favorite(
            user_id=data.user_id,
            place_id=data.poi_id,
            place_name=place.name or "",
            address=place.address or "",
            lat=place.lat or 0.0,
            lon=place.lon or 0.0,
        )

        session.add(favorite)

        await session.commit()

        return {
            "poi_id": data.poi_id,
            "user_id": data.user_id,
            "favorited": True,
        }


@app.get("/api/favorites/{user_id}")
async def get_favorites(
    user_id: int,
):

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Favorite)
            .where(
                Favorite.user_id == user_id
            )
        )

        favorites = result.scalars().all()

    return {
        "user_id": user_id,
        "favorites": [
            {
                "id": favorite.id,
                "place_id": favorite.place_id,
                "place_name": favorite.place_name,
                "address": favorite.address,
                "lat": favorite.lat,
                "lon": favorite.lon,
            }
            for favorite in favorites
        ],
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================
# TELEGRAM AUTH
# ============================================================

@app.post("/api/auth/telegram")
async def auth_telegram(
    request: Request,
):

    data = await request.json()

    init_data = data.get(
        "initData",
        "",
    )

    if "user=" not in init_data:

        raise HTTPException(
            status_code=401,
            detail="Invalid initData",
        )

    try:

        import urllib.parse

        parsed = urllib.parse.parse_qs(
            init_data
        )

        user_json = parsed.get(
            "user",
            ["{}"],
        )[0]

        user_data = json.loads(
            user_json
        )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:

        error(
            f"Ошибка разбора Telegram initData: "
            f"{exc}"
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid initData",
        )

    user_id = user_data.get("id")

    if not user_id:

        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram user",
        )

    username = user_data.get(
        "username",
        "",
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(User)
            .where(
                User.user_id == user_id
            )
        )

        user = result.scalar_one_or_none()

        is_new = user is None

        if is_new:

            user = User(
                user_id=user_id,
                username=username,
            )

            session.add(user)

        else:

            user.username = username

        await session.commit()

        return {
            "user_id": user.user_id,
            "username": user.username,
            "is_new": is_new,
            "tokens": user.tokens,
        }


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )