"""Telegram Mini App initData validation middleware."""

import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.parse import parse_qsl

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class TelegramAuthError(ValueError):
    """Raised when Telegram Mini App initData is missing or invalid."""


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age: int = 86400,
) -> dict[str, Any]:
    """Validate Telegram WebApp initData and return the decoded user payload."""
    if not init_data or not bot_token:
        raise TelegramAuthError("Missing Telegram initData")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise TelegramAuthError("Malformed Telegram initData") from exc

    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("Missing Telegram initData hash")

    auth_date_raw = data.get("auth_date")
    try:
        auth_date = int(auth_date_raw)
    except (TypeError, ValueError) as exc:
        raise TelegramAuthError("Invalid Telegram auth_date") from exc

    if max_age >= 0 and time.time() - auth_date > max_age:
        raise TelegramAuthError("Expired Telegram initData")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(data.items())
    )

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("Invalid Telegram initData signature")

    raw_user = data.get("user")
    if not raw_user:
        raise TelegramAuthError("Telegram user is missing")

    try:
        user = json.loads(raw_user)
    except json.JSONDecodeError as exc:
        raise TelegramAuthError("Invalid Telegram user payload") from exc

    if not isinstance(user, dict) or not user.get("id"):
        raise TelegramAuthError("Invalid Telegram user")

    return user


class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """Protect /api endpoints with Telegram Mini App initData."""

    def __init__(
        self,
        app,
        bot_token: str,
        max_age: int = 86400,
        enabled: bool | None = None,
    ):
        super().__init__(app)
        self.bot_token = bot_token
        self.max_age = max_age
        self.enabled = (
            os.getenv("TELEGRAM_AUTH_REQUIRED", "0").strip().lower()
            in {"1", "true", "yes", "on"}
            if enabled is None
            else enabled
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not self.enabled:
            # Temporary compatibility for the current frontend until it starts
            # sending Authorization: tma <initData>.
            if path == "/api/favorites/toggle" and request.method == "POST":
                try:
                    payload = json.loads((await request.body()).decode("utf-8"))
                    if payload.get("user_id"):
                        request.state.telegram_user_id = int(payload["user_id"])
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            elif path.startswith("/api/favorites/"):
                legacy_user_id = path.rsplit("/", 1)[-1]
                if legacy_user_id.isdigit():
                    request.state.telegram_user_id = int(legacy_user_id)
                    request.scope["path"] = "/api/favorites/me"
            return await call_next(request)

        if (
            not path.startswith("/api/")
            or path == "/api/auth/telegram"
        ):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("tma "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Telegram authentication required"},
            )

        try:
            user = validate_init_data(
                authorization[4:].strip(),
                self.bot_token,
                max_age=self.max_age,
            )
        except TelegramAuthError as exc:
            return JSONResponse(
                status_code=401,
                content={"detail": str(exc)},
            )

        request.state.telegram_user = user
        request.state.telegram_user_id = int(user["id"])
        return await call_next(request)
