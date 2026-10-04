"""Authentication and MCP OAuth discovery helpers for DawnNexus."""
from __future__ import annotations

import hmac
import json
import os
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError
from starlette.types import ASGIApp, Receive, Scope, Send


def auth_mode() -> str:
    """Return the configured MCP authentication mode."""
    mode = os.getenv("MCP_AUTH_MODE", "static").strip().lower()
    if mode not in {"static", "oauth"}:
        raise RuntimeError("MCP_AUTH_MODE must be 'static' or 'oauth'")
    return mode


def require_auth_token() -> str:
    """Require a strong static bearer token for local/legacy deployments."""
    token = os.getenv("MCP_AUTH_TOKEN", "").strip()
    if len(token) < 32:
        raise RuntimeError(
            "MCP_AUTH_TOKEN is required and must contain at least 32 characters"
        )
    return token


def _issuer() -> str:
    value = os.getenv("MCP_AUTH_ISSUER", "").strip()
    if not value.startswith("https://"):
        raise RuntimeError("MCP_AUTH_ISSUER must be an HTTPS issuer URL")
    return value if value.endswith("/") else f"{value}/"


def _resource() -> str:
    value = os.getenv(
        "MCP_RESOURCE_URL",
        "https://dawnnexus.onrender.com",
    ).strip().rstrip("/")
    if not value.startswith("https://"):
        raise RuntimeError("MCP_RESOURCE_URL must be an HTTPS URL")
    return value


def _audience() -> str:
    value = os.getenv("MCP_AUTH_AUDIENCE", "").strip()
    if not value:
        raise RuntimeError("MCP_AUTH_AUDIENCE is required when MCP_AUTH_MODE=oauth")
    return value


def _scopes() -> list[str]:
    raw = os.getenv("MCP_AUTH_SCOPES", "discord:read").strip()
    return [item.strip() for item in raw.split() if item.strip()]


def protected_resource_metadata() -> dict[str, Any]:
    """Return RFC 9728 protected-resource metadata for ChatGPT MCP OAuth."""
    return {
        "resource": _resource(),
        "authorization_servers": [_issuer()],
        "scopes_supported": _scopes(),
        "resource_documentation": _resource(),
    }


def _jwks_client() -> PyJWKClient:
    url = os.getenv("MCP_AUTH_JWKS_URL", f"{_issuer()}.well-known/jwks.json").strip()
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300)


def _validate_oauth_token(token: str) -> dict[str, Any]:
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=_audience(),
        issuer=_issuer(),
        options={"require": ["exp", "iat", "iss", "aud"]},
    )

    required = set(_scopes())
    if required:
        granted = set(str(claims.get("scope", "")).split())
        granted.update(str(item) for item in claims.get("permissions", []) or [])
        missing = required - granted
        if missing:
            raise InvalidTokenError(
                f"missing required scopes: {', '.join(sorted(missing))}"
            )

    return claims


class BearerAuthMiddleware:
    """Authenticate MCP requests using static bearer or OAuth 2.1 JWTs."""

    def __init__(
        self,
        app: ASGIApp,
        token: str | None = None,
        protected_path: str = "/mcp",
    ) -> None:
        self.app = app
        self.token = token
        self.protected_path = protected_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/.well-known/oauth-protected-resource":
            await self._metadata(send)
            return

        if path != self.protected_path:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        authorization = headers.get("authorization", "")
        scheme, _, supplied = authorization.partition(" ")

        if scheme.lower() != "bearer" or not supplied.strip():
            await self._unauthorized(send, error="invalid_token")
            return

        supplied = supplied.strip()
        try:
            if auth_mode() == "static":
                expected = self.token if self.token is not None else require_auth_token()
                valid = hmac.compare_digest(supplied, expected)
            else:
                _validate_oauth_token(supplied)
                valid = True
        except (InvalidTokenError, RuntimeError, ValueError, TypeError):
            valid = False
        except Exception:
            valid = False

        if not valid:
            await self._unauthorized(send, error="invalid_token")
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _metadata(send: Send) -> None:
        try:
            body = json.dumps(
                protected_resource_metadata(),
                separators=(",", ":"),
            ).encode("utf-8")
            status = 200
        except RuntimeError as exc:
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            status = 500

        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    @staticmethod
    async def _unauthorized(send: Send, error: str) -> None:
        resource_metadata = ""
        if auth_mode() == "oauth":
            resource_metadata = (
                f'{_resource()}/.well-known/oauth-protected-resource'
            )

        challenge = f'Bearer realm="DawnNexus MCP", error="{error}"'
        if resource_metadata:
            challenge += f', resource_metadata="{resource_metadata}"'

        body = json.dumps(
            {
                "error": "unauthorized",
                "error_description": "Valid bearer authentication is required",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"cache-control", b"no-store"),
                    (b"www-authenticate", challenge.encode("utf-8")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def env_csv(name: str, default: str) -> list[str]:
    """Read a comma-separated environment setting."""
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]
