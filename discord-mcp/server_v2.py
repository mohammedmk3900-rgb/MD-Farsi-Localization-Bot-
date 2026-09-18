"""Read-only Discord MCP bridge with full authorized history indexing."""
from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from indexer import MessageIndex

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8000"))
DB_PATH = os.getenv("DISCORD_DB_PATH", "discord.db")
API = "https://discord.com/api/v10"

if not TOKEN or not GUILD_ID:
    raise RuntimeError("DISCORD_BOT_TOKEN and DISCORD_GUILD_ID are required")

mcp = FastMCP("Millennium Dawn Farsi Localization Discord", host=HOST, port=PORT)
index = MessageIndex(DB_PATH)


def normalize_message(message: dict[str, Any], channel: dict[str, Any] | None = None) -> dict[str, Any]:
    author = message.get("author") or {}
    channel_data = channel or message.get("channel") or {}
    channel_id = str(channel_data.get("id") or message.get("channel_id") or "")
    return {
        "id": str(message.get("id")),
        "channel_id": channel_id,
        "channel_name": channel_data.get("name"),
        "author_id": author.get("id"),
        "author_name": author.get("global_name") or author.get("username"),
        "content": message.get("content") or "",
        "timestamp": message.get("timestamp"),
        "edited_timestamp": message.get("edited_timestamp"),
        "url": f"https://discord.com/channels/{GUILD_ID}/{channel_id}/{message.get('id')}",
    }


async def discord_get(path: str, params: dict[str, Any] | None = None) -> Any:
    headers = {"Authorization": f"Bot {TOKEN}", "User-Agent": "MD-Farsi-Localization-Discord-MCP/2.0"}
    async with httpx.AsyncClient(base_url=API, headers=headers, timeout=30.0) as client:
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()


async def get_channels() -> list[dict[str, Any]]:
    channels = await discord_get(f"/guilds/{GUILD_ID}/channels")
    return [c for c in channels if c.get("type") in {0, 5, 10, 11, 12, 15}]


async def fetch_page(channel_id: str, before: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": 100}
    if before:
        params["before"] = before
    messages = await discord_get(f"/channels/{channel_id}/messages", params=params)
    return [normalize_message(m) for m in messages]


@mcp.tool()
async def get_server_overview() -> dict[str, Any]:
    guild = await discord_get(f"/guilds/{GUILD_ID}")
    channels = await get_channels()
    return {
        "server": {"id": guild.get("id"), "name": guild.get("name")},
        "channels": len(channels),
        "indexed_messages": index.count(),
        "database": DB_PATH,
    }


@mcp.tool()
async def list_channels() -> list[dict[str, Any]]:
    channels = await get_channels()
    return [{"id": c.get("id"), "name": c.get("name"), "type": c.get("type"), "parent_id": c.get("parent_id")} for c in channels]


@mcp.tool()
async def sync_channel_history(channel_id: str, max_pages: int = 0) -> dict[str, Any]:
    """Index all accessible history in one channel; max_pages=0 means unlimited."""
    channels = {str(c["id"]): c for c in await get_channels()}
    if channel_id not in channels:
        raise ValueError("Channel is not visible to the bot or is not a supported text channel")
    channel = channels[channel_id]
    before = None
    pages = 0
    total = 0
    while True:
        page = await fetch_page(channel_id, before)
        if not page:
            break
        for item in page:
            item["channel_name"] = channel.get("name")
        total += index.upsert_messages(page)
        pages += 1
        before = page[-1]["id"]
        if len(page) < 100 or (max_pages and pages >= max_pages):
            break
    return {"channel_id": channel_id, "channel_name": channel.get("name"), "pages": pages, "messages_processed": total, "complete": len(page) < 100 if pages else True}


@mcp.tool()
async def sync_server_history(max_pages_per_channel: int = 0) -> dict[str, Any]:
    """Index all accessible text channels. This never bypasses Discord permissions."""
    results = []
    for channel in await get_channels():
        results.append(await sync_channel_history(str(channel["id"]), max_pages_per_channel))
    return {"channels_processed": len(results), "results": results, "indexed_messages": index.count()}


@mcp.tool()
async def get_sync_status() -> dict[str, Any]:
    return {"database": DB_PATH, "indexed_messages": index.count(), "indexed_channels": index.channel_count()}


@mcp.tool()
async def search_index(query: str, limit: int = 50) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        return []
    return index.search(query, limit)


@mcp.tool()
async def read_channel(channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
    return index.read_channel(channel_id, limit)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
