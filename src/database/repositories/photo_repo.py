from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import PlacePhoto


async def get_place_photo(
    session: AsyncSession,
    place_id: str,
) -> PlacePhoto | None:

    result = await session.execute(
        select(PlacePhoto)
        .where(PlacePhoto.place_id == place_id)
        .limit(1)
    )

    return result.scalar_one_or_none()


async def save_place_photo(
    session: AsyncSession,
    place_id: str,
    photo: dict,
) -> PlacePhoto:

    existing = await get_place_photo(
        session,
        place_id,
    )

    if existing:
        return existing

    item = PlacePhoto(
        place_id=place_id,
        source=photo["source"],
        original_url=photo["original_url"],
        local_url=photo["local_url"],
        author=photo.get("author"),
        license=photo.get("license"),
    )

    session.add(item)

    await session.flush()

    return item