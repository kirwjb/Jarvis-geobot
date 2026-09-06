from telebot.async_telebot import AsyncTeleBot
from src.config import SUPERADMINS
from src.database.db import AsyncSessionLocal
from src.database.models import OsmCache, Place, PlacePhoto
from src.database.session_manager import redis_client
from src.utils.utils import admin_logger
from sqlalchemy import delete, func, select


async def register_cache_admin_handler(bot: AsyncTeleBot):
    @bot.message_handler(commands=["clear_city_cache"])
    async def clear_city_cache(message):
        if message.from_user.id not in SUPERADMINS:
            await bot.reply_to(message, "⚠️ Эта команда доступна только суперадминистраторам.")
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await bot.reply_to(message, "❌ Использование: /clear_city_cache <город>")
            return

        city = parts[1].strip()
        city_key = city.casefold()

        async with AsyncSessionLocal() as session:
            try:
                osm_result = await session.execute(
                    delete(OsmCache).where(func.lower(OsmCache.city) == city_key)
                )
                place_result = await session.execute(
                    select(Place.place_id).where(func.lower(Place.city) == city_key)
                )
                place_ids = [row[0] for row in place_result.all()]

                photos_deleted = 0
                places_deleted = 0
                if place_ids:
                    photo_result = await session.execute(
                        delete(PlacePhoto).where(PlacePhoto.place_id.in_(place_ids))
                    )
                    photos_deleted = photo_result.rowcount or 0
                    place_delete_result = await session.execute(
                        delete(Place).where(Place.place_id.in_(place_ids))
                    )
                    places_deleted = place_delete_result.rowcount or 0

                await session.commit()

                try:
                    await redis_client.delete(f"weather:{city}")
                except Exception:
                    admin_logger.exception("Failed to clear weather cache for %s", city)

                osm_deleted = osm_result.rowcount or 0
                await bot.reply_to(
                    message,
                    "🧹 Кэш города <b>{}</b> очищен.\n"
                    "OSM: {}\nМеста: {}\nФото: {}\n"
                    "♻️ При следующем запросе данные будут загружены заново.".format(
                        city, osm_deleted, places_deleted, photos_deleted
                    ),
                    parse_mode="HTML",
                )
                admin_logger.info(
                    "Superadmin %s cleared city cache: city=%s osm=%s places=%s photos=%s",
                    message.from_user.id,
                    city,
                    osm_deleted,
                    places_deleted,
                    photos_deleted,
                )
            except Exception as exc:
                await session.rollback()
                admin_logger.exception("City cache cleanup failed for %s", city)
                await bot.reply_to(message, f"❌ Не удалось очистить кэш города: {exc}")
