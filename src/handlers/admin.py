"""Telegram In-Chat Moderation and Governance Handlers for JARVIS Ecosystem.

Accessible to ADMIN and SUPERADMIN:
    /ban <user_id | @username> [reason]
    /unban <user_id | @username>
    /mute <user_id | @username> [reason]
    /unmute <user_id | @username>
    /user <user_id | @username>
    /broadcast <text>

Accessible exclusively to SUPERADMIN:
    /promote <user_id | @username>
    /demote <user_id | @username>
    /maintenance [on|off]
"""

import asyncio
from datetime import datetime
from telebot import types
from telebot.async_telebot import AsyncTeleBot

from src.database.db import AsyncSessionLocal
from src.database.repositories.user_repo import UserRepository
from src.database.session_manager import redis_client as default_redis
from src.services.rbac import (
    Role,
    can_govern,
    can_moderate,
    can_target_user,
    is_superadmin,
    resolve_user_role,
)
from src.utils.redis_keys import RedisKeys
from src.utils.utils import admin_logger

async def _get_caller_role(user_id: int) -> Role:
    """Fetch effective role of the command caller."""
    if is_superadmin(user_id):
        return Role.SUPERADMIN
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_identifier(user_id)
        if not user:
            return Role.USER
        return resolve_user_role(user.user_id, user.role, user.is_admin)

def _parse_command_args(text: str) -> tuple[str, str]:
    """Split command text into (target_identifier, remaining_text)."""
    parts = text.strip().split(maxsplit=2)
    target = parts[1].strip() if len(parts) > 1 else ""
    remaining = parts[2].strip() if len(parts) > 2 else ""
    return target, remaining

async def register_admin_handlers(bot: AsyncTeleBot, redis_client=None):
    """Register moderation and governance commands on the bot instance."""
    redis = redis_client or default_redis

    @bot.message_handler(commands=["admin", "moderation", "admin_help"])
    async def cmd_admin_help(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_moderate(caller_role):
            await bot.reply_to(message, "⚠️ У вас нет прав администратора.")
            return

        help_text = [
            "🛡️ <b>JARVIS MODERATION CONTROL PANEL</b>",
            f"👤 Ваша роль: <b>{caller_role.value}</b>",
            "",
            "<b>Команды модерации (ADMIN & SUPERADMIN):</b>",
            "• <code>/ban &lt;id|@username&gt; [причина]</code> — Заблокировать доступ",
            "• <code>/unban &lt;id|@username&gt;</code> — Разблокировать пользователя",
            "• <code>/mute &lt;id|@username&gt; [причина]</code> — Запретить общение с ботом",
            "• <code>/unmute &lt;id|@username&gt;</code> — Вернуть право общения",
            "• <code>/user &lt;id|@username&gt;</code> — Досье пользователя и статистика",
            "• <code>/broadcast &lt;текст&gt;</code> — Безопасная рассылка активным пользователям",
        ]

        if can_govern(caller_role):
            help_text.extend([
                "",
                "<b>Команды управления (SUPERADMIN ONLY):</b>",
                "• <code>/promote &lt;id|@username&gt;</code> — Назначить администратором",
                "• <code>/demote &lt;id|@username&gt;</code> — Разжаловать до пользователя",
                "• <code>/maintenance [on|off]</code> — Переключить режим техобслуживания",
            ])

        await bot.reply_to(message, "\n".join(help_text), parse_mode="HTML")

    @bot.message_handler(commands=["ban"])
    async def cmd_ban(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_moderate(caller_role):
            await bot.reply_to(message, "⚠️ У вас нет прав администратора.")
            return

        target_id, reason = _parse_command_args(message.text)
        if not target_id:
            await bot.reply_to(message, "❌ Использование: <code>/ban &lt;user_id | @username&gt; [причина]</code>", parse_mode="HTML")
            return

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            target = await repo.get_by_identifier(target_id)
            if not target:
                await bot.reply_to(message, f"❌ Пользователь <code>{target_id}</code> не найден в базе данных.", parse_mode="HTML")
                return

            target_role = resolve_user_role(target.user_id, target.role, target.is_admin)
            if not can_target_user(caller_role, target_role):
                if target_role == Role.SUPERADMIN:
                    await bot.reply_to(message, "⛔ Ошибка: Суперадминистратор неприкосновенен и не может быть заблокирован.")
                else:
                    await bot.reply_to(message, "⛔ Ошибка: Администратор не может блокировать другого администратора.")
                return

            await repo.set_ban_status(target.user_id, True)
            await redis.set(RedisKeys.ban(target.user_id), "banned")
            admin_logger.info("User #%s banned by #%s (%s). Reason: %s", target.user_id, message.from_user.id, caller_role.value, reason or "None")

            reason_str = f"\n📄 Причина: <i>{reason}</i>" if reason else ""
            await bot.reply_to(
                message,
                f"🚫 <b>Пользователь заблокирован:</b>\n"
                f"• ID: <code>{target.user_id}</code>\n"
                f"• Username: @{target.username or 'отсутствует'}\n"
                f"• Исполнитель: <code>{caller_role.value}</code> (#{message.from_user.id}){reason_str}",
                parse_mode="HTML",
            )

    @bot.message_handler(commands=["unban"])
    async def cmd_unban(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_moderate(caller_role):
            await bot.reply_to(message, "⚠️ У вас нет прав администратора.")
            return

        target_id, _ = _parse_command_args(message.text)
        if not target_id:
            await bot.reply_to(message, "❌ Использование: <code>/unban &lt;user_id | @username&gt;</code>", parse_mode="HTML")
            return

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            target = await repo.get_by_identifier(target_id)
            if not target:
                await bot.reply_to(message, f"❌ Пользователь <code>{target_id}</code> не найден в базе данных.", parse_mode="HTML")
                return

            await repo.set_ban_status(target.user_id, False)
            await redis.delete(RedisKeys.ban(target.user_id))
            admin_logger.info("User #%s unbanned by #%s (%s)", target.user_id, message.from_user.id, caller_role.value)

            await bot.reply_to(
                message,
                f"✅ <b>Пользователь разблокирован:</b>\n"
                f"• ID: <code>{target.user_id}</code>\n"
                f"• Username: @{target.username or 'отсутствует'}\n"
                f"• Доступ к боту и Mini App полностью восстановлен.",
                parse_mode="HTML",
            )

    @bot.message_handler(commands=["mute"])
    async def cmd_mute(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_moderate(caller_role):
            await bot.reply_to(message, "⚠️ У вас нет прав администратора.")
            return

        target_id, reason = _parse_command_args(message.text)
        if not target_id:
            await bot.reply_to(message, "❌ Использование: <code>/mute &lt;user_id | @username&gt; [причина]</code>", parse_mode="HTML")
            return

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            target = await repo.get_by_identifier(target_id)
            if not target:
                await bot.reply_to(message, f"❌ Пользователь <code>{target_id}</code> не найден в базе данных.", parse_mode="HTML")
                return

            target_role = resolve_user_role(target.user_id, target.role, target.is_admin)
            if not can_target_user(caller_role, target_role):
                if target_role == Role.SUPERADMIN:
                    await bot.reply_to(message, "⛔ Ошибка: Суперадминистратор неприкосновенен и не может быть заглушен.")
                else:
                    await bot.reply_to(message, "⛔ Ошибка: Администратор не может ограничить другого администратора.")
                return

            await repo.set_mute_status(target.user_id, True)
            await redis.set(RedisKeys.mute(target.user_id), "muted")
            admin_logger.info("User #%s muted by #%s. Reason: %s", target.user_id, message.from_user.id, reason or "None")

            reason_str = f"\n📄 Причина: <i>{reason}</i>" if reason else ""
            await bot.reply_to(
                message,
                f"🔇 <b>Пользователь заглушен (MUTE):</b>\n"
                f"• ID: <code>{target.user_id}</code>\n"
                f"• Username: @{target.username or 'отсутствует'}{reason_str}\n"
                f"• Сообщения пользователя будут отклоняться ботом.",
                parse_mode="HTML",
            )

    @bot.message_handler(commands=["unmute"])
    async def cmd_unmute(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_moderate(caller_role):
            await bot.reply_to(message, "⚠️ У вас нет прав администратора.")
            return

        target_id, _ = _parse_command_args(message.text)
        if not target_id:
            await bot.reply_to(message, "❌ Использование: <code>/unmute &lt;user_id | @username&gt;</code>", parse_mode="HTML")
            return

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            target = await repo.get_by_identifier(target_id)
            if not target:
                await bot.reply_to(message, f"❌ Пользователь <code>{target_id}</code> не найден в базе данных.", parse_mode="HTML")
                return

            await repo.set_mute_status(target.user_id, False)
            await redis.delete(RedisKeys.mute(target.user_id))
            admin_logger.info("User #%s unmuted by #%s", target.user_id, message.from_user.id)

            await bot.reply_to(
                message,
                f"🔊 <b>Режим MUTE снят:</b>\n"
                f"• ID: <code>{target.user_id}</code>\n"
                f"• Username: @{target.username or 'отсутствует'}\n"
                f"• Пользователь может полноценно общаться с ботом.",
                parse_mode="HTML",
            )

    @bot.message_handler(commands=["user", "user_lookup"])
    async def cmd_user_inspect(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_moderate(caller_role):
            await bot.reply_to(message, "⚠️ У вас нет прав администратора.")
            return

        target_id, _ = _parse_command_args(message.text)
        if not target_id:
            await bot.reply_to(message, "❌ Использование: <code>/user &lt;user_id | @username&gt;</code>", parse_mode="HTML")
            return

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            target = await repo.get_by_identifier(target_id)
            if not target:
                await bot.reply_to(message, f"❌ Пользователь <code>{target_id}</code> не найден в базе данных.", parse_mode="HTML")
                return

            role = resolve_user_role(target.user_id, target.role, target.is_admin)
            route_count = await repo.get_route_count(target.user_id)

            created_at_str = target.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if target.created_at else "Неизвестно"
            banned_badge = "🔴 Заблокирован" if target.is_banned else "🟢 Активен"
            muted_badge = "🔇 Заглушен (Muted)" if getattr(target, "is_muted", False) else "🔊 Обычный"

            role_badge = f"👑 {role.value}" if role == Role.SUPERADMIN else (f"🛡️ {role.value}" if role == Role.ADMIN else f"👤 {role.value}")

            dossier = (
                f"📋 <b>ДОСЬЕ ПОЛЬЗОВАТЕЛЯ JARVIS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>User ID:</b> <code>{target.user_id}</code>\n"
                f"• <b>Username:</b> @{target.username or 'отсутствует'}\n"
                f"• <b>Роль в системе:</b> {role_badge}\n"
                f"• <b>Дата регистрации:</b> <code>{created_at_str}</code>\n"
                f"• <b>Создано маршрутов:</b> <b>{route_count}</b>\n"
                f"• <b>Баланс токенов:</b> <code>{target.tokens}</code>\n"
                f"• <b>Статус доступа:</b> {banned_badge}\n"
                f"• <b>Голосовой статус:</b> {muted_badge}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await bot.reply_to(message, dossier, parse_mode="HTML")

    @bot.message_handler(commands=["broadcast"])
    async def cmd_broadcast(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_moderate(caller_role):
            await bot.reply_to(message, "⚠️ У вас нет прав администратора.")
            return

        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await bot.reply_to(message, "❌ Использование: <code>/broadcast &lt;текст сообщения&gt;</code>", parse_mode="HTML")
            return

        broadcast_text = parts[1].strip()
        status_msg = await bot.reply_to(message, "⏳ <i>Подготовка безопасной рассылки...</i>", parse_mode="HTML")

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            active_user_ids = await repo.get_all_active_user_ids()

        total = len(active_user_ids)
        if total == 0:
            await bot.edit_message_text("⚠️ В базе данных нет активных пользователей для рассылки.", message.chat.id, status_msg.message_id)
            return

        delivered = 0
        failed = 0
        batch_size = 25

        formatted_msg = f"📢 <b>ОПОВЕЩЕНИЕ СИСТЕМЫ JARVIS:</b>\n\n{broadcast_text}"

        for i in range(0, total, batch_size):
            batch = active_user_ids[i:i + batch_size]
            for uid in batch:
                try:
                    await bot.send_message(uid, formatted_msg, parse_mode="HTML")
                    delivered += 1
                except Exception:
                    failed += 1
                await asyncio.sleep(0.04)

            if i + batch_size < total:
                await asyncio.sleep(0.5)

        admin_logger.info("Broadcast dispatched by #%s: delivered=%d, failed=%d, total=%d", message.from_user.id, delivered, failed, total)
        await bot.edit_message_text(
            f"📢 <b>Рассылка успешно завершена!</b>\n\n"
            f"• 👥 Всего адресатов: <b>{total}</b>\n"
            f"• ✅ Успешно доставлено: <b>{delivered}</b>\n"
            f"• ❌ Ошибок доставки (блокировки/удаления): <b>{failed}</b>",
            message.chat.id,
            status_msg.message_id,
            parse_mode="HTML",
        )

    @bot.message_handler(commands=["promote"])
    async def cmd_promote(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_govern(caller_role):
            await bot.reply_to(message, "⚠️ Данная команда доступна исключительно <b>SUPERADMIN</b>.", parse_mode="HTML")
            return

        target_id, _ = _parse_command_args(message.text)
        if not target_id:
            await bot.reply_to(message, "❌ Использование: <code>/promote &lt;user_id | @username&gt;</code>", parse_mode="HTML")
            return

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            target = await repo.get_by_identifier(target_id)
            if not target:
                await bot.reply_to(message, f"❌ Пользователь <code>{target_id}</code> не найден в базе данных.", parse_mode="HTML")
                return

            if is_superadmin(target.user_id):
                await bot.reply_to(message, f"ℹ️ Пользователь <code>{target.user_id}</code> уже обладает высшим статусом SUPERADMIN.", parse_mode="HTML")
                return

            await repo.set_role(target.user_id, role="ADMIN", is_admin=True)
            await redis.set(f"admin_status:{target.user_id}", "admin")
            admin_logger.info("Superadmin #%s promoted #%s to ADMIN role", message.from_user.id, target.user_id)

            await bot.reply_to(
                message,
                f"👑 <b>Пользователь повышен:</b>\n"
                f"• ID: <code>{target.user_id}</code>\n"
                f"• Username: @{target.username or 'отсутствует'}\n"
                f"• Новая роль: <b>ADMIN</b> 🛡️\n"
                f"• Права модерации в чате активированы.",
                parse_mode="HTML",
            )

    @bot.message_handler(commands=["demote"])
    async def cmd_demote(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_govern(caller_role):
            await bot.reply_to(message, "⚠️ Данная команда доступна исключительно <b>SUPERADMIN</b>.", parse_mode="HTML")
            return

        target_id, _ = _parse_command_args(message.text)
        if not target_id:
            await bot.reply_to(message, "❌ Использование: <code>/demote &lt;user_id | @username&gt;</code>", parse_mode="HTML")
            return

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            target = await repo.get_by_identifier(target_id)
            if not target:
                await bot.reply_to(message, f"❌ Пользователь <code>{target_id}</code> не найден в базе данных.", parse_mode="HTML")
                return

            if is_superadmin(target.user_id):
                await bot.reply_to(message, "⛔ Ошибка: Статус SUPERADMIN является верховным и неизменяемым через бота.", parse_mode="HTML")
                return

            await repo.set_role(target.user_id, role="USER", is_admin=False)
            await redis.set(f"admin_status:{target.user_id}", "user")
            admin_logger.info("Superadmin #%s demoted #%s to USER role", message.from_user.id, target.user_id)

            await bot.reply_to(
                message,
                f"🔰 <b>Пользователь разжалован:</b>\n"
                f"• ID: <code>{target.user_id}</code>\n"
                f"• Username: @{target.username or 'отсутствует'}\n"
                f"• Новая роль: <b>USER</b> 👤\n"
                f"• Административные права отозваны.",
                parse_mode="HTML",
            )

    @bot.message_handler(commands=["maintenance"])
    async def cmd_maintenance(message: types.Message):
        caller_role = await _get_caller_role(message.from_user.id)
        if not can_govern(caller_role):
            await bot.reply_to(message, "⚠️ Данная команда доступна исключительно <b>SUPERADMIN</b>.", parse_mode="HTML")
            return

        parts = message.text.strip().split()
        target_state = parts[1].lower() if len(parts) > 1 else None

        current = await redis.get(RedisKeys.maintenance())
        if target_state == "on":
            new_val = "1"
        elif target_state == "off":
            new_val = "0"
        else:
            new_val = "1" if current != "1" else "0"

        await redis.set(RedisKeys.maintenance(), new_val)
        admin_logger.info("Superadmin #%s switched maintenance mode to %s", message.from_user.id, new_val)

        if new_val == "1":
            status_desc = "🔴 <b>ВКЛЮЧЕН (Admins Only)</b>\nБот доступен только администрации. Обычные пользователи получают уведомление о техработах."
        else:
            status_desc = "🟢 <b>ВЫКЛЮЧЕН (Normal Operations)</b>\nВсе сервисы бота и Mini App доступны в штатном режиме."

        await bot.reply_to(
            message,
            f"⚙️ <b>Глобальный режим техобслуживания:</b>\n{status_desc}",
            parse_mode="HTML",
        )
