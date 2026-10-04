"""OAuth 2.1 authorization server for the DawnNexus MCP endpoint.

This is a small, single-owner authorization server backed by the existing
SQLite database. It is intentionally self-contained so ChatGPT can complete
the MCP authorization-code + PKCE flow without requiring a third-party IdP.

Set MCP_PUBLIC_URL and MCP_OAUTH_PASSWORD in the deployment environment.
The login page is HTTPS-only in production and the password is never stored.
"""
from __future__ import annotations

import html
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import AnyHttpUrl

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route


def _now() -> int:
    return int(time.time())


def _append_query(url: str, **params: str | None) -> str:
    parsed = urlparse(url)
    query = [(k, v) for k, values in parse_qs(parsed.query).items() for v in values]
    query.extend((k, v) for k, v in params.items() if v is not None)
    return urlunparse(parsed._replace(query=urlencode(query)))


class DawnNexusOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    """Persistent single-owner OAuth provider for DawnNexus."""

    def __init__(self, db_path: str, public_url: str) -> None:
        self.db_path = db_path
        self.public_url = public_url.rstrip("/")
        self.resource_url = f"{self.public_url}/mcp"
        self.username = os.getenv("MCP_OAUTH_USERNAME", "admin").strip() or "admin"
        self.password = os.getenv("MCP_OAUTH_PASSWORD", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    client_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_pending (
                    request_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_codes (
                    code TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_access_tokens (
                    token TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at INTEGER
                );
                CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
                    token TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at INTEGER
                );
                """
            )

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM oauth_clients WHERE client_id = ?", (client_id,)
            ).fetchone()
        if not row:
            return None
        return OAuthClientInformationFull.model_validate_json(row["payload"])

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id:
            raise TokenError(error="invalid_client", error_description="client_id is required")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO oauth_clients(client_id, payload) VALUES(?, ?)
                ON CONFLICT(client_id) DO UPDATE SET payload=excluded.payload
                """,
                (client_info.client_id, client_info.model_dump_json()),
            )

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        requested = params.scopes or ["discord:read"]
        if any(scope != "discord:read" for scope in requested):
            return _append_query(
                str(params.redirect_uri),
                error="invalid_scope",
                error_description="DawnNexus only grants discord:read",
                state=params.state,
            )

        code = AuthorizationCode(
            code=f"code_{secrets.token_urlsafe(32)}",
            client_id=client.client_id or "",
            scopes=["discord:read"],
            expires_at=time.time() + 300,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource or self.resource_url,
        )
        request_id = secrets.token_urlsafe(32)
        pending_payload = json.dumps(
            {"code": json.loads(code.model_dump_json()), "state": params.state},
            separators=(",", ":"),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO oauth_pending(request_id, payload, expires_at) VALUES(?, ?, ?)",
                (request_id, pending_payload, code.expires_at),
            )
            conn.execute("DELETE FROM oauth_pending WHERE expires_at < ?", (time.time(),))
        return f"{self.public_url}/oauth/login?request_id={request_id}"

    async def approve(self, request_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload, expires_at FROM oauth_pending WHERE request_id = ? AND expires_at >= ?",
                (request_id, time.time()),
            ).fetchone()
            if not row:
                return None
            pending = json.loads(row["payload"])
            code = AuthorizationCode.model_validate(pending["code"])
            state = pending.get("state")
            conn.execute("DELETE FROM oauth_pending WHERE request_id = ?", (request_id,))
            conn.execute(
                "INSERT INTO oauth_codes(code, payload, expires_at) VALUES(?, ?, ?)",
                (code.code, code.model_dump_json(), code.expires_at),
            )
        return _append_query(str(code.redirect_uri), code=code.code, state=state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM oauth_codes WHERE code = ? AND expires_at >= ?",
                (authorization_code, time.time()),
            ).fetchone()
        if not row:
            return None
        code = AuthorizationCode.model_validate_json(row["payload"])
        if code.client_id != client.client_id:
            return None
        return code

    def _mint_access(
        self, code: AuthorizationCode | RefreshToken
    ) -> tuple[AccessToken, RefreshToken]:
        access_value = f"dn_access_{secrets.token_urlsafe(32)}"
        refresh_value = f"dn_refresh_{secrets.token_urlsafe(32)}"
        access_exp = _now() + 3600
        refresh_exp = _now() + 30 * 24 * 3600
        access = AccessToken(
            token=access_value,
            client_id=code.client_id,
            scopes=code.scopes,
            expires_at=access_exp,
            resource=code.resource or self.resource_url,
            subject=self.username,
            claims={"iss": self.public_url, "sub": self.username},
        )
        refresh = RefreshToken(
            token=refresh_value,
            client_id=code.client_id,
            scopes=code.scopes,
            expires_at=refresh_exp,
            resource=code.resource or self.resource_url,
            subject=self.username,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO oauth_access_tokens(token, payload, expires_at) VALUES(?, ?, ?)",
                (access.token, access.model_dump_json(), access.expires_at),
            )
            conn.execute(
                "INSERT INTO oauth_refresh_tokens(token, payload, expires_at) VALUES(?, ?, ?)",
                (refresh.token, refresh.model_dump_json(), refresh.expires_at),
            )
        return access, refresh

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        with self._connect() as conn:
            conn.execute("DELETE FROM oauth_codes WHERE code = ?", (authorization_code.code,))
        access, refresh = self._mint_access(authorization_code)
        return OAuthToken(
            access_token=access.token,
            token_type="Bearer",
            expires_in=3600,
            refresh_token=refresh.token,
            refresh_token_expires_in=30 * 24 * 3600,
            scope=" ".join(access.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload, expires_at FROM oauth_access_tokens WHERE token = ?",
                (token,),
            ).fetchone()
        if not row or (row["expires_at"] is not None and row["expires_at"] < _now()):
            return None
        return AccessToken.model_validate_json(row["payload"])

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload, expires_at FROM oauth_refresh_tokens WHERE token = ?",
                (refresh_token,),
            ).fetchone()
        if not row or (row["expires_at"] is not None and row["expires_at"] < _now()):
            return None
        token = RefreshToken.model_validate_json(row["payload"])
        return token if token.client_id == client.client_id else None

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        requested = scopes or ["discord:read"]
        if any(scope != "discord:read" for scope in requested):
            raise TokenError(error="invalid_scope", error_description="Unsupported scope")
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM oauth_refresh_tokens WHERE token = ?", (refresh_token.token,)
            )
        access, refresh = self._mint_access(
            RefreshToken(
                token=refresh_token.token,
                client_id=refresh_token.client_id,
                scopes=["discord:read"],
                expires_at=refresh_token.expires_at,
                resource=refresh_token.resource,
                subject=refresh_token.subject,
            )
        )
        return OAuthToken(
            access_token=access.token,
            token_type="Bearer",
            expires_in=3600,
            refresh_token=refresh.token,
            refresh_token_expires_in=30 * 24 * 3600,
            scope="discord:read",
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM oauth_access_tokens WHERE token = ?", (token.token,))
            conn.execute("DELETE FROM oauth_refresh_tokens WHERE token = ?", (token.token,))

    def auth_settings(self) -> AuthSettings:
        return AuthSettings(
            issuer_url=AnyHttpUrl(self.public_url),
            resource_server_url=AnyHttpUrl(self.resource_url),
            required_scopes=["discord:read"],
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=["discord:read"],
                default_scopes=["discord:read"],
            ),
            revocation_options=RevocationOptions(enabled=True),
            validate_token_resource=True,
        )


def build_login_routes(provider: DawnNexusOAuthProvider) -> list[Route]:
    async def login_page(request: Request) -> Response:
        request_id = request.query_params.get("request_id", "")
        if not request_id:
            return HTMLResponse("Missing authorization request.", status_code=400)
        with provider._connect() as conn:
            row = conn.execute(
                "SELECT payload, expires_at FROM oauth_pending WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if not row or row["expires_at"] < time.time():
            return HTMLResponse("Authorization request expired.", status_code=400)
        pending = json.loads(row["payload"])
        code = AuthorizationCode.model_validate(pending["code"])
        client = await provider.get_client(code.client_id)
        client_name = html.escape(
            str((client.client_name if client else None) or code.client_id)
        )
        safe_request_id = html.escape(request_id, quote=True)
        body = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>DawnNexus authorization</title>
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:system-ui;max-width:520px;margin:8vh auto;padding:24px">
<h1>DawnNexus</h1>
<p><b>{client_name}</b> is requesting read-only access to your Millennium Dawn
Farsi Localization Discord data.</p>
<p>Permission: <code>discord:read</code></p>
<form method="post" action="/oauth/login">
<input type="hidden" name="request_id" value="{safe_request_id}">
<label>Username<br><input name="username" autocomplete="username" required></label><br><br>
<label>Password<br><input name="password" type="password" autocomplete="current-password" required></label><br><br>
<button type="submit">Authorize DawnNexus</button>
</form>
</body></html>"""
        return HTMLResponse(body, headers={"cache-control": "no-store"})

    async def login_submit(request: Request) -> Response:
        raw = (await request.body()).decode("utf-8")
        fields = {k: values[0] for k, values in parse_qs(raw).items() if values}
        request_id = fields.get("request_id", "")
        username = fields.get("username", "")
        password = fields.get("password", "")
        if len(provider.password) < 16:
            return HTMLResponse(
                "DawnNexus OAuth is not configured. Set MCP_OAUTH_PASSWORD on the server.",
                status_code=503,
                headers={"cache-control": "no-store"},
            )
        if not secrets.compare_digest(username, provider.username) or not secrets.compare_digest(
            password, provider.password
        ):
            return HTMLResponse(
                "Invalid credentials.",
                status_code=401,
                headers={"cache-control": "no-store"},
            )
        redirect = await provider.approve(request_id)
        if not redirect:
            return HTMLResponse(
                "Authorization request expired or invalid.",
                status_code=400,
            )
        return RedirectResponse(
            redirect,
            status_code=303,
            headers={"cache-control": "no-store"},
        )

    return [
        Route("/oauth/login", login_page, methods=["GET"]),
        Route("/oauth/login", login_submit, methods=["POST"]),
    ]
