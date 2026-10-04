"""Run the Discord Gateway indexer and MCP HTTP server together."""
from __future__ import annotations

import asyncio
import os

import uvicorn

from bot import main as bot_main
from http_app import create_http_app
from server import mcp


async def main() -> None:
    bot_task = asyncio.create_task(bot_main(), name="discord-gateway")
    app = create_http_app(mcp)

    config = uvicorn.Config(
        app,
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        proxy_headers=False,
        server_header="md-farsi-discord-mcp",
    )
    http_server = uvicorn.Server(config)
    mcp_task = asyncio.create_task(http_server.serve(), name="mcp-server")

    try:
        done, pending = await asyncio.wait(
            {bot_task, mcp_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            if task is mcp_task:
                http_server.should_exit = True
            task.cancel()

        await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            result = task.result()
            if isinstance(result, BaseException):
                raise result
    finally:
        http_server.should_exit = True
        if not mcp_task.done():
            mcp_task.cancel()
            await asyncio.gather(mcp_task, return_exceptions=True)
        if not bot_task.done():
            bot_task.cancel()
            await asyncio.gather(bot_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
