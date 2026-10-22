"""
Standalone Admin Console for JARVIS GeoBot Ecosystem.

Role Hierarchy & Access:
    Exclusively restricted to SUPERADMIN (bot owner with direct machine access).
    Standard in-chat moderation is accessible to both ADMIN and SUPERADMIN.

Usage:
    ./Jarvis -a
    ./Jarvis -a stats
    ./Jarvis -a db-vacuum
    ./Jarvis -a migrations
    ./Jarvis -a redis-metrics
    ./Jarvis -a users [--limit 10] [--page 1] [--role ADMIN|USER]
    ./Jarvis -a latency
    ./Jarvis -a ban <id|@username> [reason]
    ./Jarvis -a unban <id|@username>
    ./Jarvis -a mute <id|@username> [reason]
    ./Jarvis -a unmute <id|@username>
    ./Jarvis -a promote <id|@username>
    ./Jarvis -a demote <id|@username>
    ./Jarvis -a maintenance [on|off|status]
    ./Jarvis -a clear-city <name>
    ./Jarvis -a clear-redis
    ./Jarvis -a guillotine <id|@username>
    ./Jarvis -a salon
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Optional

import aiohttp
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import delete, func, select, text, update

from src.config import (
    BOT_OWNER_ID,
    NOMINATIM_URLS,
    OVERPASS_URLS,
    SUPERADMINS,
)
from src.database.db import AsyncSessionLocal, engine
from src.database.models import Favorite, History, OsmCache, Place, PlacePhoto, User
from src.database.repositories.user_repo import UserRepository
from src.database.session_manager import redis_client
from src.services.rbac import (
    Role,
    can_target_user,
    is_superadmin,
    resolve_user_role,
    verify_cli_superadmin,
)
from src.utils.redis_keys import RedisKeys

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def print_banner(active_superadmin_id: Optional[int] = None):
    owner_str = f"Owner #{active_superadmin_id}" if active_superadmin_id else "Host Machine Owner"
    print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════════════╗
║               🛠️   JARVIS ADMIN CONTROL CENTER                       ║
║        Three-Tier RBAC Management & High-Perf Diagnostics            ║
╚══════════════════════════════════════════════════════════════════════╝{RESET}
  {MAGENTA}👑 Authenticated Superadmin:{RESET} {BOLD}{owner_str}{RESET} {GREEN}[Direct Host Access: Verified]{RESET}
""")

def verify_cli_access(caller_id: Optional[int] = None) -> int:
    """
    Enforce that CLI administration is strictly accessible to SUPERADMIN.
    Returns the resolved active Superadmin ID.
    """
    if not SUPERADMINS and BOT_OWNER_ID is None:
        print(f"\n{RED}{BOLD}🚨 RBAC SECURITY REJECTION:{RESET}")
        print(f"{RED}No SUPERADMIN or BOT_OWNER_ID is configured in the environment (.env).{RESET}")
        print(f"{YELLOW}Please configure BOT_OWNER_ID or SUPERADMIN_ID in your .env file to enable CLI operations.{RESET}\n")
        sys.exit(1)

    if caller_id is not None:
        if not is_superadmin(caller_id):
            print(f"\n{RED}{BOLD}⛔ RBAC PERMISSION DENIED:{RESET}")
            print(f"{RED}User #{caller_id} does not possess SUPERADMIN rank.{RESET}")
            print(f"{YELLOW}CLI orchestration (./Jarvis -a) is strictly restricted to SUPERADMIN.{RESET}")
            print(f"{DIM}Standard in-chat moderation is available via Telegram bot commands (/ban, /unban, etc.).{RESET}\n")
            sys.exit(1)
        return caller_id

    return BOT_OWNER_ID or SUPERADMINS[0]

async def get_system_stats() -> dict:
    """Fetch database row counts, active flags, and Redis connectivity."""
    async with AsyncSessionLocal() as session:
        user_count = await session.scalar(select(func.count(User.user_id))) or 0
        banned_count = await session.scalar(select(func.count(User.user_id)).where(User.is_banned == True)) or 0
        muted_count = await session.scalar(select(func.count(User.user_id)).where(User.is_muted == True)) or 0
        admin_count = await session.scalar(select(func.count(User.user_id)).where((User.is_admin == True) | (User.role == "ADMIN"))) or 0
        superadmin_count = len(SUPERADMINS)
        cache_count = await session.scalar(select(func.count(OsmCache.id))) or 0
        place_count = await session.scalar(select(func.count(Place.id))) or 0
        photo_count = await session.scalar(select(func.count(PlacePhoto.id))) or 0
        fav_count = await session.scalar(select(func.count(Favorite.id))) or 0
        history_count = await session.scalar(select(func.count(History.id))) or 0

    m_val = await redis_client.get(RedisKeys.maintenance())
    maintenance_active = (m_val == "1")

    try:
        redis_ok = await redis_client.ping()
    except Exception:
        redis_ok = False

    return {
        "users": user_count,
        "banned_users": banned_count,
        "muted_users": muted_count,
        "admin_users": admin_count,
        "superadmin_users": superadmin_count,
        "cached_cities": cache_count,
        "places": place_count,
        "photos": photo_count,
        "favorites": fav_count,
        "history": history_count,
        "maintenance": maintenance_active,
        "redis_ok": redis_ok,
    }

async def show_stats():
    """Print comprehensive telemetry report."""
    stats = await get_system_stats()
    m_color = RED if stats["maintenance"] else GREEN
    m_text = "ENABLED (Admins Only)" if stats["maintenance"] else "DISABLED (Normal Ops)"
    r_color = GREEN if stats["redis_ok"] else RED
    r_text = "ONLINE" if stats["redis_ok"] else "OFFLINE"

    print(f"\n{BOLD}═══════════════ SYSTEM DIAGNOSTICS & METRICS ═══════════════{RESET}")
    print(f" • Maintenance Mode:     {m_color}{m_text}{RESET}")
    print(f" • Redis Status:          {r_color}{r_text}{RESET}")
    print(f" • Registered Users:      {CYAN}{stats['users']}{RESET} (Superadmins: {MAGENTA}{stats['superadmin_users']}{RESET}, Admins: {YELLOW}{stats['admin_users']}{RESET})")
    print(f" • Access Status Flags:   Banned: {RED}{stats['banned_users']}{RESET} | Muted: {YELLOW}{stats['muted_users']}{RESET}")
    print(f" • Cached OSM Cities:     {CYAN}{stats['cached_cities']}{RESET}")
    print(f" • Stored Places (POIs):  {CYAN}{stats['places']}{RESET}")
    print(f" • Cached Place Photos:   {CYAN}{stats['photos']}{RESET}")
    print(f" • User Saved Favorites:  {CYAN}{stats['favorites']}{RESET}")
    print(f" • Route Query History:   {CYAN}{stats['history']}{RESET}")
    print(f"{BOLD}═════════════════════════════════════════════════════════════{RESET}\n")

async def run_db_vacuum_analyze():
    """Run PostgreSQL VACUUM ANALYZE to reclaim storage and refresh planner stats."""
    print(f"\n{CYAN}⚙️  Executing PostgreSQL VACUUM ANALYZE across all database tables...{RESET}")
    t0 = time.perf_counter()
    try:
        async with engine.connect() as conn:
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("VACUUM ANALYZE;"))
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"{GREEN}✅ VACUUM ANALYZE completed successfully in {elapsed:.2f}ms!{RESET}")
        print(f"{DIM}PostgreSQL planner statistics updated and dead tuples reclaimed.{RESET}\n")
    except Exception as exc:
        print(f"{RED}❌ VACUUM ANALYZE failed: {exc}{RESET}\n")

async def check_schema_migrations() -> dict:
    """Inspect current schema revision vs Alembic heads and report pending migrations."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    head_rev = heads[0] if heads else None

    current_rev = None
    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(text("SELECT version_num FROM alembic_version;"))
            row = res.first()
            if row:
                current_rev = row[0]
        except Exception:
            current_rev = None

    pending = []
    if head_rev and current_rev != head_rev:
        try:
            for sc in script.iterate_revisions(head_rev, current_rev):
                if sc.revision != current_rev:
                    pending.append({
                        "revision": sc.revision,
                        "doc": sc.doc or "No description",
                    })
        except Exception:
            pass

    return {
        "current_revision": current_rev,
        "head_revision": head_rev,
        "pending_migrations": pending,
        "is_up_to_date": (current_rev == head_rev) and (current_rev is not None),
    }

async def show_schema_migrations():
    """Print formatted migration audit report."""
    print(f"\n{BOLD}═══════════════ ALEMBIC SCHEMA MIGRATION AUDIT ═══════════════{RESET}")
    res = await check_schema_migrations()
    curr = res["current_revision"] or "None (Unversioned)"
    head = res["head_revision"] or "Unknown"

    print(f" • Database Current Revision: {CYAN}{curr}{RESET}")
    print(f" • Repository Head Revision:   {CYAN}{head}{RESET}")

    if res["is_up_to_date"]:
        print(f"\n {GREEN}🟢 STATUS: Database schema is completely up-to-date.{RESET}")
    else:
        pending = res["pending_migrations"]
        print(f"\n {YELLOW}⚠️ STATUS: {len(pending)} pending schema migration(s) detected:{RESET}")
        for p in pending:
            print(f"   • {YELLOW}{p['revision']}{RESET}: {p['doc']}")
        print(f"\n {DIM}Run 'alembic upgrade head' to apply pending migrations.{RESET}")
    print(f"{BOLD}══════════════════════════════════════════════════════════════{RESET}\n")

async def show_redis_metrics():
    """Inspect real-time hit/miss ratios and memory footprints from Redis."""
    print(f"\n{BOLD}═══════════════ REDIS & CACHE PERFORMANCE METRICS ═══════════════{RESET}")
    try:
        stats = await redis_client.info("stats")
        mem = await redis_client.info("memory")
        keyspace = await redis_client.info("keyspace")
    except Exception as exc:
        print(f"{RED}❌ Unable to fetch Redis telemetry: {exc}{RESET}\n")
        return

    hits = int(stats.get("keyspace_hits", 0))
    misses = int(stats.get("keyspace_misses", 0))
    total = hits + misses
    ratio = (hits / total * 100.0) if total > 0 else 0.0

    used_mem = mem.get("used_memory_human", "N/A")
    peak_mem = mem.get("used_memory_peak_human", "N/A")
    lua_mem = mem.get("used_memory_lua_human", "N/A")
    max_mem = mem.get("maxmemory_human", "Unlimited")

    color_ratio = GREEN if ratio >= 75.0 else (YELLOW if ratio >= 40.0 else RED)

    print(f" • Cache Hits:            {GREEN}{hits:,}{RESET}")
    print(f" • Cache Misses:          {RED}{misses:,}{RESET}")
    print(f" • Total Lookups:         {CYAN}{total:,}{RESET}")
    print(f" • Hit Ratio:             {color_ratio}{BOLD}{ratio:.2f}%{RESET}")
    print("─" * 65)
    print(f" • Used Memory:           {CYAN}{used_mem}{RESET} (Peak: {CYAN}{peak_mem}{RESET})")
    print(f" • Lua Engine Memory:     {CYAN}{lua_mem}{RESET}")
    print(f" • Max Memory Limit:      {CYAN}{max_mem}{RESET}")
    print("─" * 65)
    print(f" • Keyspace Distribution:")
    if keyspace:
        for db, info_val in keyspace.items():
            print(f"   {CYAN}{db}{RESET}: {info_val}")
    else:
        print(f"   {DIM}No persistent keys currently stored in Redis keyspace.{RESET}")
    print(f"{BOLD}═════════════════════════════════════════════════════════════════{RESET}\n")

async def clear_city_cache(city: str):
    """Clear OSM places, photos, and weather cache for a city."""
    city_key = city.strip().casefold()
    if not city_key:
        print(f"{RED}City name cannot be empty.{RESET}")
        return

    async with AsyncSessionLocal() as session:
        try:
            osm_res = await session.execute(
                delete(OsmCache).where(func.lower(OsmCache.city) == city_key)
            )
            place_res = await session.execute(
                select(Place.place_id).where(func.lower(Place.city) == city_key)
            )
            place_ids = [row[0] for row in place_res.all()]

            photos_del = 0
            places_del = 0
            if place_ids:
                photo_del_res = await session.execute(
                    delete(PlacePhoto).where(PlacePhoto.place_id.in_(place_ids))
                )
                photos_del = photo_del_res.rowcount or 0
                place_del_res = await session.execute(
                    delete(Place).where(Place.place_id.in_(place_ids))
                )
                places_del = place_del_res.rowcount or 0

            await session.commit()
            await redis_client.delete(f"weather:{city.strip()}")

            print(f"{GREEN}Cache successfully cleared for city '{city}'!{RESET}")
            print(f" • OSM Cache entries deleted: {osm_res.rowcount or 0}")
            print(f" • Places deleted:           {places_del}")
            print(f" • Photo entries deleted:    {photos_del}")
            print(f" • Weather cache invalidated.")
        except Exception as exc:
            await session.rollback()
            print(f"{RED}Failed to clear city cache: {exc}{RESET}")

async def clear_all_redis():
    """Clear transient weather and session Redis caches."""
    try:
        keys = await redis_client.keys("weather:*")
        keys.extend(await redis_client.keys("user_session:*"))
        if keys:
            await redis_client.delete(*keys)
            print(f"{GREEN}Cleared {len(keys)} dynamic Redis cache keys.{RESET}")
        else:
            print(f"{YELLOW}No transient Redis cache keys found.{RESET}")
    except Exception as exc:
        print(f"{RED}Redis cache clear error: {exc}{RESET}")

async def display_user_page(
    users: list[User],
    page: int,
    total_pages: int,
    total_count: int,
    role_filter: Optional[str] = None,
):
    """Render a single page of the Superadmin User Directory."""
    filter_label = f" [Filter: {role_filter}]" if role_filter else ""
    print(f"\n{BOLD}═════════ SUPERADMIN USER DIRECTORY (Page {page}/{total_pages} · Total: {total_count}){filter_label} ═════════{RESET}")
    print(f"{BOLD}{'USER ID':<15} {'USERNAME':<18} {'ROLE':<12} {'TOKENS':<8} {'BANNED':<8} {'MUTED':<8} {'REGISTERED'}{RESET}")
    print("─" * 84)

    for u in users:
        uname = f"@{u.username}" if u.username else "—"
        effective_role = resolve_user_role(u.user_id, u.role, u.is_admin)

        if effective_role == Role.SUPERADMIN:
            role_badge = f"{MAGENTA}{BOLD}SUPERADMIN{RESET}"
        elif effective_role == Role.ADMIN:
            role_badge = f"{YELLOW}{BOLD}ADMIN{RESET}"
        else:
            role_badge = f"{CYAN}USER{RESET}"

        ban_badge = f"{RED}YES{RESET}" if u.is_banned else f"{GREEN}NO{RESET}"
        mute_badge = f"{RED}YES{RESET}" if getattr(u, "is_muted", False) else f"{GREEN}NO{RESET}"
        reg_date = u.created_at.strftime("%Y-%m-%d") if getattr(u, "created_at", None) else "—"

        print(f"{u.user_id:<15} {uname:<18} {role_badge:<21} {u.tokens:<8} {ban_badge:<17} {mute_badge:<17} {reg_date}")
    print("─" * 84)

async def user_directory_interactive():
    """Interactive paginated browser for registered users with role and flag controls."""
    page = 1
    page_size = 10
    role_filter = None

    while True:
        offset = (page - 1) * page_size
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            users, total_count = await repo.list_users_paginated(
                offset=offset,
                limit=page_size,
                role_filter=role_filter,
            )

        total_pages = max(1, (total_count + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages
            continue

        await display_user_page(users, page, total_pages, total_count, role_filter)

        print(f"{BOLD}Controls:{RESET} [N]ext · [P]rev · [F]ilter · [T]oggle Flag · [B]an · [U]nban · [Q]uit to Menu")
        cmd = input(f"{CYAN}Select action: {RESET}").strip().lower()

        if cmd in ("n", "next"):
            if page < total_pages:
                page += 1
            else:
                print(f"{YELLOW}Already at the last page.{RESET}")
        elif cmd in ("p", "prev", "back"):
            if page > 1:
                page -= 1
            else:
                print(f"{YELLOW}Already at the first page.{RESET}")
        elif cmd in ("f", "filter"):
            print("Role filter choices: 1) ALL  2) ADMIN  3) USER  4) SUPERADMIN")
            fc = input("Enter choice [1-4]: ").strip()
            if fc == "1":
                role_filter = None
            elif fc == "2":
                role_filter = "ADMIN"
            elif fc == "3":
                role_filter = "USER"
            elif fc == "4":
                role_filter = "SUPERADMIN"
            page = 1
        elif cmd in ("t", "toggle"):
            target_str = input("Enter User ID to toggle flags: ").strip()
            if target_str.isdigit():
                uid = int(target_str)
                print("1) Toggle Ban  2) Toggle Mute  3) Promote to Admin  4) Demote to User")
                sub = input("Choice: ").strip()
                if sub == "1":
                    await toggle_user_ban(uid)
                elif sub == "2":
                    await toggle_user_mute(uid)
                elif sub == "3":
                    await promote_user(uid)
                elif sub == "4":
                    await demote_user(uid)
        elif cmd == "b":
            target_str = input("Enter User ID or @username to BAN: ").strip()
            if target_str:
                await ban_user(target_str)
        elif cmd == "u":
            target_str = input("Enter User ID or @username to UNBAN: ").strip()
            if target_str:
                await unban_user(target_str)
        elif cmd in ("q", "quit", "exit"):
            break

async def list_users_cli(limit: int = 15, page: int = 1, role_filter: Optional[str] = None):
    """Non-interactive CLI list of users."""
    offset = (page - 1) * limit
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        users, total_count = await repo.list_users_paginated(
            offset=offset,
            limit=limit,
            role_filter=role_filter,
        )

    total_pages = max(1, (total_count + limit - 1) // limit)
    await display_user_page(users, page, total_pages, total_count, role_filter)

async def ban_user(identifier: str, reason: str = ""):
    """Ban user in PostgreSQL and Redis."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}Error: User '{identifier}' not found in database.{RESET}")
            return

        if is_superadmin(user.user_id):
            print(f"{RED}⛔ Error: Superadmin #{user.user_id} is immune and cannot be banned.{RESET}")
            return

        await repo.set_ban_status(user.user_id, True)
        await redis_client.set(RedisKeys.ban(user.user_id), "banned")
        reason_str = f" Reason: '{reason}'" if reason else ""
        print(f"{GREEN}Successfully BANNED user #{user.user_id} (@{user.username or 'none'}).{reason_str}{RESET}")

async def unban_user(identifier: str):
    """Unban user in PostgreSQL and Redis."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}Error: User '{identifier}' not found in database.{RESET}")
            return

        await repo.set_ban_status(user.user_id, False)
        await redis_client.delete(RedisKeys.ban(user.user_id))
        print(f"{GREEN}Successfully UNBANNED user #{user.user_id} (@{user.username or 'none'}).{RESET}")

async def mute_user(identifier: str, reason: str = ""):
    """Mute conversational privileges for user."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}Error: User '{identifier}' not found in database.{RESET}")
            return

        if is_superadmin(user.user_id):
            print(f"{RED}⛔ Error: Superadmin #{user.user_id} is immune and cannot be muted.{RESET}")
            return

        await repo.set_mute_status(user.user_id, True)
        await redis_client.set(RedisKeys.mute(user.user_id), "muted")
        reason_str = f" Reason: '{reason}'" if reason else ""
        print(f"{GREEN}Successfully MUTED user #{user.user_id} (@{user.username or 'none'}).{reason_str}{RESET}")

async def unmute_user(identifier: str):
    """Restore conversational privileges for user."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}Error: User '{identifier}' not found in database.{RESET}")
            return

        await repo.set_mute_status(user.user_id, False)
        await redis_client.delete(RedisKeys.mute(user.user_id))
        print(f"{GREEN}Successfully UNMUTED user #{user.user_id} (@{user.username or 'none'}).{RESET}")

async def toggle_user_ban(user_id: int):
    """Toggle ban status for target user ID."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(user_id)
        if not user:
            print(f"{RED}User #{user_id} not found.{RESET}")
            return
        if is_superadmin(user.user_id):
            print(f"{RED}Cannot ban Superadmin.{RESET}")
            return

        new_status = not user.is_banned
        await repo.set_ban_status(user_id, new_status)
        if new_status:
            await redis_client.set(RedisKeys.ban(user_id), "banned")
            print(f"{RED}User #{user_id} is now BANNED.{RESET}")
        else:
            await redis_client.delete(RedisKeys.ban(user_id))
            print(f"{GREEN}User #{user_id} is now UNBANNED.{RESET}")

async def toggle_user_mute(user_id: int):
    """Toggle mute status for target user ID."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(user_id)
        if not user:
            print(f"{RED}User #{user_id} not found.{RESET}")
            return
        if is_superadmin(user.user_id):
            print(f"{RED}Cannot mute Superadmin.{RESET}")
            return

        new_status = not getattr(user, "is_muted", False)
        await repo.set_mute_status(user_id, new_status)
        if new_status:
            await redis_client.set(RedisKeys.mute(user_id), "muted")
            print(f"{YELLOW}User #{user_id} is now MUTED.{RESET}")
        else:
            await redis_client.delete(RedisKeys.mute(user_id))
            print(f"{GREEN}User #{user_id} is now UNMUTED.{RESET}")

async def promote_user(identifier: str | int):
    """Superadmin elevates user to ADMIN role."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}User '{identifier}' not found in database.{RESET}")
            return

        if is_superadmin(user.user_id):
            print(f"{YELLOW}User #{user.user_id} is already a SUPERADMIN.{RESET}")
            return

        await repo.set_role(user.user_id, role="ADMIN", is_admin=True)
        await redis_client.set(f"admin_status:{user.user_id}", "admin")
        print(f"{GREEN}👑 Successfully PROMOTED #{user.user_id} (@{user.username or 'none'}) to ADMIN role.{RESET}")

async def demote_user(identifier: str | int):
    """Superadmin strips administrative role from user."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}User '{identifier}' not found in database.{RESET}")
            return

        if is_superadmin(user.user_id):
            print(f"{RED}⛔ Cannot demote SUPERADMIN #{user.user_id} (Immutable sovereign rank).{RESET}")
            return

        await repo.set_role(user.user_id, role="USER", is_admin=False)
        await redis_client.set(f"admin_status:{user.user_id}", "user")
        print(f"{YELLOW}🔰 Successfully DEMOTED #{user.user_id} (@{user.username or 'none'}) to standard USER role.{RESET}")

async def toggle_maintenance(target_state: Optional[str] = None):
    """Toggle or set maintenance mode in Redis."""
    current = await redis_client.get(RedisKeys.maintenance())
    if target_state == "on":
        new_val = "1"
    elif target_state == "off":
        new_val = "0"
    elif target_state == "status":
        status = "ENABLED" if current == "1" else "DISABLED"
        print(f"Maintenance mode is currently: {status}")
        return
    else:
        new_val = "1" if current != "1" else "0"

    await redis_client.set(RedisKeys.maintenance(), new_val)
    status_str = f"{RED}ENABLED (Admins Only){RESET}" if new_val == "1" else f"{GREEN}DISABLED (Normal Ops){RESET}"
    print(f"\nMaintenance mode set to: {status_str}")

async def run_latency_diagnostics():
    """Measure round-trip latency to PostgreSQL, Redis, and public OSM upstream mirrors."""
    print(f"\n{BOLD}═══════════════ REAL-TIME ROUND-TRIP LATENCY DIAGNOSTICS ═══════════════{RESET}\n")

    db_ms = None
    db_err = None
    t0 = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
        db_ms = (time.perf_counter() - t0) * 1000
    except Exception as exc:
        db_err = str(exc).split("\n")[0]

    redis_ms = None
    redis_err = None
    t0 = time.perf_counter()
    try:
        await redis_client.ping()
        redis_ms = (time.perf_counter() - t0) * 1000
    except Exception as exc:
        redis_err = str(exc).split("\n")[0]

    def _color_lat(ms: float | None, err: str | None) -> str:
        if err or ms is None:
            return f"{RED}🔴 FAILED ({err or 'Timeout'}){RESET}"
        if ms < 50.0:
            return f"{GREEN}🟢 {ms:.2f} ms (Lightning){RESET}"
        if ms < 300.0:
            return f"{GREEN}🟢 {ms:.2f} ms (Fast){RESET}"
        if ms < 1000.0:
            return f"{YELLOW}🟡 {ms:.2f} ms (Acceptable){RESET}"
        return f"{RED}🔴 {ms:.2f} ms (High Latency){RESET}"

    print(f" • PostgreSQL Database:   {_color_lat(db_ms, db_err)}")
    print(f" • Redis Cache Store:     {_color_lat(redis_ms, redis_err)}")
    print("─" * 70)
    print(f" {BOLD}Public OpenStreetMap & Overpass Mirrors:{RESET}")

    mirrors = list(dict.fromkeys(NOMINATIM_URLS + OVERPASS_URLS))
    timeout = aiohttp.ClientTimeout(total=3.5)
    headers = {"User-Agent": "Jarvis-Admin-Diagnostics/2.4"}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        for url in mirrors:
            t0 = time.perf_counter()
            err_msg = None
            ms_val = None
            try:
                async with session.get(url) as resp:
                    ms_val = (time.perf_counter() - t0) * 1000
                    if resp.status >= 500:
                        err_msg = f"HTTP {resp.status}"
            except Exception as exc:
                err_msg = type(exc).__name__

            label = url.replace("https://", "").replace("http://", "")
            if len(label) > 42:
                label = label[:39] + "..."
            print(f"   {CYAN}{label:<42}{RESET} -> {_color_lat(ms_val, err_msg)}")

    print(f"\n{BOLD}════════════════════════════════════════════════════════════════════════{RESET}\n")

async def execute_guillotine(identifier: str):
    """
    Satirical alias for banishing a user:
    Displays an ASCII French Revolution / aristocratic decree:
    'The Bourgeoisie has convened: decree of exile executed.'
    """
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}Error: Citizen '{identifier}' was not found within the Imperial Register.{RESET}")
            return

        if is_superadmin(user.user_id):
            print(f"""
{YELLOW}{BOLD}
    ⚔️  INCIDENT DE HAUTE TRAHISON!
    Mon Dieu! The Sovereign Superadmin (#{user.user_id}) cannot be summoned
    before the Revolutionary Tribunal! The guillotine blade fractures on sovereign steel!{RESET}
""")
            return

        await repo.set_ban_status(user.user_id, True)
        await redis_client.set(RedisKeys.ban(user.user_id), "banned")

    print(f"""{RED}{BOLD}
      ╔══════════════════════════════════════════════════════════════════════╗
      ║      ⚖️  RÉPUBLIQUE DE JARVIS — COMITÉ DE SALUT PUBLIC BOURGEOIS  ⚖️    ║
      ║                   DÉCRET OFFICIEL D'EXIL ET DE DÉCHÉANCE             ║
      ╚══════════════════════════════════════════════════════════════════════╝{RESET}
                             {YELLOW}|===|
                             |_|_|
                             |/ \\|
                             |___|
                            /|   |\\
                           /_|===|_\\
                             |   |
                             |___|
                             ( o )
                          =========={RESET}

  {BOLD}📜 "The Bourgeoisie has convened: decree of exile executed."{RESET}

  {RED}Citizen #{user.user_id} (@{user.username or 'sans-culotte'}) has been escorted to the scaffold of banishment.{RESET}
  {DIM}• Access to the Sovereign Realm of Jarvis & Mini App: REVOKED IN PERPETUITY.{RESET}
  {DIM}• Redis Ban Status Key: ENGRAVED IN OBSIDIAN.{RESET}
  {DIM}• Execution Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}{RESET}
  {BOLD}Vive la République, et que l'ordre règne sur le géoportail!{RESET}
""")

async def display_salon():
    """
    Displays an ornate ASCII rococo tea and champagne salon alongside witty
    butler commentary ('A vintage 1982 telemetry dossier for Monsieur, served chilled.')
    """
    stats = await get_system_stats()

    t0 = time.perf_counter()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1;"))
    db_ms = (time.perf_counter() - t0) * 1000

    redis_stats = await redis_client.info("stats")
    hits = int(redis_stats.get("keyspace_hits", 0))
    misses = int(redis_stats.get("keyspace_misses", 0))
    ratio = (hits / (hits + misses) * 100.0) if (hits + misses) > 0 else 100.0

    print(fr"""{YELLOW}{BOLD}
      ╔══════════════════════════════════════════════════════════════════════╗
      ║             🥂  LE SALON ROCOCO DE HAUTE TÉLÉMÉTRIE  ☕             ║
      ║         Dégustation Impériale · Champagne Brut & Grand Luxe          ║
      ╚══════════════════════════════════════════════════════════════════════╝{RESET}
                    {MAGENTA}_.-''''-._
                  .'  __/\__  '.
                 /   /  ||  \   \\       {CYAN}"A vintage 1982 telemetry dossier{RESET}
                |   |  .||.  |   |       {CYAN}for Monsieur, served chilled."{RESET}
                 \\   \\  ||  /   /
                  '.  ¯¯\/¯¯  .'            {DIM}~ Butler Jarvis, Premier Sommelier{RESET}
                    '-.____.-'
                     (______)
                     (______)
                     (______){RESET}

  {BOLD}🎩 MESSIEURS, VOICI VOTRE BILAN ARISTOCRATIQUE:{RESET}
  {BOLD}──────────────────────────────────────────────────────────────────────{RESET}
  • {YELLOW}Souverain en Chef:{RESET}         Superadmin #{BOT_OWNER_ID or (SUPERADMINS[0] if SUPERADMINS else 'Inconnu')}
  • {CYAN}Cave de PostgreSQL:{RESET}        {stats['users']} sujets recensés ({stats['admin_users']} officiers de cour)
  • {CYAN}Trésor Géographique:{RESET}       {stats['places']} monuments impériaux & {stats['cached_cities']} cités cartographiées
  • {CYAN}Dossiers d'Itinéraires:{RESET}    {stats['history']} expéditions enregistrées au journal impérial
  • {GREEN}Bouquet de Clés Redis:{RESET}     Ratio de dégustation cache: {ratio:.1f}% ({hits} hits précieux)
  • {GREEN}Latence de la Couronne:{RESET}    Postgres: {db_ms:.2f} ms de noble vélocité
  {BOLD}──────────────────────────────────────────────────────────────────────{RESET}
  {DIM}Que Monsieur daigne poursuivre son règne sereinement sur le royaume numérique.{RESET}
""")

async def interactive_menu(active_superadmin_id: int):
    """Interactive administrative loop."""
    print_banner(active_superadmin_id)
    while True:
        print(f"""
{BOLD}SELECT ACTION (SUPERADMIN PRIVILEGE):{RESET}
  {CYAN}1{RESET}) 📊 System Statistics & Metrics
  {CYAN}2{RESET}) 👥 Superadmin User Directory (Pagination & RBAC Controls)
  {CYAN}3{RESET}) 🧹 Vacuum & Analyze Database (PostgreSQL Optimizer)
  {CYAN}4{RESET}) 📜 Alembic Schema Migrations Status
  {CYAN}5{RESET}) ⚡ Redis & Cache Performance (Hit/Miss Ratios & Memory)
  {CYAN}6{RESET}) 🌐 Real-Time Round-Trip Latency Diagnostics
  {CYAN}7{RESET}) 🚫 Ban User
  {CYAN}8{RESET}) ✅ Unban User
  {CYAN}9{RESET}) 🔇 Mute User / 🔊 Unmute User
  {CYAN}10{RESET}) 👑 Promote to Admin / 🔰 Demote to User
  {CYAN}11{RESET}) ⚙️  Toggle Maintenance Mode
  {CYAN}12{RESET}) 🏙️  Clear Regional City Cache
  {CYAN}13{RESET}) ⚔️  Guillotine Execution Decree (Satirical Ban)
  {CYAN}14{RESET}) 🥂 Le Salon Rococo (Vintage Telemetry Dossier)
  {CYAN}0{RESET}) 🚪 Exit Admin Console
""")
        choice = input(f"{BOLD}Enter choice [0-14]: {RESET}").strip()

        if choice == "1":
            await show_stats()
        elif choice == "2":
            await user_directory_interactive()
        elif choice == "3":
            await run_db_vacuum_analyze()
        elif choice == "4":
            await show_schema_migrations()
        elif choice == "5":
            await show_redis_metrics()
        elif choice == "6":
            await run_latency_diagnostics()
        elif choice == "7":
            target = input("Enter User ID or @username to BAN: ").strip()
            reason = input("Enter reason (optional): ").strip()
            if target:
                await ban_user(target, reason)
        elif choice == "8":
            target = input("Enter User ID or @username to UNBAN: ").strip()
            if target:
                await unban_user(target)
        elif choice == "9":
            sub = input("1) MUTE user  2) UNMUTE user: ").strip()
            target = input("Enter User ID or @username: ").strip()
            if sub == "1" and target:
                reason = input("Enter reason (optional): ").strip()
                await mute_user(target, reason)
            elif sub == "2" and target:
                await unmute_user(target)
        elif choice == "10":
            sub = input("1) PROMOTE to Admin  2) DEMOTE to User: ").strip()
            target = input("Enter User ID or @username: ").strip()
            if sub == "1" and target:
                await promote_user(target)
            elif sub == "2" and target:
                await demote_user(target)
        elif choice == "11":
            await toggle_maintenance()
        elif choice == "12":
            city = input("Enter city name to clear cache: ").strip()
            if city:
                await clear_city_cache(city)
        elif choice == "13":
            target = input("Enter citizen ID or @username to summon to the guillotine: ").strip()
            if target:
                await execute_guillotine(target)
        elif choice == "14":
            await display_salon()
        elif choice in ("0", "q", "exit"):
            print(f"{CYAN}Exiting JARVIS Admin Console. Goodbye Monsieur!{RESET}")
            break
        else:
            print(f"{RED}Invalid option. Please choose 0-14.{RESET}")

async def main(args: list[str]):
    clean_args = []
    caller_id = None
    mock_auth = os.getenv("MOCK_AUTH") == "1" or os.getenv("JARVIS_MOCK_AUTH") == "1"

    i = 0
    while i < len(args):
        a = args[i].lower()
        if a in ("--auth=0", "--mock-auth", "--no-auth", "-m"):
            mock_auth = True
        elif a == "--auth" and i + 1 < len(args) and args[i + 1].strip() == "0":
            mock_auth = True
            i += 1
        elif a in ("--user", "--caller-id", "--superadmin-id") and i + 1 < len(args):
            if args[i + 1].strip().isdigit():
                caller_id = int(args[i + 1].strip())
            i += 1
        elif a.startswith("--user="):
            val = a.split("=", 1)[1]
            if val.isdigit():
                caller_id = int(val)
        else:
            clean_args.append(args[i])
        i += 1

    if mock_auth:
        os.environ["MOCK_AUTH"] = "1"
        os.environ["JARVIS_MOCK_AUTH"] = "1"
        print(f"{YELLOW}🔓 [Mock Auth] Running with mock authentication enabled (--auth=0).{RESET}")

    active_superadmin_id = verify_cli_access(caller_id)

    args = clean_args

    try:
        if not args or args[0] in ("-i", "--interactive"):
            await interactive_menu(active_superadmin_id)
            return

        cmd = args[0].lower()
        if cmd in ("stats", "-s", "--stats"):
            await show_stats()
        elif cmd in ("db-vacuum", "vacuum"):
            await run_db_vacuum_analyze()
        elif cmd in ("migrations", "migrate-check"):
            await show_schema_migrations()
        elif cmd in ("redis-metrics", "redis", "cache"):
            await show_redis_metrics()
        elif cmd in ("latency", "diag", "diagnostics"):
            await run_latency_diagnostics()
        elif cmd in ("users", "-u"):
            limit = 15
            page = 1
            role_filter = None
            j = 1
            while j < len(args):
                if args[j].isdigit():
                    limit = int(args[j])
                elif args[j] in ("--page", "-p") and j + 1 < len(args) and args[j + 1].isdigit():
                    page = int(args[j + 1])
                    j += 1
                elif args[j] in ("--role", "-r") and j + 1 < len(args):
                    role_filter = args[j + 1].upper()
                    j += 1
                j += 1
            await list_users_cli(limit=limit, page=page, role_filter=role_filter)
        elif cmd == "ban":
            if len(args) < 2:
                print("Usage: ./Jarvis -a ban <user_id_or_username> [reason]")
                return
            reason = " ".join(args[2:]) if len(args) > 2 else ""
            await ban_user(args[1], reason)
        elif cmd == "unban":
            if len(args) < 2:
                print("Usage: ./Jarvis -a unban <user_id_or_username>")
                return
            await unban_user(args[1])
        elif cmd == "mute":
            if len(args) < 2:
                print("Usage: ./Jarvis -a mute <user_id_or_username> [reason]")
                return
            reason = " ".join(args[2:]) if len(args) > 2 else ""
            await mute_user(args[1], reason)
        elif cmd == "unmute":
            if len(args) < 2:
                print("Usage: ./Jarvis -a unmute <user_id_or_username>")
                return
            await unmute_user(args[1])
        elif cmd == "promote":
            if len(args) < 2:
                print("Usage: ./Jarvis -a promote <user_id_or_username>")
                return
            await promote_user(args[1])
        elif cmd == "demote":
            if len(args) < 2:
                print("Usage: ./Jarvis -a demote <user_id_or_username>")
                return
            await demote_user(args[1])
        elif cmd in ("maintenance", "maint"):
            target = args[1] if len(args) > 1 else None
            await toggle_maintenance(target)
        elif cmd in ("clear-city", "clear_city"):
            if len(args) < 2:
                print("Usage: ./Jarvis -a clear-city <city_name>")
                return
            await clear_city_cache(" ".join(args[1:]))
        elif cmd in ("clear-redis", "clear_redis"):
            await clear_all_redis()
        elif cmd == "guillotine":
            if len(args) < 2:
                print("Usage: ./Jarvis -a guillotine <user_id_or_username>")
                return
            await execute_guillotine(args[1])
        elif cmd == "salon":
            await display_salon()
        else:
            print(f"{RED}Unknown admin command: {cmd}{RESET}")
            print("Run './Jarvis -a' without arguments for interactive console mode.")
    finally:
        try:
            if hasattr(redis_client, "aclose"):
                await redis_client.aclose()
            else:
                await redis_client.close()
        except Exception:
            pass
        try:
            await engine.dispose()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
