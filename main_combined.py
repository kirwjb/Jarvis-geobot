import asyncio
import html
import logging
import os
import re
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
from src.handlers.admin import register_admin_handlers
from src.utils.languages import get_text
from src.utils.utils import log, error

from src.routers.api_integrated import app as fastapi_app
from src.routers.wikimedia_photos import router as wikimedia_photos_router, poi_router

WEB_DIR = Path(__file__).resolve().parent / "frontend"
MEDIA_DIR = Path(__file__).resolve().parent / "media"
INDEX_FILE = WEB_DIR / "index.html"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

fastapi_app.include_router(wikimedia_photos_router)
fastapi_app.include_router(poi_router)

fastapi_app.mount(
    "/media",
    StaticFiles(directory=str(MEDIA_DIR)),
    name="media",
)

LEGAL_FILE = Path(__file__).resolve().parent / "LEGAL.MD"

def _render_legal_html_page(md: str) -> str:
    lines = md.splitlines()
    body_parts = []
    in_list = False
    in_quote = False
    quote_buf = []

    def flush_list():
        nonlocal in_list
        if in_list:
            body_parts.append('</ul>')
            in_list = False

    def flush_quote():
        nonlocal in_quote, quote_buf
        if in_quote:
            q_html = '<br>'.join(format_inline(l) for l in quote_buf)
            body_parts.append(f'<blockquote class="legal-blockquote">{q_html}</blockquote>')
            in_quote = False
            quote_buf = []

    def format_inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer" class="legal-link">\1</a>', s)
        s = re.sub(r'\*\*\*([^*]+)\*\*\*', r'<strong><em>\1</em></strong>', s)
        s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', s)
        s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
        return s

    for line in lines:
        t = line.strip()
        if t.startswith('> ') or t == '>':
            flush_list()
            in_quote = True
            quote_buf.append(re.sub(r'^>\s?', '', t))
            continue
        else:
            flush_quote()

        if re.match(r'^(\-{3,}|\*{3,}|_{3,})$', t):
            flush_list()
            body_parts.append('<hr class="legal-divider">')
            continue

        if t.startswith('# '):
            flush_list()
            body_parts.append(f'<h1 class="legal-h1">{format_inline(t[2:])}</h1>')
            continue
        if t.startswith('## '):
            flush_list()
            body_parts.append(f'<h2 class="legal-h2">{format_inline(t[3:])}</h2>')
            continue
        if t.startswith('### '):
            flush_list()
            body_parts.append(f'<h3 class="legal-h3">{format_inline(t[4:])}</h3>')
            continue

        lm = re.match(r'^[-*•]\s+(.*)$', t)
        if lm:
            if not in_list:
                body_parts.append('<ul class="legal-list">')
                in_list = True
            body_parts.append(f'<li>{format_inline(lm.group(1))}</li>')
            continue
        else:
            flush_list()

        if not t:
            continue

        body_parts.append(f'<p class="legal-p">{format_inline(t)}</p>')

    flush_list()
    flush_quote()
    rendered_body = '\n'.join(body_parts)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>JARVIS LEGAL COMPLIANCE</title>
<style>
  :root {{
    --bg: #0b0f19;
    --card: #131b2e;
    --text: #f8fafc;
    --text-soft: #cbd5e1;
    --border: rgba(255,255,255,0.1);
    --accent: #38bdf8;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #0f172a;
      --text-soft: #334155;
      --border: rgba(0,0,0,0.1);
      --accent: #0284c7;
    }}
  }}
  body {{
    margin: 0;
    padding: 24px 16px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.65;
  }}
  .container {{
    max-width: 760px;
    margin: 0 auto;
    background: var(--card);
    padding: 32px 24px;
    border-radius: 20px;
    border: 1px solid var(--border);
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  }}
  .legal-h1 {{ font-size: 20px; line-height: 1.35; margin: 0 0 20px 0; color: var(--text); }}
  .legal-h2 {{ font-size: 17px; margin: 28px 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid var(--border); color: var(--text); }}
  .legal-h3 {{ font-size: 15px; margin: 20px 0 8px 0; color: var(--text); }}
  .legal-p {{ margin: 0 0 14px 0; color: var(--text-soft); font-size: 14px; }}
  .legal-p strong, strong {{ color: var(--text); font-weight: 600; }}
  .legal-blockquote {{
    margin: 16px 0 20px 0;
    padding: 12px 18px;
    background: rgba(56, 189, 248, 0.08);
    border-left: 3px solid var(--accent);
    border-radius: 0 12px 12px 0;
    font-size: 13px;
    color: var(--text-soft);
  }}
  .legal-divider {{ border: 0; height: 1px; background: var(--border); margin: 24px 0; }}
  .legal-list {{ margin: 0 0 16px 0; padding-left: 24px; }}
  .legal-list li {{ margin-bottom: 8px; color: var(--text-soft); font-size: 14px; }}
  .legal-link {{ color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }}
  .back-bar {{ margin-bottom: 20px; }}
  .btn-back {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 99px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--accent);
    text-decoration: none;
    font-size: 13px;
    font-weight: 500;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="back-bar"><a href="/" class="btn-back">← Назад в Jarvis</a></div>
  {rendered_body}
</div>
</body>
</html>"""

@fastapi_app.get("/LEGAL.MD")
@fastapi_app.get("/legal.md")
async def serve_legal_document(request: Request, raw: bool = False):
    if not LEGAL_FILE.exists():
        return HTMLResponse("Legal document not found", status_code=404)

    accept = request.headers.get("accept", "")
    # Return raw markdown for fetch API or explicit raw query
    if raw or "text/markdown" in accept or "text/plain" in accept or ("*/*" in accept and not accept.startswith("text/html")):
        return FileResponse(
            str(LEGAL_FILE),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'inline; filename="LEGAL.MD"'}
        )

    # Return beautifully rendered HTML for browser navigation
    content = LEGAL_FILE.read_text(encoding="utf-8")
    return HTMLResponse(_render_legal_html_page(content))

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
    await register_start_handlers(bot)
    await register_admin_handlers(bot, redis_client)
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
                headers={"Cache-Control": "no-cache"},
            )
        return FileResponse(
            INDEX_FILE,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"},
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
