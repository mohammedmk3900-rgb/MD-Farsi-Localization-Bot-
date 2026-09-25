"""Run the Discord Gateway indexer and MCP server together."""
from __future__ import annotations
import asyncio
import os
from bot import main as bot_main
from server import mcp

async def main()->None:
    bot_task=asyncio.create_task(bot_main())
    try:
        await asyncio.to_thread(mcp.run,transport="streamable-http",host=os.getenv("MCP_HOST", "0.0.0.0"),port=int(os.getenv("MCP_PORT", "8000")))
    finally:
        bot_task.cancel()
        await asyncio.gather(bot_task,return_exceptions=True)

if __name__=="__main__": asyncio.run(main())
