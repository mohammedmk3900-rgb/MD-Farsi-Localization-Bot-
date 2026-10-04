"""Run the Discord Gateway indexer and authenticated MCP server together."""
from __future__ import annotations

import asyncio
import os

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from mcp.server.transport_security import TransportSecuritySettings

from auth import BearerAuthMiddleware, env_csv
from bot import main as bot_main
from server import mcp


async def health(_: object) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "DawnNexus", "mcp": "/mcp"})


def build_app() -> Starlette:
    allowed_hosts = env_csv(
        "MCP_ALLOWED_HOSTS",
        "dawnnexus.onrender.com,dawnnexus.onrender.com:*",
    )
    allowed_origins = env_csv(
        "MCP_ALLOWED_ORIGINS",
        "https://chatgpt.com,https://chat.openai.com",
    )

    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )

    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        transport_security=transport_security,
        host=os.getenv("MCP_HOST", "0.0.0.0"),
    )

    # Keep the health check public so Render can probe the service without
    # receiving or requiring the MCP bearer secret.
    app = Starlette(
        routes=[Route("/health", health, methods=["GET"])],
    )
    app.mount("/", BearerAuthMiddleware(mcp_app, protected_path="/mcp"))
    return app


async def main() -> None:
    bot_task = asyncio.create_task(bot_main())
    try:
        config = uvicorn.Config(
            build_app(),
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "info"),
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
        server = uvicorn.Server(config)
        await server.serve()
    finally:
        bot_task.cancel()
        await asyncio.gather(bot_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
