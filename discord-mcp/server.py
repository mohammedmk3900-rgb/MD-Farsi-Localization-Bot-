"""Read-only Discord → MCP bridge for Millennium Dawn Farsi Localization."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8000"))
DISCORD_API = "https://discord.com/api/v10"

if not DISCORD_BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is required")
if not GUILD_ID:
    raise RuntimeError("DISCORD_GUILD_ID is required")

mcp = FastMCP(
    "Millennium Dawn Farsi Localization Discord",
    host=HOST,
    port=PORT,
)


async def discord_get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Call the Discord REST API using the bot token."""
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "User-Agent": "MD-Farsi-Localization-Discord-MCP/1.0",
    }

    async with httpx.AsyncClient(
        base_url=DISCORD_API,
        headers=headers,
        timeout=20.0,
    ) as client:
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()


def channel_summary(channel: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": channel.get("id"),
        "name": channel.get("name"),
        "type": channel.get("type"),
        "parent_id": channel.get("parent_id"),
        "position": channel.get("position"),
        "topic": channel.get("topic"),
    }


@mcp.tool()
async def get_server_overview() -> dict[str, Any]:
    """Return a compact overview of the configured Discord server."""
    guild = await discord_get(f"/guilds/{GUILD_ID}")
    channels = await discord_get(f"/guilds/{GUILD_ID}/channels")
    roles = await discord_get(f"/guilds/{GUILD_ID}/roles")

    return {
        "server": {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "description": guild.get("description"),
            "member_count": guild.get("approximate_member_count"),
        },
        "counts": {
            "channels": len(channels),
            "roles": len(roles),
        },
        "channels": [channel_summary(c) for c in channels],
        "role_names": [r.get("name") for r in roles if r.get("name") != "@everyone"],
    }


@mcp.tool()
async def list_channels() -> list[dict[str, Any]]:
    """List channels visible to the configured Discord bot."""
    channels = await discord_get(f"/guilds/{GUILD_ID}/channels")
    return [channel_summary(c) for c in channels]


@mcp.tool()
async def list_roles() -> list[dict[str, Any]]:
    """List roles in the configured Discord server."""
    roles = await discord_get(f"/guilds/{GUILD_ID}/roles")
    return [
        {
            "id": role.get("id"),
            "name": role.get("name"),
            "position": role.get("position"),
            "managed": role.get("managed"),
            "mentionable": role.get("mentionable"),
        }
        for role in roles
        if role.get("name") != "@everyone"
    ]


@mcp.tool()
async def read_channel(channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Read recent messages from a Discord text channel."""
    limit = max(1, min(limit, 100))
    messages = await discord_get(
        f"/channels/{channel_id}/messages",
        params={"limit": limit},
    )

    return [
        {
            "id": message.get("id"),
            "author": {
                "id": (message.get("author") or {}).get("id"),
                "name": (message.get("author") or {}).get("username"),
            },
            "content": message.get("content", ""),
            "timestamp": message.get("timestamp"),
            "edited_timestamp": message.get("edited_timestamp"),
            "reply_to": (
                (message.get("referenced_message") or {}).get("id")
                if message.get("referenced_message")
                else None
            ),
        }
        for message in messages
    ]


@mcp.tool()
async def search_messages(query: str, limit: int = 25) -> list[dict[str, Any]]:
    """Search messages in the configured Discord server."""
    query = query.strip()
    if not query:
        return []

    limit = max(1, min(limit, 100))
    results = await discord_get(
        f"/guilds/{GUILD_ID}/messages/search",
        params={"content": query, "limit": limit},
    )

    messages: list[dict[str, Any]] = []
    for bucket in results.get("messages", []):
        for message in bucket:
            author = message.get("author") or {}
            channel = message.get("channel") or {}
            messages.append(
                {
                    "id": message.get("id"),
                    "channel_id": channel.get("id"),
                    "channel_name": channel.get("name"),
                    "author": author.get("username"),
                    "content": message.get("content", ""),
                    "timestamp": message.get("timestamp"),
                    "url": (
                        f"https://discord.com/channels/{GUILD_ID}/"
                        f"{channel.get('id')}/{message.get('id')}"
                    ),
                }
            )
            if len(messages) >= limit:
                return messages

    return messages


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
