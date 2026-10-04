"""Run the Discord Gateway indexer and MCP server together."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os

import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bot import main as bot_main
from server import mcp


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Require a static bearer token for the public MCP HTTP endpoint."""

    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._token_hash = hashlib.sha256(token.encode("utf-8")).digest()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        scheme, _, presented = authorization.partition(" ")
        presented = presented.strip()

        valid = (
            scheme.lower() == "bearer"
            and bool(presented)
            and hmac.compare_digest(
                hashlib.sha256(presented.encode("utf-8")).digest(),
                self._token_hash,
            )
        )
        if not valid:
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)


def build_app():
    token = os.getenv("DAWNNEXUS_MCP_BEARER_TOKEN", "").strip()
    if len(token) < 32:
        raise RuntimeError(
            "DAWNNEXUS_MCP_BEARER_TOKEN is required and must be at least 32 characters"
        )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> Response:
        return JSONResponse(
            {
                "status": "ok",
                "service": "DawnNexus",
                "mcp": "streamable-http",
                "authentication": "bearer",
            }
        )

    app = mcp.streamable_http_app(
        host=os.getenv("MCP_HOST", "0.0.0.0"),
    )
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app


async def main() -> None:
    bot_task = asyncio.create_task(bot_main())
    try:
        app = build_app()
        config = uvicorn.Config(
            app,
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")),
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()
    finally:
        bot_task.cancel()
        await asyncio.gather(bot_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
