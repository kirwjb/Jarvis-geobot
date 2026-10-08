import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from telebot.async_telebot import AsyncTeleBot
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.config import TOKEN
from src.database.session_manager import redis_client
from src.middleware.security import SecurityMiddleware
from src.handlers.start import register_start_handlers
from src.utils.languages import get_text
from src.utils.utils import log, error

from src.routers.api_integrated import app as fastapi_app
from src.routers.photo_warmup import router as photo_warmup_router
from src.routers.wikimedia_photos import router as wikimedia_photos_router

WEB_DIR = Path(__file__).resolve().parent / "frontend"
MEDIA_DIR = Path(__file__).resolve().parent / "media"
INDEX_FILE = WEB_DIR / "index.html"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Register routers first
fastapi_app.include_router(photo_warmup_router)
fastapi_app.include_router(wikimedia_photos_router)

# Mount media static files
fastapi_app.mount(
    "/media",
    StaticFiles(directory=str(MEDIA_DIR)),
    name="media",
)

# Mount frontend static files
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
    # Only welcoming start handler serving as database entry point is registered
    await register_start_handlers(bot)
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
async def security_and_csp_headers(request: Request, call_next):
    """Ensure strict CSP, CORS headers, Referrer-Policy and header compatibility for Telegram Mini App."""
    if request.method == "OPTIONS":
        from fastapi.responses import Response
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
                "ngrok-skip-browser-warning": "true",
            },
        )

    response = await call_next(request)
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'; "
        "script-src 'self' https: 'unsafe-inline' 'unsafe-eval' https://telegram.org https://*.telegram.org; "
        "style-src 'self' https: 'unsafe-inline'; "
        "img-src 'self' https: data: blob: https://upload.wikimedia.org https://commons.wikimedia.org https://*.wikimedia.org; "
        "connect-src 'self' https: wss: ws:; "
        "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org tg:;"
    )
    # Remove X-Frame-Options to allow Telegram WebApp iframe embedding
    if "x-frame-options" in response.headers:
        del response.headers["x-frame-options"]
    return response


@fastapi_app.middleware("http")
async def serve_geoapp_root(request: Request, call_next):
    if request.method == "GET" and (request.url.path == "/" or request.url.path == "/index.html"):
        mock_auth = os.getenv("MOCK_AUTH") == "1" or os.getenv("JARVIS_MOCK_AUTH") == "1"
        if mock_auth and INDEX_FILE.exists():
            html_text = INDEX_FILE.read_text(encoding="utf-8")
            mock_script = (
                '<script id="jarvis-mock-auth">'
                'window.JARVIS_MOCK_AUTH=true;'
                'window.JARVIS_MOCK_USER={id:999999999,first_name:"Admin",username:"mock_admin",is_admin:true};'
                'window.Telegram=window.Telegram||{};'
                'window.Telegram.WebApp=window.Telegram.WebApp||{'
                'initData:"mock_auth",'
                'initDataUnsafe:{user:window.JARVIS_MOCK_USER},'
                'colorScheme:"dark",'
                'themeParams:{},'
                'ready:function(){},expand:function(){},close:function(){},'
                'setHeaderColor:function(){},setBackgroundColor:function(){},'
                'onEvent:function(){},offEvent:function(){},sendData:function(){},'
                'HapticFeedback:{impactOccurred:function(){},notificationOccurred:function(){},selectionChanged:function(){}}'
                '};'
                '</script>'
            )
            if "</head>" in html_text:
                html_text = html_text.replace("</head>", f"{mock_script}\n</head>")
            return HTMLResponse(
                html_text,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )
        return FileResponse(
            INDEX_FILE,
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return await call_next(request)


if __name__ == "__main__":
    try:
        server_port = int(os.environ.get("PORT", "8000"))
        uvicorn.run(
            fastapi_app,
            host="0.0.0.0",
            port=server_port,
            log_level="info",
        )
    except KeyboardInterrupt:
        log(get_text("bot_stopped"))
    except Exception as exc:
        error(get_text("bot_stopped_with_error", e=str(exc)))
        logger.exception("Unhandled exception in main: %s", exc)
