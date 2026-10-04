"""ASGI security and health wrapper for the production Discord MCP service."""
from __future__ import annotations

import hmac
import os
from collections.abc import Awaitable, Callable
from typing import Any

ASGIApp = Callable[[dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]], Awaitable[Any]]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _allowed_origins() -> set[str]:
    return {
        item.strip()
        for item in os.getenv("MCP_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    }


class SecurityMiddleware:
    """Protect the MCP endpoint with bearer auth and Origin validation."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        auth_required: bool,
        auth_token: str,
        allowed_origins: set[str],
    ) -> None:
        self.app = app
        self.auth_required = auth_required
        self.auth_token = auth_token
        self.allowed_origins = allowed_origins

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/healthz", "/readyz"}:
            await self._health(scope, send)
            return

        if path != "/mcp":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        origin = headers.get("origin")
        if origin is not None:
            if not self.allowed_origins or origin not in self.allowed_origins:
                await self._respond(send, 403, b"forbidden origin\n")
                return

        if self.auth_required:
            authorization = headers.get("authorization", "")
            scheme, _, credentials = authorization.partition(" ")
            if scheme.casefold() != "bearer" or not credentials:
                await self._respond(
                    send,
                    401,
                    b"missing bearer token\n",
                    extra_headers=[(b"www-authenticate", b"Bearer")],
                )
                return
            if not hmac.compare_digest(credentials, self.auth_token):
                await self._respond(send, 401, b"invalid bearer token\n")
                return

        await self.app(scope, receive, send)

    async def _health(self, scope: dict[str, Any], send: Callable[..., Awaitable[Any]]) -> None:
        if scope.get("path") == "/healthz":
            await self._respond(send, 200, b"ok\n")
            return

        required = {
            "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN", "").strip(),
            "DISCORD_GUILD_ID": os.getenv("DISCORD_GUILD_ID", "").strip(),
        }
        if self.auth_required:
            required["MCP_AUTH_TOKEN"] = self.auth_token
        if not all(required.values()):
            await self._respond(send, 503, b"not ready\n")
            return

        await self._respond(send, 200, b"ready\n")

    @staticmethod
    async def _respond(
        send: Callable[..., Awaitable[Any]],
        status: int,
        body: bytes,
        *,
        extra_headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        headers = [
            (b"content-type", b"text/plain; charset=utf-8"),
            (b"content-length", str(len(body)).encode("ascii")),
            *(extra_headers or []),
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})


def create_http_app(mcp_server: Any) -> ASGIApp:
    """Build the production ASGI app around the MCP SDK endpoint."""
    auth_required = _env_bool("MCP_AUTH_REQUIRED", True)
    auth_token = os.getenv("MCP_AUTH_TOKEN", "").strip()
    if auth_required and len(auth_token) < 32:
        raise RuntimeError(
            "MCP_AUTH_TOKEN must contain at least 32 characters when MCP_AUTH_REQUIRED=true"
        )

    app = mcp_server.streamable_http_app()
    return SecurityMiddleware(
        app,
        auth_required=auth_required,
        auth_token=auth_token,
        allowed_origins=_allowed_origins(),
    )
