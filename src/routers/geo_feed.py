"""Next-generation POI feed: full OSM import, search, shuffle and page counts."""
import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from src.database.db import AsyncSessionLocal
from src.database.models import Place, PlacePhoto
from src.services.parser_service import get_attractions_osm
from src.services.photo_url_service import find_photo_url

router = APIRouter(prefix="/api/geo", tags=["geo-feed"])
PAGE_SIZE = 8
MAX_PAGE_SIZE = 30
TAG_CATEGORY_MAP = {"architecture": {"castle", "church", "monument", "manor", "gallery", "ruins"}, "nature": {"park", "viewpoint", "ruins"}, "museum": {"museum"}, "church": {"church"}, "castle": {"castle"}, "monument": {"monument"}, "park": {"park"}}
CATEGORY_MAP = {"музей": "museum", "достопримечательность": "misc", "галерея": "gallery", "смотровая площадка": "viewpoint", "памятник": "monument", "мемориал": "memorial", "замок": "castle", "руины": "ruins", "церковь": "church", "собор": "church", "усадьба": "manor", "парк аттракционов": "theme_park"}
VALID_CATEGORIES = {"castle", "church", "museum", "monument", "park", "gallery", "viewpoint", "memorial", "ruins", "manor", "theme_park", "misc"}

def categories(tags: list[str]) -> set[str]:
    result = set()
    for tag in tags:
        key = str(tag or "").strip().lower()
        result.update(TAG_CATEGORY_MAP.get(key, {key}))
    return result

def normalize_category(value: str) -> str:
    value = (value or "").strip().lower()
    return CATEGORY_MAP.get(value, value if value in VALID_CATEGORIES else "misc")

def place_dict(place: Place, photo: PlacePhoto | None = None) -> dict:
    url = photo.original_url if photo else None
    images = {"thumb": url, "medium": url, "original": url} if url else None
    return {"id": place.place_id, "name": place.name, "city": place.city, "region": place.region, "address": place.address or "", "category": place.category, "lat": float(place.lat), "lon": float(place.lon), "hours": place.hours, "phone": place.phone, "image_url": url, "images": images}

async def ensure_city_data(session, city: str, region: str) -> None:
    exists = await session.execute(select(func.count(Place.id)).where(Place.city == city))
    if exists.scalar_one() > 0:
        return
    attractions = await get_attractions_osm(city, limit=0)
    for attr in attractions:
        pid, name = attr.get("id"), attr.get("name"); lat, lon = attr.get("lat"), attr.get("lon")
        if not pid or not name or lat is None or lon is None: continue
        row = await session.execute(select(Place).where(Place.place_id == pid).limit(1)); place = row.scalar_one_or_none()
        if place is None:
            session.add(Place(place_id=pid, name=name, city=city, region=region, address=attr.get("address") or "", category=normalize_category(attr.get("type", "misc")), lat=float(lat), lon=float(lon), hours=attr.get("hours"), phone=attr.get("phone")))
    await session.flush()

async def hydrate_urls(session, places: list[Place]) -> dict[str, PlacePhoto]:
    result: dict[str, PlacePhoto] = {}
    for place in places:
        row = await session.execute(select(PlacePhoto).where(PlacePhoto.place_id == place.place_id).order_by(PlacePhoto.id.asc()).limit(1)); photo = row.scalar_one_or_none()
        if photo and photo.original_url:
            result[place.place_id] = photo; continue
        data = await find_photo_url(name=place.name, city=place.city, lat=place.lat, lon=place.lon, category=place.category)
        if not data: continue
        if photo is None:
            photo = PlacePhoto(place_id=place.place_id, source=data["source"], original_url=data["original_url"], local_url_thumb=None, local_url_medium=None, author=data.get("author"), license=data.get("license")); session.add(photo)
        else:
            photo.source = data["source"]; photo.original_url = data["original_url"]; photo.local_url_thumb = None; photo.local_url_medium = None; photo.author = data.get("author"); photo.license = data.get("license")
        result[place.place_id] = photo
    await session.flush(); return result

@router.get("/pois/feed")
async def feed(region: str, city: str, tags: Optional[str] = None, search: str = "", page: int = 0, page_size: int = PAGE_SIZE, shuffle: str = ""):
    page = max(page, 0); page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    tag_list = [x.strip() for x in (tags or "").split(",") if x.strip()]; cats = categories(tag_list)
    seed = shuffle or hashlib.sha256(f"{city}|{tags or ''}".encode()).hexdigest()[:16]
    async with AsyncSessionLocal() as session:
        await ensure_city_data(session, city, region)
        filters = [Place.city == city]
        if cats: filters.append(Place.category.in_(cats))
        if search.strip():
            term = f"%{search.strip()}%"; filters.append((Place.name.ilike(term)) | (Place.address.ilike(term)))
        count = await session.execute(select(func.count(Place.id)).where(*filters)); total = int(count.scalar_one()); pages = (total + page_size - 1) // page_size if total else 0
        order_expr = func.md5(Place.place_id + seed)
        rows = await session.execute(select(Place).where(*filters).order_by(order_expr).offset(page * page_size).limit(page_size))
        places = list(rows.scalars().all()); photos = await hydrate_urls(session, places); await session.commit()
        return {"region": region, "city": city, "tags": tag_list, "search": search, "page": page, "page_size": page_size, "total": total, "pages": pages, "has_next": page + 1 < pages, "shuffle": seed, "pois": [place_dict(p, photos.get(p.place_id)) for p in places]}

@router.get("/pois/{place_id}")
async def detail(place_id: str):
    async with AsyncSessionLocal() as session:
        row = await session.execute(select(Place).where(Place.place_id == place_id).limit(1)); place = row.scalar_one_or_none()
        if place is None: raise HTTPException(status_code=404, detail="Place not found")
        photos = await hydrate_urls(session, [place]); await session.commit(); return place_dict(place, photos.get(place.place_id))
