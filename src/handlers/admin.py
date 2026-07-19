import os
import asyncio
import tempfile
import time
import shutil
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func, update, text, delete, or_
from src.config import SUPERADMINS
from src.database.db import AsyncSessionLocal
from src.database.models import User, OsmCache, Favorite, History, Group, GroupMember, GroupVote
from src.database.session_manager import user_sessions
from src.database.repositories.user_repo import UserRepository
from src.utils.languages import get_text
from src.utils.utils import admin_logger
from src.utils.redis_keys import RedisKeys


#---------ADMIN AND SUPERADMIN DECORATORS----------
async def register_admin_handlers(bot: AsyncTeleBot, redis_client):
    def adminRequired(func):
        async def wrapper(message_or_call):
            user_id = message_or_call.from_user.id
            if user_id in SUPERADMINS:
                return await func(message_or_call)
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(User.is_admin).where(User.user_id == user_id))
                if result.scalar_one_or_none():
                    return await func(message_or_call)
            await bot.reply_to(message_or_call, get_text("admin_required_msg"))
        return wrapper

    def superadminRequired(func):
        async def wrapper(message_or_call):
            if message_or_call.from_user.id in SUPERADMINS:
                return await func(message_or_call)
            await bot.reply_to(message_or_call, get_text("superadmin_required_msg"))
        return wrapper

#----------HANLDLERS----------
    @bot.message_handler(commands=['ban', 'unban'])
    @adminRequired
    async def ban_management(message):
        cmd = message.text.split()[0]
        args = message.text.split()
        
        if len(args) < 2:
            return await bot.reply_to(message, get_text("usage_ban_unban"))
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            
            user = await user_repo.get_by_identifier(args[1])
            
            if not user:
                return await bot.reply_to(message, get_text("user_not_found"))

            if user not in SUPERADMINS:
                is_banned = (cmd == '/ban')
                await user_repo.set_ban_status(user.user_id, is_banned)
            else:
                pass
                admin_logger.info("SUPERADMIN BAN ATTEMPT.")
    
        if is_banned:

            await redis_client.set(RedisKeys.ban(user.user_id), "1")
            await bot.reply_to(message, get_text("user_banned", username=user.username, user_id=user.user_id))
        else:
            await redis_client.delete(RedisKeys.ban(user.user_id))
            await bot.reply_to(message, get_text("user_unbanned", username=user.username, user_id=user.user_id))

    @bot.message_handler(commands=['maintenance'])
    @superadminRequired
    async def toggle_maintenance(message):
        current = await redis_client.get(RedisKeys.maintenance())
        new_val = "1" if current != "1" else "0"
        await redis_client.set(RedisKeys.maintenance(), new_val)
        status = "ВКЛЮЧЕН (только админы)" if new_val == "1" else "ВЫКЛЮЧЕН"
        await bot.reply_to(message, get_text("maintenance_status", status=status))

    @bot.message_handler(commands=['stats'])
    @adminRequired
    async def stats_command(message):
        async with AsyncSessionLocal() as session:
          
            u_count = await session.scalar(select(func.count(User.user_id)))
            c_count = await session.scalar(select(func.count(OsmCache.id)))
            h_count = await session.scalar(select(func.count(History.id)))
            f_count = await session.scalar(select(func.count(Favorite.id)))
            g_count = await session.scalar(select(func.count(Group.id)))
            
           
            stats = get_text(
                "stats_title", 
                total_users=u_count, 
                cached_cities=c_count, 
                total_routes=h_count,
                total_favs=f_count,
                total_groups=g_count  
            )
            await bot.reply_to(message, stats, parse_mode="HTML")
    @bot.message_handler(commands=['user_lookup'])
    @adminRequired
    async def user_lookup(message):
        args = message.text.split()
        if len(args) < 2: return await bot.reply_to(message, get_text("usage_user_lookup"))
        
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_identifier(args[1])
            if not user: return await bot.reply_to(message, get_text("user_not_found"))
            
            await bot.reply_to(message, get_text("user_profile", username=user.username, user_id=user.user_id, is_admin=user.is_admin), parse_mode="HTML")

    @bot.message_handler(commands=['flush_redis'])
    @superadminRequired
    async def flush_redis(message):
        await redis_client.flushall()
        await bot.reply_to(message, get_text("redis_flushed"))

    @bot.message_handler(commands=['permissions'])
    @adminRequired
    async def permissionsSummary(message):
        textMsg = get_text("admin_permissions_panel")
        await bot.reply_to(message, textMsg, parse_mode="HTML")


    @bot.message_handler(commands=['db_ping'])
    @adminRequired
    async def dbPingCommand(message):
        latency = None
        async with AsyncSessionLocal() as session:
            try:
                startTime = time.time()
                await session.execute(text("SELECT 1"))
                endTime = time.time()
                latency = (endTime - startTime) * 1000
                statusEmoji = "⚡" if latency < 15 else "🐢"
                await bot.reply_to(message, get_text("db_ping_result", status_emoji=statusEmoji, latency=f"{latency:.2f} ms"), parse_mode="HTML")
            except Exception as e:
                admin_logger.exception(f"Command failed: {e}")
                await bot.reply_to(message, get_text("generic_admin_error"))

    @bot.message_handler(commands=['active_users'])
    @adminRequired
    async def activeUsersCommand(message):
        async with AsyncSessionLocal() as session:
            try:
                queryStmt = select(func.count(func.distinct(History.user_id))).where(History.created_at >= text("NOW() - INTERVAL '1 day'"))
                activeCnt = (await session.execute(queryStmt)).scalar() or 0
                await bot.reply_to(message, get_text("active_users_result", active_count=activeCnt), parse_mode="HTML")
            except Exception as e:
                admin_logger.exception(f"Command failed: {e}")
                await bot.reply_to(message, get_text("generic_admin_error"))

    @bot.message_handler(commands=['cached_regions'])
    @adminRequired
    async def cachedRegionsCommand(message):
        async with AsyncSessionLocal() as session:
            try:
                queryStmt = select(OsmCache.city, func.count(OsmCache.id)).group_by(OsmCache.city)
                results = (await session.execute(queryStmt)).all()
                if not results:
                    await bot.reply_to(message, get_text("cached_regions_empty"))
                    return
                resp = get_text("cached_regions_summary")
                for city, count in results:
                    resp += f"• <code>{city or 'Неизвестно'}</code>: {count} объектов\n"
                await bot.reply_to(message, resp, parse_mode="HTML")
            except Exception as e:
                admin_logger.exception(f"Command failed: {e}")
                await bot.reply_to(message, get_text("generic_admin_error"))

    @bot.message_handler(commands=['top_locations'])
    @adminRequired
    async def topLocationsCommand(message):
        async with AsyncSessionLocal() as session:
            try:
                queryStmt = select(Favorite.place_id, func.count(Favorite.id)).group_by(Favorite.place_id).order_by(func.count(Favorite.id).desc()).limit(5)
                results = (await session.execute(queryStmt)).all()
                if not results:
                    await bot.reply_to(message, get_text("top_locations_empty"))
                    return
                resp = get_text("top_locations_summary")
                for placeId, count in results:
                    resp += f"• ID <code>{placeId}</code> — В избранном у: <b>{count}</b> чел.\n"
                await bot.reply_to(message, resp, parse_mode="HTML")
            except Exception as e:
                admin_logger.exception(f"Command failed: {e}")
                await bot.reply_to(message, get_text("generic_admin_error"))

    @bot.message_handler(commands=['session_info'])
    @adminRequired
    async def sessionInfoCommand(message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                await bot.reply_to(message, get_text("session_info_usage"))
                return
            targetId = parts[1]
            sessionData = await user_sessions.get_user_session(targetId)
            if not sessionData:
                await bot.reply_to(message, get_text("active_session_not_found"), parse_mode="HTML")
                return
            await bot.reply_to(message, get_text("session_info_result", target_id=targetId, session_data=sessionData), parse_mode="HTML")
        except Exception as e:
            admin_logger.exception(f"Command failed: {e}")
            await bot.reply_to(message, get_text("generic_admin_error"))

    
    @bot.message_handler(commands=['latest_history'])
    @adminRequired
    async def latestHistoryCommand(message):
        async with AsyncSessionLocal() as session:
            try:
                queryStmt = select(History).order_by(History.created_at.desc()).limit(5)
                results = (await session.execute(queryStmt)).scalars().all()
                if not results:
                    await bot.reply_to(message, get_text("latest_history_empty"))
                    return
                resp = get_text("latest_history_summary")
                for record in results:
                    resp += f"• Юзер <code>{record.user_id}</code>: {record.query or 'Поиск'} [{record.created_at}]\n"
                await bot.reply_to(message, resp, parse_mode="HTML")
            except Exception as e:
                admin_logger.exception(f"Command failed: {e}")
                await bot.reply_to(message, get_text("generic_admin_error"))

    @bot.message_handler(commands=['bot_uptime'])
    @adminRequired
    async def botUptimeCommand(message):
        currentTimeStr = time.strftime('%Y-%m-%d %H:%M:%S')
        await bot.reply_to(message, get_text("bot_uptime_result", current_time=currentTimeStr), parse_mode="HTML")

    @bot.message_handler(commands=['sys_alerts'])
    @adminRequired
    async def sysAlertsCommand(message):
        await bot.reply_to(message, get_text("sys_alerts_result"), parse_mode="HTML")

    @bot.message_handler(commands=['getdb'])
    @superadminRequired
    async def getDatabaseDump(message):
        await bot.reply_to(message, get_text("database_dump_in_progress"), parse_mode="HTML")
        logDir = "admin_logs"
        dumpFilePath = os.path.join(logDir, "jarvis_geo_bot_db_dump.sql")
        try:
            if not os.path.exists(logDir):
                os.makedirs(logDir)
            if os.path.exists(dumpFilePath):
                if os.path.isdir(dumpFilePath):
                    shutil.rmtree(dumpFilePath)
                else:
                    os.remove(dumpFilePath)
            
            async with AsyncSessionLocal() as session:
                tables = ["users", "osm_cache", "favorites", "history", "groups", "group_members", "group_votes"]
                with open(dumpFilePath, "w", encoding="utf-8") as dumpFile:
                    dumpFile.write("-- JARVIS GEO-BOT PYTHON DUMP\n")
                    dumpFile.write(f"-- CREATED AT: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    for table in tables:
                        dumpFile.write(f"--- DATA FOR TABLE: {table} ---\n")
                        res = await session.execute(text(f"SELECT * FROM {table}"))
                        columns = res.keys()
                        for row in res.fetchall():
                            vals = []
                            for v in row:
                                if v is None:
                                    vals.append("NULL")
                                elif isinstance(v, (int, float)):
                                    vals.append(str(v))
                                elif isinstance(v, bool):
                                    vals.append("TRUE" if v else "FALSE")
                                else:
                                    escaped = str(v).replace("'", "''")
                                    vals.append(f"'{escaped}'")
                            colStr = ", ".join(columns)
                            valStr = ", ".join(vals)
                            dumpFile.write(f"INSERT INTO {table} ({colStr}) VALUES ({valStr});\n")
                        dumpFile.write("\n")
            
            if os.path.exists(dumpFilePath) and os.path.getsize(dumpFilePath) > 0:
                with open(dumpFilePath, 'rb') as f:
                    await bot.send_document(message.chat.id, f, caption=get_text("database_dump_caption"))
                admin_logger.info(f"Superadmin {message.from_user.id} dumped database via Python")
            else:
                raise FileNotFoundError()
        except Exception as e:
            admin_logger.exception(f"Command failed: {e}")
            await bot.reply_to(message, get_text("generic_admin_error"))
            
    @bot.message_handler(commands=['clear_cache'])
    @superadminRequired
    async def clearCacheCommand(message):
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(delete(OsmCache))
                await session.commit()
                await bot.reply_to(message, get_text("cache_cleared"))
                admin_logger.info(f"Superadmin {message.from_user.id} dropped OsmCache table data")
            except Exception as e:
                admin_logger.exception(f"Command failed: {e}")
                await session.rollback()
                await bot.reply_to(message, get_text("cache_clear_error", error=e))

    @bot.message_handler(commands=['drop_database_data'])
    @superadminRequired
    async def dropDatabaseDataCommand(message):
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(delete(Favorite))
                await session.execute(delete(History))
                await session.execute(delete(OsmCache))
                await session.commit()
                await bot.reply_to(message, get_text("database_wiped"), parse_mode="HTML")
                admin_logger.critical(f"Superadmin {message.from_user.id} wiped database user data")
            except Exception as e:
                admin_logger.exception(f"Command failed: {e}")
                await session.rollback()
                await bot.reply_to(message, get_text("database_wipe_error", error=e))

            
    @bot.message_handler(commands=['force_broadcast'])
    @superadminRequired
    async def forceBroadcastCommand(message):
        try:
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                await bot.reply_to(message, get_text("usage_force_broadcast"))
                return
            broadcastText = parts[1]
            async with AsyncSessionLocal() as session:
                users = (await session.execute(select(User.user_id))).scalars().all()
                successCount = 0
                for uId in users:
                    try:
                        await bot.send_message(uId, get_text("broadcast_message", broadcast_text=broadcastText), parse_mode="HTML")
                        successCount += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        continue
                await bot.reply_to(message, get_text("broadcast_completed", success_count=successCount, total_count=len(users)), parse_mode="HTML")
        except Exception as e:
            admin_logger.exception(f"Command failed: {e}")
            await bot.reply_to(message, get_text("broadcast_error", error=e))

    @bot.message_handler(commands=['set_admin'])
    @superadminRequired
    async def setAdminCommand(message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                await bot.reply_to(message, get_text("usage_add_admin"))
                return
            newAdminId = int(parts[1])

            async with AsyncSessionLocal() as dbSession:
                result = await dbSession.execute(
                    update(User).where(User.user_id == newAdminId).values(is_admin=True)
                )
                if result.rowcount == 0:
                    await bot.reply_to(message, get_text("admin_not_found", user_id=newAdminId), parse_mode="HTML")
                    return
                await dbSession.commit()

            await bot.reply_to(message, get_text("admin_added_success", user_id=newAdminId), parse_mode="HTML")
        except ValueError:
            await bot.reply_to(message, get_text("target_id_numeric"))
        except Exception as e:
            admin_logger.exception(f"Command failed: {e}")
            await bot.reply_to(message, get_text("admin_action_error", e=str(e)))

    @bot.message_handler(commands=['rev_admin'])
    @superadminRequired
    async def revAdminCommand(message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                await bot.reply_to(message, get_text("usage_rev_admin"))
                return
            oldAdminId = int(parts[1])

            async with AsyncSessionLocal() as dbSession:
                result = await dbSession.execute(
                    update(User).where(User.user_id == oldAdminId).values(is_admin=False)
                )
                if result.rowcount == 0:
                    await bot.reply_to(message, get_text("admin_not_found", user_id=oldAdminId), parse_mode="HTML")
                    return
                await dbSession.commit()

            await bot.reply_to(message, get_text("admin_revoked_success", user_id=oldAdminId), parse_mode="HTML")
        except ValueError:
            await bot.reply_to(message, get_text("target_id_numeric"))
        except Exception as e:
            admin_logger.exception(f"Command failed: {e}")
            await bot.reply_to(message, get_text("admin_action_error", e=str(e)))