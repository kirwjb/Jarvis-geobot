import asyncio
import logging
import redis.asyncio as redis
from telebot.async_telebot import AsyncTeleBot
from src.config import TOKEN, REDIS_HOST, REDIS_PORT
from src.database.db import engine
from src.database.models import Base
from src.database.session_manager import redis_client
from src.middleware.security import SecurityMiddleware
from src.handlers.admin import register_admin_handlers
#from src.handlers.users import register_user_handlers
from src.utils.languages import get_text
from src.utils.utils import log, error, logger 

logger = logging.getLogger('telebot')
logger.setLevel(logging.CRITICAL)


async def main():
    
    bot = AsyncTeleBot(TOKEN)
    
    security_mw = SecurityMiddleware(redis_client)
    bot.setup_middleware(security_mw)

    await register_admin_handlers(bot, redis_client)

    log(get_text("bot_started"))
    await bot.infinity_polling(allowed_updates=['message', 'callback_query'])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log(get_text("bot_stopped"))
    except SystemExit:
        log(get_text("bot_stopped"))
    except Exception as e:
        error(get_text("bot_stopped_with_error", e=str(e)))
        logger.exception("Unhandled exception in main: %s", e)