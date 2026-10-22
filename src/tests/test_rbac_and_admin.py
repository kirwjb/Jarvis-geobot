"""
Unit tests validating RBAC role hierarchy, permission boundaries,
in-chat moderation handlers, CLI authorization, and satirical calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.services.rbac import (
    Role,
    can_govern,
    can_manage_cli,
    can_moderate,
    can_promote_or_demote,
    can_target_user,
    is_superadmin,
    resolve_user_role,
    verify_cli_superadmin,
)
from src.database.models import User
from src.cli.admin import verify_cli_access, execute_guillotine, display_salon
from src.middleware.security import SecurityMiddleware
from src.handlers.admin import _get_caller_role, register_admin_handlers
from src.utils.redis_keys import RedisKeys

def test_role_hierarchy_ordering():
    assert Role.USER < Role.ADMIN < Role.SUPERADMIN
    assert Role.SUPERADMIN > Role.ADMIN > Role.USER
    assert Role.ADMIN >= Role.USER
    assert Role.ADMIN <= Role.SUPERADMIN
    assert Role.USER == Role.USER
    assert Role.ADMIN == Role.ADMIN
    assert Role.SUPERADMIN == Role.SUPERADMIN

def test_is_superadmin_configuration(monkeypatch):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [111111, 222222])
    monkeypatch.setattr("src.services.rbac.BOT_OWNER_ID", 111111)

    assert is_superadmin(111111) is True
    assert is_superadmin("222222") is True
    assert is_superadmin(333333) is False
    assert is_superadmin(None) is False
    assert is_superadmin("invalid") is False

def test_resolve_user_role(monkeypatch):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [777777])
    monkeypatch.setattr("src.services.rbac.BOT_OWNER_ID", 777777)

    assert resolve_user_role(777777, db_role="USER", is_admin=False) == Role.SUPERADMIN

    assert resolve_user_role(123456, db_role="ADMIN", is_admin=True) == Role.ADMIN
    assert resolve_user_role(123456, db_role="USER", is_admin=True) == Role.ADMIN

    assert resolve_user_role(123456, db_role="USER", is_admin=False) == Role.USER
    assert resolve_user_role(123456, db_role=None, is_admin=False) == Role.USER

def test_role_capability_checks():
    assert can_moderate(Role.USER) is False
    assert can_govern(Role.USER) is False
    assert can_manage_cli(Role.USER) is False
    assert can_promote_or_demote(Role.USER) is False

    assert can_moderate(Role.ADMIN) is True
    assert can_govern(Role.ADMIN) is False
    assert can_manage_cli(Role.ADMIN) is False
    assert can_promote_or_demote(Role.ADMIN) is False

    assert can_moderate(Role.SUPERADMIN) is True
    assert can_govern(Role.SUPERADMIN) is True
    assert can_manage_cli(Role.SUPERADMIN) is True
    assert can_promote_or_demote(Role.SUPERADMIN) is True

def test_target_hierarchy_matrix():
    assert can_target_user(Role.SUPERADMIN, Role.USER) is True
    assert can_target_user(Role.SUPERADMIN, Role.ADMIN) is True
    assert can_target_user(Role.SUPERADMIN, Role.SUPERADMIN) is False

    assert can_target_user(Role.ADMIN, Role.USER) is True
    assert can_target_user(Role.ADMIN, Role.ADMIN) is False
    assert can_target_user(Role.ADMIN, Role.SUPERADMIN) is False

    assert can_target_user(Role.USER, Role.USER) is False
    assert can_target_user(Role.USER, Role.ADMIN) is False
    assert can_target_user(Role.USER, Role.SUPERADMIN) is False

def test_verify_cli_access_allows_superadmin(monkeypatch):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [888888])
    monkeypatch.setattr("src.services.rbac.BOT_OWNER_ID", 888888)
    monkeypatch.setattr("src.cli.admin.SUPERADMINS", [888888])
    monkeypatch.setattr("src.cli.admin.BOT_OWNER_ID", 888888)

    active_id = verify_cli_access(caller_id=None)
    assert active_id == 888888

    active_id = verify_cli_access(caller_id=888888)
    assert active_id == 888888

def test_verify_cli_access_rejects_non_superadmin(monkeypatch):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [888888])
    monkeypatch.setattr("src.services.rbac.BOT_OWNER_ID", 888888)
    monkeypatch.setattr("src.cli.admin.SUPERADMINS", [888888])
    monkeypatch.setattr("src.cli.admin.BOT_OWNER_ID", 888888)

    with pytest.raises(SystemExit) as exc:
        verify_cli_access(caller_id=123456)
    assert exc.value.code == 1

def test_verify_cli_access_rejects_when_no_superadmin_configured(monkeypatch):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [])
    monkeypatch.setattr("src.services.rbac.BOT_OWNER_ID", None)
    monkeypatch.setattr("src.cli.admin.SUPERADMINS", [])
    monkeypatch.setattr("src.cli.admin.BOT_OWNER_ID", None)

    with pytest.raises(SystemExit) as exc:
        verify_cli_access(caller_id=None)
    assert exc.value.code == 1

@pytest.mark.asyncio
async def test_guillotine_protects_superadmin(monkeypatch, capsys):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.BOT_OWNER_ID", 999001)
    monkeypatch.setattr("src.cli.admin.SUPERADMINS", [999001])
    monkeypatch.setattr("src.cli.admin.BOT_OWNER_ID", 999001)

    fake_user = User(user_id=999001, username="royal_owner", role="SUPERADMIN", is_admin=True, is_banned=False)

    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def commit(self): pass
        async def execute(self, *args, **kwargs):
            mock_res = MagicMock()
            mock_res.scalar_one_or_none.return_value = fake_user
            return mock_res

    monkeypatch.setattr("src.cli.admin.AsyncSessionLocal", lambda: FakeSession())

    await execute_guillotine("999001")
    captured = capsys.readouterr().out
    assert "INCIDENT DE HAUTE TRAHISON" in captured
    assert "blade fractures on sovereign steel" in captured

@pytest.mark.asyncio
async def test_salon_renders_luxury_dossier(monkeypatch, capsys):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.BOT_OWNER_ID", 999001)
    monkeypatch.setattr("src.cli.admin.SUPERADMINS", [999001])
    monkeypatch.setattr("src.cli.admin.BOT_OWNER_ID", 999001)

    async def fake_get_stats():
        return {
            "users": 100,
            "banned_users": 2,
            "muted_users": 1,
            "admin_users": 5,
            "superadmin_users": 1,
            "cached_cities": 3,
            "places": 500,
            "photos": 80,
            "favorites": 40,
            "history": 95,
            "maintenance": False,
            "redis_ok": True,
        }

    monkeypatch.setattr("src.cli.admin.get_system_stats", fake_get_stats)

    class FakeConn:
        async def execute(self, *args, **kwargs): pass

    class FakeEngine:
        def connect(self):
            mock = MagicMock()
            mock.__aenter__ = AsyncMock(return_value=FakeConn())
            mock.__aexit__ = AsyncMock(return_value=None)
            return mock

    monkeypatch.setattr("src.cli.admin.engine", FakeEngine())

    mock_redis = AsyncMock()
    mock_redis.info.return_value = {"keyspace_hits": "150", "keyspace_misses": "10"}
    monkeypatch.setattr("src.cli.admin.redis_client", mock_redis)

    await display_salon()
    captured = capsys.readouterr().out
    assert "LE SALON ROCOCO DE HAUTE TÉLÉMÉTRIE" in captured
    assert "A vintage 1982 telemetry dossier" in captured
    assert "Cave de PostgreSQL" in captured

@pytest.mark.asyncio
async def test_security_middleware_superadmin_bypasses_all(monkeypatch):
    monkeypatch.setattr("src.middleware.security.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "1"
    mw = SecurityMiddleware(mock_redis)

    mock_msg = MagicMock()
    mock_msg.from_user.id = 999001
    mock_msg.callback_query = None

    res = await mw.pre_process(mock_msg, {})
    assert res is None

@pytest.mark.asyncio
async def test_security_middleware_blocks_normal_user_on_maintenance(monkeypatch):
    monkeypatch.setattr("src.middleware.security.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])

    mock_redis = AsyncMock()
    mock_redis.get.side_effect = lambda key: "1" if key == RedisKeys.maintenance() else "user"
    mw = SecurityMiddleware(mock_redis)

    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def execute(self, *args, **kwargs):
            mock = MagicMock()
            mock.first.return_value = ("USER", False)
            return mock

    monkeypatch.setattr("src.middleware.security.AsyncSessionLocal", lambda: FakeSession())

    mock_msg = MagicMock()
    mock_msg.from_user.id = 123456
    mock_msg.chat.id = 123456
    mock_msg.bot.send_message = AsyncMock()

    res = await mw.pre_process(mock_msg, {})
    assert res == "cancel"

@pytest.mark.asyncio
async def test_security_middleware_blocks_muted_user(monkeypatch):
    monkeypatch.setattr("src.middleware.security.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])

    mock_redis = AsyncMock()
    async def fake_get(key):
        if key == RedisKeys.maintenance(): return "0"
        if key == RedisKeys.mute(555555): return "muted"
        if key == RedisKeys.ban(555555): return "safe"
        return None
    mock_redis.get = fake_get

    mw = SecurityMiddleware(mock_redis)
    mw.limiter.is_allowed = AsyncMock(return_value=True)

    mock_msg = MagicMock()
    mock_msg.from_user.id = 555555
    mock_msg.chat.id = 555555
    mock_msg.bot.send_message = AsyncMock()

    res = await mw.pre_process(mock_msg, {})
    assert res == {"cancel": True}
    mock_msg.bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_admin_handlers_moderation_and_governance(monkeypatch):
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])
    monkeypatch.setattr("src.handlers.admin.is_superadmin", lambda uid: uid == 999001)

    registered_handlers = {}

    class MockBot:
        def __init__(self):
            self.reply_to = AsyncMock()

        def message_handler(self, commands, **kwargs):
            def decorator(func):
                for cmd in commands:
                    registered_handlers[cmd] = func
                return func
            return decorator

    mock_bot = MockBot()
    mock_redis = AsyncMock()
    await register_admin_handlers(mock_bot, redis_client=mock_redis)

    async def mock_get_caller_user(uid):
        return Role.USER
    monkeypatch.setattr("src.handlers.admin._get_caller_role", mock_get_caller_user)

    msg = MagicMock()
    msg.from_user.id = 123
    msg.text = "/ban 456 spamming"

    ban_func = registered_handlers["ban"]
    await ban_func(msg)
    assert "У вас нет прав администратора" in mock_bot.reply_to.call_args[0][1]

    async def mock_get_caller_admin(uid):
        return Role.ADMIN
    monkeypatch.setattr("src.handlers.admin._get_caller_role", mock_get_caller_admin)

    fake_target_superadmin = User(user_id=999001, username="sovereign", role="SUPERADMIN", is_admin=True)

    class FakeSessionSA:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def execute(self, *args, **kwargs):
            mock = MagicMock()
            mock.scalar_one_or_none.return_value = fake_target_superadmin
            return mock

    monkeypatch.setattr("src.handlers.admin.AsyncSessionLocal", lambda: FakeSessionSA())

    msg_sa = MagicMock()
    msg_sa.from_user.id = 888
    msg_sa.text = "/ban 999001"

    await ban_func(msg_sa)
    assert "Суперадминистратор неприкосновенен" in mock_bot.reply_to.call_args[0][1]

    promote_func = registered_handlers["promote"]
    msg_promote = MagicMock()
    msg_promote.from_user.id = 888
    msg_promote.text = "/promote 456"

    await promote_func(msg_promote)
    assert "SUPERADMIN" in mock_bot.reply_to.call_args[0][1]

    async def mock_get_caller_sa(uid):
        return Role.SUPERADMIN
    monkeypatch.setattr("src.handlers.admin._get_caller_role", mock_get_caller_sa)

    maint_func = registered_handlers["maintenance"]
    msg_maint = MagicMock()
    msg_maint.from_user.id = 999001
    msg_maint.text = "/maintenance on"

    await maint_func(msg_maint)
    mock_redis.set.assert_called_with(RedisKeys.maintenance(), "1")
    assert "ВКЛЮЧЕН" in mock_bot.reply_to.call_args[0][1]

@pytest.mark.asyncio
async def test_security_middleware_handles_callback_query_flood(monkeypatch):
    from telebot.types import CallbackQuery
    from src.utils.languages import get_text
    monkeypatch.setattr("src.middleware.security.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "0"
    mw = SecurityMiddleware(mock_redis)
    mw.limiter.is_allowed = AsyncMock(return_value=False)

    cq = CallbackQuery.de_json({
        "id": "cb_query_123",
        "from": {"id": 123456, "is_bot": False, "first_name": "Test"},
        "chat_instance": "1",
        "data": "test_action",
    })
    cq.bot = MagicMock()
    cq.bot.answer_callback_query = AsyncMock()

    res = await mw.pre_process(cq, {})
    assert res == {"cancel": True}
    cq.bot.answer_callback_query.assert_called_once_with(
        "cb_query_123",
        text=get_text("flood_msg"),
        show_alert=True,
    )

def test_utils_green_ansi_escape():
    from src.utils.utils import GREEN
    assert GREEN == "\033[92m"

@pytest.mark.asyncio
async def test_security_middleware_handles_message_flood_rejection(monkeypatch):
    from src.utils.languages import get_text
    monkeypatch.setattr("src.middleware.security.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "0"
    mw = SecurityMiddleware(mock_redis)
    mw.limiter.is_allowed = AsyncMock(return_value=False)

    msg = MagicMock()
    msg.from_user.id = 123456
    msg.chat.id = 987654
    msg.bot.send_message = AsyncMock()

    res = await mw.pre_process(msg, {})
    assert res == {"cancel": True}
    msg.bot.send_message.assert_called_once_with(
        987654,
        get_text("flood_msg"),
    )

@pytest.mark.asyncio
async def test_security_middleware_handles_callback_query_maintenance(monkeypatch):
    from telebot.types import CallbackQuery
    from src.utils.languages import get_text
    monkeypatch.setattr("src.middleware.security.SUPERADMINS", [999001])
    monkeypatch.setattr("src.services.rbac.SUPERADMINS", [999001])

    mock_redis = AsyncMock()
    mock_redis.get.side_effect = lambda key: "1" if key == RedisKeys.maintenance() else "user"
    mw = SecurityMiddleware(mock_redis)

    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def execute(self, *args, **kwargs):
            mock = MagicMock()
            mock.first.return_value = ("USER", False)
            return mock

    monkeypatch.setattr("src.middleware.security.AsyncSessionLocal", lambda: FakeSession())

    cq = CallbackQuery.de_json({
        "id": "cb_maint_123",
        "from": {"id": 123456, "is_bot": False, "first_name": "Test"},
        "chat_instance": "1",
        "data": "test_action",
    })
    cq.bot = MagicMock()
    cq.bot.answer_callback_query = AsyncMock()

    res = await mw.pre_process(cq, {})
    assert res == {"cancel": True}
    cq.bot.answer_callback_query.assert_called_once_with(
        "cb_maint_123",
        text=get_text("maintenance_mode_msg"),
        show_alert=True,
    )

def test_cancel_payload_telebot_and_dict_compatibility():
    from telebot.handler_backends import CancelUpdate
    from src.middleware.security import CancelPayload

    payload = CancelPayload()
    assert isinstance(payload, CancelUpdate)
    assert isinstance(payload, dict)
    assert payload == {"cancel": True}
    assert payload == "cancel"
    assert payload.get("cancel") is True

