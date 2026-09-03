from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Place


async def get_place(
    session: AsyncSession,
    place_id: str,
) -> Place | None:
    result = await session.execute(
        select(Place)
        .where(Place.place_id == place_id)
        .limit(1)
    )

    return result.scalar_one_or_none()


async def get_places(
    session: AsyncSession,
    *,
    city: str | None = None,
    region: str | None = None,
    category: str | None = None,
    offset: int = 0,
    limit: int = 30,
) -> list[Place]:

    query = select(Place)

    if city:
        query = query.where(
            Place.city == city
        )

    if region:
        query = query.where(
            Place.region == region
        )

    if category:
        query = query.where(
            Place.category == category
        )

    query = (
        query
        .order_by(Place.name.asc())
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 30))
    )

    result = await session.execute(query)

    return list(result.scalars().all())


async def upsert_place(
    session: AsyncSession,
    *,
    place_id: str,
    name: str,
    city: str,
    region: str,
    address: str,
    category: str,
    lat: float,
    lon: float,
    hours: str | None = None,
    phone: str | None = None,
) -> Place:

    place = await get_place(
        session,
        place_id,
    )

    if place is None:
        place = Place(
            place_id=place_id,
            name=name,
            city=city,
            region=region,
            address=address,
            category=category,
            lat=lat,
            lon=lon,
            hours=hours,
            phone=phone,
        )

        session.add(place)

    else:
        place.name = name
        place.city = city
        place.region = region
        place.address = address
        place.category = category
        place.lat = lat
        place.lon = lon
        place.hours = hours
        place.phone = phone

    await session.flush()

    return place


async def delete_place(
    session: AsyncSession,
    place_id: str,
) -> bool:

    place = await get_place(
        session,
        place_id,
    )

    if place is None:
        return False

    await session.delete(place)
    await session.flush()

    return True