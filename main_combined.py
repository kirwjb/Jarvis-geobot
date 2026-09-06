import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from telebot.async_telebot import AsyncTeleBot
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import TOKEN
from src.database.session_manager import redis_client
from src.middleware.security import SecurityMiddleware
from src.handlers.admin import register_admin_handlers
from src.handlers.cache_admin import register_cache_admin_handler
from src.utils.languages import get_text
from src.utils.utils import log, error

from src.routers.api_integrated import app as fastapi_app

WEB_DIR = Path(__file__).resolve().parent / "frontend"
MEDIA_DIR = Path(__file__).resolve().parent / "media"
INDEX_FILE = WEB_DIR / "index.html"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

fastapi_app.mount(
    "/media",
    StaticFiles(directory=str(MEDIA_DIR)),
    name="media",
)
fastapi_app.mount(
    "/",
    StaticFiles(directory=str(WEB_DIR), html=True),
    name="geoapp",
)

logger = logging.getLogger("telebot")
logger.setLevel(logging.CRITICAL)

bot = AsyncTeleBot(TOKEN)
security_mw = SecurityMiddleware(redis_client)
bot.setup_middleware(security_mw)


async def init_bot():
    await register_admin_handlers(bot, redis_client)
    await register_cache_admin_handler(bot)
    log(get_text("bot_started"))


async def run_bot():
    await bot.infinity_polling(
        allowed_updates=["message", "callback_query"]
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_bot()
    bot_task = asyncio.create_task(run_bot())
    log(get_text("FastAPI started"))
    try:
        yield
    finally:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        log(get_text("bot_stopped"))


fastapi_app.router.lifespan_context = lifespan


@fastapi_app.middleware("http")
async def serve_geoapp_root(request: Request, call_next):
    if request.method == "GET" and request.url.path == "/":
        return FileResponse(INDEX_FILE, media_type="text/html")
    return await call_next(request)


if __name__ == "__main__":
    try:
        uvicorn.run(
            fastapi_app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )
    except KeyboardInterrupt:
        log(get_text("bot_stopped"))
    except Exception as exc:
        error(get_text("bot_stopped_with_error", e=str(exc)))
        logger.exception("Unhandled exception in main: %s", exc)
