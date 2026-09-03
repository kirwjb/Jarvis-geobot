from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import PlacePhoto


async def get_place_photo(
    session: AsyncSession,
    place_id: str,
) -> PlacePhoto | None:

    result = await session.execute(
        select(PlacePhoto)
        .where(
            PlacePhoto.place_id == place_id
        )
        .order_by(PlacePhoto.id.asc())
        .limit(1)
    )

    return result.scalar_one_or_none()


async def get_place_photos(
    session: AsyncSession,
    place_id: str,
) -> list[PlacePhoto]:

    result = await session.execute(
        select(PlacePhoto)
        .where(
            PlacePhoto.place_id == place_id
        )
        .order_by(PlacePhoto.id.asc())
    )

    return list(result.scalars().all())


async def save_place_photo(
    session: AsyncSession,
    *,
    place_id: str,
    source: str,
    original_url: str,
    local_url: str,
    author: str | None = None,
    license: str | None = None,
) -> PlacePhoto:

    existing = await session.execute(
        select(PlacePhoto)
        .where(
            PlacePhoto.place_id == place_id,
            PlacePhoto.original_url == original_url,
        )
        .limit(1)
    )

    photo = existing.scalar_one_or_none()

    if photo:
        photo.local_url = local_url
        photo.author = author
        photo.license = license

        await session.flush()

        return photo

    photo = PlacePhoto(
        place_id=place_id,
        source=source,
        original_url=original_url,
        local_url=local_url,
        author=author,
        license=license,
    )

    session.add(photo)

    await session.flush()

    return photo