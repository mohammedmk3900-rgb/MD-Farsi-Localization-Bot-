"""Run the Discord Gateway indexer and authenticated MCP server together."""
from __future__ import annotations

import asyncio
import os

import uvicorn

from bot import main as bot_main
from server import build_app


async def main() -> None:
    bot_task = asyncio.create_task(bot_main())
    try:
        config = uvicorn.Config(
            build_app(),
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
