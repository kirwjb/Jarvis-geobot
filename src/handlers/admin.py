"""
Legacy in-chat admin handlers have been migrated to the standalone CLI tool.

Use the standalone console tool via:
    Jarvis -a
or:
    python jarvis.py -a
"""

from telebot.async_telebot import AsyncTeleBot

async def register_admin_handlers(bot: AsyncTeleBot, redis_client=None):
    """No-op stub for backwards compatibility. Administration is now performed via 'Jarvis -a'."""
    pass