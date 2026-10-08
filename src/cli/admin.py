"""
Standalone Admin Console for JARVIS GeoBot.

Replaces legacy in-chat admin commands. Can be executed as:
    Jarvis -a
    python jarvis.py -a
    python -m src.cli.admin [options]
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, select, update
from src.database.db import AsyncSessionLocal
from src.database.models import Favorite, History, OsmCache, Place, PlacePhoto, User
from src.database.repositories.user_repo import UserRepository
from src.database.session_manager import redis_client
from src.utils.redis_keys import RedisKeys

# ANSI color codes for clean terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════╗
║               🛠️  JARVIS ADMIN CONSOLE                      ║
║            Standalone Management & Diagnostics               ║
╚══════════════════════════════════════════════════════════════╝{RESET}""")


async def get_system_stats() -> dict:
    """Fetch system-wide statistics from PostgreSQL and Redis."""
    async with AsyncSessionLocal() as session:
        user_count = await session.scalar(select(func.count(User.user_id))) or 0
        banned_count = (
            await session.scalar(
                select(func.count(User.user_id)).where(User.is_banned == True)
            )
            or 0
        )
        admin_count = (
            await session.scalar(
                select(func.count(User.user_id)).where(User.is_admin == True)
            )
            or 0
        )
        cache_count = await session.scalar(select(func.count(OsmCache.id))) or 0
        place_count = await session.scalar(select(func.count(Place.id))) or 0
        photo_count = (
            await session.scalar(select(func.count(PlacePhoto.id))) or 0
        )
        fav_count = await session.scalar(select(func.count(Favorite.id))) or 0
        history_count = await session.scalar(select(func.count(History.id))) or 0

    m_val = await redis_client.get(RedisKeys.maintenance())
    maintenance_active = m_val == "1"

    try:
        redis_ok = await redis_client.ping()
    except Exception:
        redis_ok = False

    return {
        "users": user_count,
        "banned_users": banned_count,
        "admin_users": admin_count,
        "cached_cities": cache_count,
        "places": place_count,
        "photos": photo_count,
        "favorites": fav_count,
        "history": history_count,
        "maintenance": maintenance_active,
        "redis_ok": redis_ok,
    }


async def show_stats():
    """Print formatted statistics report."""
    stats = await get_system_stats()
    m_color = RED if stats["maintenance"] else GREEN
    m_text = "ENABLED (Admins Only)" if stats["maintenance"] else "DISABLED (Normal Ops)"
    r_color = GREEN if stats["redis_ok"] else RED
    r_text = "ONLINE" if stats["redis_ok"] else "OFFLINE"

    print(f"\n{BOLD}═══════════════ SYSTEM DIAGNOSTICS & METRICS ═══════════════{RESET}")
    print(f" • Maintenance Mode:     {m_color}{m_text}{RESET}")
    print(f" • Redis Status:          {r_color}{r_text}{RESET}")
    print(f" • Registered Users:      {CYAN}{stats['users']}{RESET} (Banned: {RED}{stats['banned_users']}{RESET}, Admins: {YELLOW}{stats['admin_users']}{RESET})")
    print(f" • Cached OSM Cities:     {CYAN}{stats['cached_cities']}{RESET}")
    print(f" • Total Stored Places:   {CYAN}{stats['places']}{RESET}")
    print(f" • Cached Place Photos:   {CYAN}{stats['photos']}{RESET}")
    print(f" • User Saved Favorites:  {CYAN}{stats['favorites']}{RESET}")
    print(f" • Saved Trip Histories:  {CYAN}{stats['history']}{RESET}")
    print(f"{BOLD}═════════════════════════════════════════════════════════════{RESET}\n")


async def list_users(limit: int = 15):
    """List recent users in database."""
    async with AsyncSessionLocal() as session:
        query = select(User).order_by(User.user_id.desc()).limit(limit)
        result = await session.execute(query)
        users = result.scalars().all()

        if not users:
            print(f"{YELLOW}No users found in database.{RESET}")
            return

        print(f"\n{BOLD}{'USER ID':<16} {'USERNAME':<20} {'TOKENS':<8} {'BANNED':<8} {'ADMIN'}{RESET}")
        print("─" * 65)
        for u in users:
            uname = f"@{u.username}" if u.username else "—"
            ban = f"{RED}YES{RESET}" if u.is_banned else f"{GREEN}NO{RESET}"
            admin = f"{YELLOW}YES{RESET}" if u.is_admin else "NO"
            print(f"{u.user_id:<16} {uname:<20} {u.tokens:<8} {ban:<17} {admin}")
        print("─" * 65)


async def ban_user(identifier: str):
    """Ban user in PostgreSQL and Redis."""
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(identifier)
        if not user:
            print(f"{RED}Error: User '{identifier}' not found in database.{RESET}")
            return

        await repo.set_ban_status(user.user_id, True)
        await redis_client.set(RedisKeys.ban(user.user_id), "1")
        print(f"{GREEN}Successfully BANNED user #{user.user_id} (@{user.username or 'none'}).{RESET}")


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


async def clear_city_cache(city: str):
    """Clear OSM, Place, Photo and Weather cache for a city."""
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
    """Clear app Redis caches."""
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


async def interactive_menu():
    """Interactive loop for CLI administration."""
    print_banner()
    while True:
        print(f"""
{BOLD}SELECT ACTION:{RESET}
  {CYAN}1{RESET}) 📊 System Statistics
  {CYAN}2{RESET}) 👥 List Recent Users
  {CYAN}3{RESET}) 🚫 Ban User
  {CYAN}4{RESET}) ✅ Unban User
  {CYAN}5{RESET}) ⚙️  Toggle Maintenance Mode
  {CYAN}6{RESET}) 🧹 Clear City Cache
  {CYAN}7{RESET}) 🔄 Flush Transient Redis Caches
  {CYAN}0{RESET}) 🚪 Exit
""")
        choice = input(f"{BOLD}Enter choice [0-7]: {RESET}").strip()

        if choice == "1":
            await show_stats()
        elif choice == "2":
            lim = input("How many users to display? [default 15]: ").strip()
            limit_val = int(lim) if lim.isdigit() else 15
            await list_users(limit=limit_val)
        elif choice == "3":
            target = input("Enter User ID or @username to BAN: ").strip()
            if target:
                await ban_user(target)
        elif choice == "4":
            target = input("Enter User ID or @username to UNBAN: ").strip()
            if target:
                await unban_user(target)
        elif choice == "5":
            await toggle_maintenance()
        elif choice == "6":
            city = input("Enter city name to clear cache: ").strip()
            if city:
                await clear_city_cache(city)
        elif choice == "7":
            confirm = input("Clear transient weather & session Redis caches? (y/N): ").strip().lower()
            if confirm == "y":
                await clear_all_redis()
        elif choice in ("0", "q", "exit"):
            print(f"{CYAN}Exiting JARVIS Admin Console. Goodbye!{RESET}")
            break
        else:
            print(f"{RED}Invalid option. Please choose 0-7.{RESET}")


async def main(args: list[str]):
    # Extract mock auth flags if passed directly
    clean_args = []
    mock_auth = os.getenv("MOCK_AUTH") == "1" or os.getenv("JARVIS_MOCK_AUTH") == "1"
    i = 0
    while i < len(args):
        a = args[i].lower()
        if a in ("--auth=0", "--mock-auth", "--no-auth", "-m"):
            mock_auth = True
        elif a == "--auth" and i + 1 < len(args) and args[i + 1].strip() == "0":
            mock_auth = True
            i += 1
        else:
            clean_args.append(args[i])
        i += 1

    if mock_auth:
        os.environ["MOCK_AUTH"] = "1"
        os.environ["JARVIS_MOCK_AUTH"] = "1"
        print(f"{YELLOW}🔓 [Mock Auth] Running with mock authentication enabled (--auth=0).{RESET}\n")

    args = clean_args

    try:
        if not args or args[0] in ("-i", "--interactive"):
            await interactive_menu()
            return

        cmd = args[0].lower()
        if cmd in ("stats", "-s", "--stats"):
            await show_stats()
        elif cmd in ("users", "-u"):
            lim = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
            await list_users(limit=lim)
        elif cmd == "ban":
            if len(args) < 2:
                print("Usage: Jarvis -a ban <user_id_or_username>")
                return
            await ban_user(args[1])
        elif cmd == "unban":
            if len(args) < 2:
                print("Usage: Jarvis -a unban <user_id_or_username>")
                return
            await unban_user(args[1])
        elif cmd in ("maintenance", "maint"):
            target = args[1] if len(args) > 1 else None
            await toggle_maintenance(target)
        elif cmd in ("clear-city", "clear_city"):
            if len(args) < 2:
                print("Usage: Jarvis -a clear-city <city_name>")
                return
            await clear_city_cache(" ".join(args[1:]))
        elif cmd in ("clear-redis", "clear_redis"):
            await clear_all_redis()
        else:
            print(f"Unknown admin command: {cmd}")
            print("Run 'Jarvis -a' without arguments for interactive console mode.")
    finally:
        try:
            if hasattr(redis_client, "aclose"):
                await redis_client.aclose()
            else:
                await redis_client.close()
        except Exception:
            pass
        try:
            from src.database.db import engine
            await engine.dispose()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
