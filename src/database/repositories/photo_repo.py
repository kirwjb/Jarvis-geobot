"""
Репозиторий для работы с фотографиями мест.

ВАЖНО: в модели PlacePhoto должны быть поля:
- local_url_thumb   (String, nullable=True)
- local_url_medium  (String, nullable=True)

Если раньше было поле local_url — его нужно заменить миграцией.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import PlacePhoto

async def get_place_photo(
    session: AsyncSession,
    place_id: str,
) -> PlacePhoto | None:
    """Возвращает первое фото для места."""
    result = await session.execute(
        select(PlacePhoto)
        .where(PlacePhoto.place_id == place_id)
        .order_by(PlacePhoto.id.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()

async def get_place_photos(
    session: AsyncSession,
    place_id: str,
) -> list[PlacePhoto]:
    """Возвращает все фото для места."""
    result = await session.execute(
        select(PlacePhoto)
        .where(PlacePhoto.place_id == place_id)
        .order_by(PlacePhoto.id.asc())
    )
    return list(result.scalars().all())

async def save_place_photo(
    session: AsyncSession,
    *,
    place_id: str,
    source: str,
    original_url: str,
    local_url_thumb: str | None = None,
    local_url_medium: str | None = None,
    author: str | None = None,
    license: str | None = None,
) -> PlacePhoto:
    """
    Сохраняет или обновляет фотографию места.
    Если запись с тем же place_id и original_url уже есть — обновляем её.
    """
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
        photo.source = source
        photo.local_url_thumb = local_url_thumb
        photo.local_url_medium = local_url_medium
        photo.author = author
        photo.license = license
        await session.flush()
        return photo

    photo = PlacePhoto(
        place_id=place_id,
        source=source,
        original_url=original_url,
        local_url_thumb=local_url_thumb,
        local_url_medium=local_url_medium,
        author=author,
        license=license,
    )
    session.add(photo)
    await session.flush()
    return photo

async def is_photo_blocked(
    session: AsyncSession,
    place_id: str,
) -> bool:
    """Проверяет, заблокирована ли фотография для места."""
    result = await session.execute(
        select(PlacePhoto)
        .where(PlacePhoto.place_id == place_id, PlacePhoto.source == "blocked")
        .limit(1)
    )
    return result.scalar_one_or_none() is not None

async def block_place_photo(
    session: AsyncSession,
    place_id: str,
    reason: str = "blocked",
) -> PlacePhoto:
    """
    Блокирует фотографию места в базе данных.
    Помечает запись как source="blocked", чтобы предотвратить повторную загрузку.
    """
    existing = await session.execute(
        select(PlacePhoto).where(PlacePhoto.place_id == place_id)
    )
    photos = list(existing.scalars().all())
    if photos:
        for p in photos:
            p.source = "blocked"
            p.original_url = "blocked"
            p.local_url_thumb = None
            p.local_url_medium = None
            p.author = None
            p.license = None
        await session.flush()
        return photos[0]

    blocked = PlacePhoto(
        place_id=place_id,
        source="blocked",
        original_url="blocked",
        local_url_thumb=None,
        local_url_medium=None,
    )
    session.add(blocked)
    await session.flush()
    return blocked

async def delete_place_photos(
    session: AsyncSession,
    place_id: str,
) -> int:
    """Удаляет все записи фотографий места из базы данных."""
    result = await session.execute(
        select(PlacePhoto).where(PlacePhoto.place_id == place_id)
    )
    photos = list(result.scalars().all())
    count = len(photos)
    for p in photos:
        await session.delete(p)
    if count > 0:
        await session.flush()
    return count

async def save_photo_report(
    session: AsyncSession,
    *,
    place_id: str,
    photo_url: str | None = None,
    reason: str = "inappropriate",
    details: str | None = None,
):
    """Сохраняет жалобу на фотографию места."""
    from src.database.models import PhotoReport

    report = PhotoReport(
        place_id=place_id,
        photo_url=photo_url,
        reason=reason,
        details=details,
    )
    session.add(report)
    await session.flush()
    return report
