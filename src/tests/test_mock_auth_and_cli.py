"""Tests for mock authentication mode (--auth=0) and CLI parsing."""

import os
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from jarvis import extract_auth_bypass_flag, parse_port_arg
from src.middleware.telegram_auth import (
    TelegramAuthMiddleware,
    is_mock_auth_enabled,
    MOCK_USER,
)


def test_extract_auth_bypass_flag():
    # Various formats of auth bypass flags
    assert extract_auth_bypass_flag(["-r", "--auth=0"]) == (True, ["-r"])
    assert extract_auth_bypass_flag(["-r", "--auth", "0"]) == (True, ["-r"])
    assert extract_auth_bypass_flag(["-a", "--mock-auth"]) == (True, ["-a"])
    assert extract_auth_bypass_flag(["--no-auth", "stats"]) == (True, ["stats"])
    assert extract_auth_bypass_flag(["-r", "-m"]) == (True, ["-r"])

    # Normal flags without auth bypass
    assert extract_auth_bypass_flag(["-r", "--port", "8080"]) == (False, ["-r", "--port", "8080"])
    assert extract_auth_bypass_flag(["status"]) == (False, ["status"])


def test_parse_port_arg():
    assert parse_port_arg(["--port", "9000"]) == 9000
    assert parse_port_arg(["-p", "8080"]) == 8080
    assert parse_port_arg(["--port=7000"]) == 7000
    assert parse_port_arg([]) == 8000


@pytest.mark.asyncio
async def test_telegram_auth_middleware_blocks_when_mock_auth_disabled(monkeypatch):
    monkeypatch.delenv("MOCK_AUTH", raising=False)
    monkeypatch.delenv("JARVIS_MOCK_AUTH", raising=False)

    middleware = TelegramAuthMiddleware(app=None, bot_token="fake_bot_token")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/favorites/me",
        "headers": [],
    }
    request = Request(scope)

    async def call_next(req):
        return JSONResponse({"status": "ok"})

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_telegram_auth_middleware_allows_when_mock_auth_enabled(monkeypatch):
    monkeypatch.setenv("MOCK_AUTH", "1")

    assert is_mock_auth_enabled() is True

    middleware = TelegramAuthMiddleware(app=None, bot_token="fake_bot_token")

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/favorites/me",
        "headers": [],
    }
    request = Request(scope)

    async def call_next(req):
        return JSONResponse({
            "user_id": req.state.telegram_user_id,
            "user": req.state.telegram_user,
        })

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert request.state.telegram_user_id == 999999999
    assert request.state.telegram_user == MOCK_USER
