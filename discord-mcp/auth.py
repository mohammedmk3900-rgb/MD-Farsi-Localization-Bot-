"""Small, production-safe bearer authentication middleware for the MCP HTTP endpoint."""
from __future__ import annotations

import hmac
import os
from starlette.types import ASGIApp, Receive, Scope, Send


def require_auth_token() -> str:
    """Require a strong bearer token before constructing the public MCP app."""
    token = os.getenv("MCP_AUTH_TOKEN", "").strip()
    if len(token) < 32:
        raise RuntimeError(
            "MCP_AUTH_TOKEN is required and must contain at least 32 characters"
        )
    return token


class BearerAuthMiddleware:
    """Require a configured Bearer token for the MCP endpoint."""

    def __init__(self, app: ASGIApp, token: str | None = None, protected_path: str = "/mcp") -> None:
        self.app = app
        self.token = (token if token is not None else require_auth_token())
        self.protected_path = protected_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("path") != self.protected_path:
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        scheme, _, supplied = authorization.partition(" ")

        if (
            scheme.lower() != "bearer"
            or not supplied
            or not hmac.compare_digest(supplied.strip(), self.token)
        ):
            await self._unauthorized(send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _unauthorized(send: Send) -> None:
        body = b'{"error":"unauthorized","message":"Bearer token required"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"cache-control", b"no-store"),
                    (b"www-authenticate", b'Bearer realm="DawnNexus MCP"'),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def env_csv(name: str, default: str) -> list[str]:
    """Read a comma-separated environment setting."""
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]
