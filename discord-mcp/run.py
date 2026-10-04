"""Run the Discord Gateway indexer and MCP server together."""
from __future__ import annotations

import asyncio
import os

from bot import main as bot_main
from server import mcp


async def main() -> None:
    bot_task = asyncio.create_task(bot_main(), name="discord-gateway")
    mcp_task = asyncio.create_task(
        asyncio.to_thread(
            mcp.run,
            transport="streamable-http",
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")),
        ),
        name="mcp-server",
    )

    done, pending = await asyncio.wait(
        {bot_task, mcp_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

    for task in done:
        result = task.result()
        if isinstance(result, BaseException):
            raise result


if __name__ == "__main__":
    asyncio.run(main())
