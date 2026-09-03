# api_integrated.py
"""
Основной API-слой приложения.

Изменения по фотографиям:
- Модель POI теперь содержит поле images (dict с thumb/medium).
- place_to_dict возвращает и image_url (для обратной совместимости), и images.
- ensure_place_photo использует photo_repo.save_place_photo для консистентности.
- Все эндпоинты отдают оптимизированные ссылки на изображения.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from src.config import REGIONS
from src.database.db import AsyncSessionLocal
from src.database.models import Favorite, Place, PlacePhoto, User
from src.database.session_manager import redis_client
from src.database.repositories import photo_repo
from src.services.map_service import build_google_maps_link
from src.services.optimizer_service import optimizeRoutePoints
from src.services.parser_service import get_attractions_osm
from src.services.routes_service import get_distance_osrm
from src.services.weather_service import get_weather
from src.services.wiki_service import get_wikimedia_photo
from src.utils.languages import get_text
from src.utils.utils import error, info, log, logger


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
    tags: List[str] = Field(default_factory=list)
    limit: int = 30
    offset: int = 0


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
    # Для обратной совместимости оставляем image_url.
    image_url: Optional[str] = None
    # Новый формат: {"thumb": "...", "medium": "..."}
    images: Optional[dict] = None


class POIDetail(POI):
    photo: Optional[dict] = None


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
    version="2.2.0",
)
app.mount("/media", StaticFiles(directory="media"), name="media")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================
MAX_POI_LIMIT = 30
DEFAULT_POI_LIMIT = 30


def normalize_region_id(region_name: str) -> str:
    return (
        region_name.lower()
        .replace(" область", "")
        .replace(" ", "_")
    )


def normalize_category(value: str) -> str:
    value = (value or "").lower()
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
    if "gallery" in value or "галере" in value:
        return "gallery"
    if "viewpoint" in value or "смотров" in value:
        return "viewpoint"
    if "memorial" in value or "мемориал" in value:
        return "memorial"
    if "ruins" in value or "руины" in value:
        return "ruins"
    if "manor" in value or "усадь" in value:
        return "manor"
    if "theme_park" in value or "аттракцион" in value:
        return "theme_park"
    return "misc"


def normalize_limit(value: int) -> int:
    return min(max(value, 1), MAX_POI_LIMIT)


def normalize_offset(value: int) -> int:
    return max(value, 0)


def _photo_images(photo: PlacePhoto | None) -> dict | None:
    """Формирует словарь ссылок на изображения из записи БД."""
    if not photo:
        return None
    return {
        "thumb": photo.local_url_thumb,
        "medium": photo.local_url_medium,
    }


def place_to_dict(
    place: Place,
    photo: PlacePhoto | None = None,
) -> dict:
    """
    Сериализует место для ответа клиенту.

    Возвращает:
    - image_url: ссылка на thumb (для совместимости со старым фронтом);
    - images: словарь {thumb, medium} для нового фронта.
    """
    images = _photo_images(photo)
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
        "image_url": images.get("thumb") if images else None,
        "images": images,
    }


def photo_to_dict(photo: PlacePhoto | None) -> Optional[dict]:
    """Полная информация о фотографии для детальной карточки."""
    if photo is None:
        return None
    return {
        "source": photo.source,
        "original_url": photo.original_url,
        "local_url_thumb": photo.local_url_thumb,
        "local_url_medium": photo.local_url_medium,
        "author": photo.author,
        "license": photo.license,
    }


async def get_photos_map(
    session,
    place_ids: list[str],
) -> dict[str, PlacePhoto]:
    """
    Загружает фотографии для списка мест одним запросом.
    Возвращает маппинг place_id -> PlacePhoto.
    """
    if not place_ids:
        return {}
    result = await session.execute(
        select(PlacePhoto)
        .where(PlacePhoto.place_id.in_(place_ids))
        .order_by(PlacePhoto.id.asc())
    )
    photos = result.scalars().all()
    result_map: dict[str, PlacePhoto] = {}
    for photo in photos:
        if photo.place_id not in result_map:
            result_map[photo.place_id] = photo
    return result_map


async def ensure_place_photo(
    session,
    place: Place,
) -> PlacePhoto | None:
    """
    Гарантирует, что у места есть фотография.
    Если фото ещё нет — пытается получить его из Wikimedia Commons.
    """
    result = await session.execute(
        select(PlacePhoto)
        .where(PlacePhoto.place_id == place.place_id)
        .order_by(PlacePhoto.id.asc())
        .limit(1)
    )
    photo = result.scalar_one_or_none()
    if photo:
        return photo

    log(
        f"CALLING WIKIMEDIA: {place.name} | "
        f"{place.city} | {place.place_id}"
    )
    photo_data = await get_wikimedia_photo(
        name=place.name,
        city=place.city,
        place_id=place.place_id,
        lat=place.lat,
        lon=place.lon,
        category=place.category,  
    )
    
    if not photo_data:
        return None

    # Используем репозиторий, чтобы не дублировать логику сохранения.
    photo = await photo_repo.save_place_photo(
        session,
        place_id=place.place_id,
        source=photo_data["source"],
        original_url=photo_data["original_url"],
        local_url_thumb=photo_data.get("local_url_thumb"),
        local_url_medium=photo_data.get("local_url_medium"),
        author=photo_data.get("author"),
        license=photo_data.get("license"),
    )
    return photo


async def get_places_from_db(
    session,
    *,
    region: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = MAX_POI_LIMIT,
) -> list[Place]:
    query = select(Place)
    if region:
        query = query.where(Place.region == region)
    if city:
        query = query.where(Place.city == city)
    if category:
        query = query.where(Place.category == category)
    query = (
        query
        .order_by(Place.name.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_place_by_id(
    session,
    place_id: str,
) -> Optional[Place]:
    result = await session.execute(
        select(Place)
        .where(Place.place_id == place_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def upsert_osm_places(
    session,
    attractions: list[dict],
    *,
    city: str,
    region: str,
) -> list[Place]:
    result: list[Place] = []
    for attr in attractions:
        place_id = attr.get("id")
        name = attr.get("name")
        lat = attr.get("lat")
        lon = attr.get("lon")
        if not place_id or not name:
            continue
        if lat is None or lon is None:
            continue

        category = normalize_category(attr.get("type", ""))

        existing_result = await session.execute(
            select(Place)
            .where(Place.place_id == place_id)
            .limit(1)
        )
        place = existing_result.scalar_one_or_none()

        if place is None:
            place = Place(
                place_id=place_id,
                name=name,
                city=city,
                region=region,
                address=attr.get("address") or "",
                category=category,
                lat=float(lat),
                lon=float(lon),
                hours=attr.get("hours"),
                phone=attr.get("phone"),
            )
            session.add(place)
        else:
            place.name = name
            place.city = city
            place.region = region
            place.address = attr.get("address") or ""
            place.category = category
            place.lat = float(lat)
            place.lon = float(lon)
            place.hours = attr.get("hours")
            place.phone = attr.get("phone")
        result.append(place)
    await session.flush()
    return result


# ============================================================
# WEATHER CACHE
# ============================================================
async def check_weather_cache(city: str) -> Optional[dict]:
    cache_key = f"weather:{city}"
    cached = await redis_client.get(cache_key)
    if not cached:
        return None
    try:
        data = json.loads(cached)
        timestamp = datetime.fromisoformat(data["timestamp"])
        if timestamp > datetime.utcnow() - timedelta(minutes=30):
            return data
    except (
        json.JSONDecodeError,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        error(f"Ошибка чтения weather cache для {city}: {exc}")
    return None


async def set_weather_cache(city: str, data: dict) -> None:
    cache_key = f"weather:{city}"
    cache_data = {
        **data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await redis_client.setex(
        cache_key,
        1800,
        json.dumps(cache_data, ensure_ascii=False),
    )


# ============================================================
# ROOT
# ============================================================
@app.get("/")
async def root():
    return {
        "status": "JARVIS GEO-APP API",
        "version": "2.2.0",
    }


# ============================================================
# REGIONS
# ============================================================
@app.get("/api/regions", response_model=List[RegionResponse])
async def get_regions():
    return [
        RegionResponse(
            id=normalize_region_id(region_name),
            name=region_name,
            cities=cities,
        )
        for region_name, cities in REGIONS.items()
    ]


@app.get("/api/cities/{region_id}", response_model=List[CityResponse])
async def get_cities(region_id: str):
    for region_name, cities in REGIONS.items():
        if normalize_region_id(region_name) == region_id:
            return [
                CityResponse(name=city, region=region_name)
                for city in cities
            ]
    raise HTTPException(
        status_code=404,
        detail=get_text("choose_city_empty"),
    )


# ============================================================
# WEATHER
# ============================================================
@app.get("/api/weather/{city}", response_model=WeatherResponse)
async def get_weather_endpoint(city: str):
    cached = await check_weather_cache(city)
    if cached:
        return WeatherResponse(
            city=city,
            description=cached.get("description", ""),
            cached=True,
        )
    try:
        weather_text = await get_weather(city)
        await set_weather_cache(city, {"description": weather_text})
        return WeatherResponse(
            city=city,
            description=weather_text,
            cached=False,
        )
    except Exception as exc:
        error(f"Weather API error for {city}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=get_text("internal_error"),
        )


# ============================================================
# POIS — QUERY / IMPORT FROM OSM
# ============================================================
@app.post("/api/pois/query")
async def query_pois(query: POIQuery):
    if not query.city:
        raise HTTPException(status_code=400, detail="City required")

    limit = normalize_limit(query.limit)
    offset = normalize_offset(query.offset)

    async with AsyncSessionLocal() as session:
        places = await get_places_from_db(
            session,
            region=query.region,
            city=query.city,
            offset=offset,
            limit=limit,
        )

        # Если город ещё не импортирован — тянем из OSM.
        if not places and offset == 0:
            log(
                f"Places DB empty for {query.city}. "
                f"Fetching OSM data."
            )
            osm_attractions = await get_attractions_osm(
                city=query.city,
                limit=100,
            )
            if osm_attractions:
                await upsert_osm_places(
                    session,
                    osm_attractions,
                    city=query.city,
                    region=query.region,
                )
                await session.commit()
                places = await get_places_from_db(
                    session,
                    region=query.region,
                    city=query.city,
                    offset=0,
                    limit=MAX_POI_LIMIT,
                )

        # Фильтр по категориям, если клиент передал теги.
        if query.tags:
            normalized_tags = {
                normalize_category(tag) for tag in query.tags
            }
            places = [
                place
                for place in places
                if place.category in normalized_tags
            ]

        # Гарантируем наличие фото для каждого места.
        # ВАЖНО: это может быть медленно при первом запросе,
        # потому что для каждого места может быть запрос к Wikimedia.
        for place in places:
            await ensure_place_photo(session, place)

        place_ids = [place.place_id for place in places]
        photos = await get_photos_map(session, place_ids)

        pois = [
            place_to_dict(place, photos.get(place.place_id))
            for place in places[:limit]
        ]
        await session.commit()

        return {
            "count": len(pois),
            "region": query.region,
            "city": query.city,
            "tags": query.tags,
            "offset": offset,
            "limit": limit,
            "pois": pois,
        }


# ============================================================
# POIS — LIST FROM DATABASE
# ============================================================
@app.get("/api/pois")
async def get_all_pois(
    region: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = 30,
):
    limit = normalize_limit(limit)
    offset = normalize_offset(offset)
    if category:
        category = normalize_category(category)

    async with AsyncSessionLocal() as session:
        places = await get_places_from_db(
            session,
            region=region,
            city=city,
            category=category,
            offset=offset,
            limit=limit,
        )
        photos = await get_photos_map(
            session,
            [place.place_id for place in places],
        )
        pois = [
            place_to_dict(place, photos.get(place.place_id))
            for place in places
        ]
        return {
            "pois": pois,
            "count": len(pois),
            "offset": offset,
            "limit": limit,
        }


# ============================================================
# POI — DETAIL
# ============================================================
@app.get("/api/pois/{place_id}", response_model=POIDetail)
async def get_poi_detail(place_id: str):
    async with AsyncSessionLocal() as session:
        place = await get_place_by_id(session, place_id)
        if place is None:
            raise HTTPException(
                status_code=404,
                detail="Place not found",
            )

        result = await session.execute(
            select(PlacePhoto)
            .where(PlacePhoto.place_id == place_id)
            .order_by(PlacePhoto.id.asc())
            .limit(1)
        )
        photo = result.scalar_one_or_none()

        return POIDetail(
            **place_to_dict(place, photo),
            photo=photo_to_dict(photo),
        )


# ============================================================
# POI — PHOTOS
# ============================================================
@app.get("/api/pois/{place_id}/photos")
async def get_poi_photos(place_id: str):
    async with AsyncSessionLocal() as session:
        place = await get_place_by_id(session, place_id)
        if place is None:
            raise HTTPException(
                status_code=404,
                detail="Place not found",
            )

        result = await session.execute(
            select(PlacePhoto)
            .where(PlacePhoto.place_id == place_id)
            .order_by(PlacePhoto.id.asc())
        )
        photos = result.scalars().all()
        return {
            "place_id": place_id,
            "photos": [photo_to_dict(photo) for photo in photos],
        }


# ============================================================
# ROUTES
# ============================================================
@app.post("/api/route/build", response_model=RouteResponse)
async def build_route(req: RouteRequest):
    if len(req.poi_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail=get_text(
                "min_points_error",
                count=len(req.poi_ids),
            ),
        )

    # Убираем пустые и дублирующиеся ID, сохраняя порядок.
    requested_ids = []
    seen_ids = set()
    for poi_id in req.poi_ids:
        if not poi_id or poi_id in seen_ids:
            continue
        seen_ids.add(poi_id)
        requested_ids.append(poi_id)

    if len(requested_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 unique points",
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Place).where(Place.place_id.in_(requested_ids))
        )
        places = list(result.scalars().all())

    places_by_id = {place.place_id: place for place in places}
    route_points = []
    for poi_id in requested_ids:
        place = places_by_id.get(poi_id)
        if place is None:
            continue
        if place.lat is None or place.lon is None:
            continue
        route_points.append({
            "id": place.place_id,
            "lat": float(place.lat),
            "lon": float(place.lon),
            "name": place.name,
        })

    if len(route_points) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 points with coordinates",
        )

    if req.optimize:
        route_points = optimizeRoutePoints(route_points)

    google_url = build_google_maps_link(route_points)
    if not google_url:
        raise HTTPException(
            status_code=500,
            detail="Unable to build Google Maps route",
        )

    total_distance = 0.0
    distance_failed = False
    for index in range(len(route_points) - 1):
        a = route_points[index]
        b = route_points[index + 1]
        distance = await get_distance_osrm(
            a["lat"], a["lon"], b["lat"], b["lon"],
        )
        if distance is None:
            distance_failed = True
            break
        total_distance += distance

    return RouteResponse(
        poi_ids=[point["id"] for point in route_points],
        google_maps_url=google_url,
        total_distance_km=(
            round(total_distance, 1) if not distance_failed else None
        ),
        optimized=req.optimize,
    )


# ============================================================
# FAVORITES
# ============================================================
@app.post("/api/favorites/toggle")
async def toggle_favorite(data: FavoriteToggle):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Favorite)
            .where(
                Favorite.user_id == data.user_id,
                Favorite.place_id == data.poi_id,
            )
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            await session.execute(
                delete(Favorite).where(Favorite.id == existing.id)
            )
            await session.commit()
            return {
                "poi_id": data.poi_id,
                "user_id": data.user_id,
                "favorited": False,
            }

        place = await get_place_by_id(session, data.poi_id)
        if place is None:
            raise HTTPException(
                status_code=404,
                detail="Place not found",
            )

        favorite = Favorite(
            user_id=data.user_id,
            place_id=place.place_id,
            place_name=place.name,
            address=place.address or "",
            lat=float(place.lat),
            lon=float(place.lon),
        )
        session.add(favorite)
        await session.commit()
        return {
            "poi_id": data.poi_id,
            "user_id": data.user_id,
            "favorited": True,
        }


@app.get("/api/favorites/{user_id}")
async def get_favorites(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
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
async def auth_telegram(request: Request):
    data = await request.json()
    init_data = data.get("initData", "")
    if "user=" not in init_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid initData",
        )

    try:
        import urllib.parse
        parsed = urllib.parse.parse_qs(init_data)
        user_json = parsed.get("user", ["{}"])[0]
        user_data = json.loads(user_json)
    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:
        error(f"Ошибка разбора Telegram initData: {exc}")
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
    username = user_data.get("username", "")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        is_new = user is None

        if is_new:
            user = User(user_id=user_id, username=username)
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
    uvicorn.run(app, host="0.0.0.0", port=8000)