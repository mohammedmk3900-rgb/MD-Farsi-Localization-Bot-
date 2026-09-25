"""Read-only Discord MCP bridge for authorized server structure and message history."""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

from indexer import MessageIndex
from news import DiscordNewsEngine
from intelligence import DiscordIntelligence

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8000"))
DB_PATH = os.getenv("DISCORD_DB_PATH", "/app/data/discord.db")
API = "https://discord.com/api/v10"

if not TOKEN or not GUILD_ID:
    raise RuntimeError("DISCORD_BOT_TOKEN and DISCORD_GUILD_ID are required")

mcp = MCPServer("Millennium Dawn Farsi Localization Discord")
index = MessageIndex(DB_PATH)
news_engine = DiscordNewsEngine(DB_PATH)
intelligence_engine = DiscordIntelligence(DB_PATH)


def normalize_message(message: dict[str, Any], channel: dict[str, Any] | None = None) -> dict[str, Any]:
    author = message.get("author") or {}
    channel_data = channel or message.get("channel") or {}
    channel_id = str(channel_data.get("id") or message.get("channel_id") or "")
    reference = message.get("message_reference") or {}
    attachments = message.get("attachments") or []
    content = message.get("content") or ""
    return {
        "id": str(message.get("id")),
        "channel_id": channel_id,
        "channel_name": channel_data.get("name"),
        "author_id": author.get("id"),
        "author_name": author.get("global_name") or author.get("username"),
        "content": content,
        "timestamp": message.get("timestamp"),
        "edited_timestamp": message.get("edited_timestamp"),
        "url": f"https://discord.com/channels/{GUILD_ID}/{channel_id}/{message.get('id')}",
        "reference_message_id": str(reference["message_id"]) if reference.get("message_id") else None,
        "reference_channel_id": str(reference["channel_id"]) if reference.get("channel_id") else None,
        "thread_id": channel_id if channel_data.get("type") in {10, 11, 12} else None,
        "message_type": message.get("type"),
        "attachment_count": len(attachments),
        "link_count": content.lower().count("http://") + content.lower().count("https://"),
    }


async def discord_get(path: str, params: dict[str, Any] | None = None) -> Any:
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "MD-Farsi-Localization-Discord-MCP/3.0",
    }
    async with httpx.AsyncClient(base_url=API, headers=headers, timeout=30.0) as client:
        for attempt in range(4):
            response = await client.get(path, params=params)
            if response.status_code != 429:
                response.raise_for_status()
                return response.json()

            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after is not None else 1.0
            except ValueError:
                delay = 1.0
            await asyncio.sleep(min(max(delay, 0.25), 30.0))

        response.raise_for_status()
        return response.json()


async def get_channels() -> list[dict[str, Any]]:
    return await discord_get(f"/guilds/{GUILD_ID}/channels")


async def get_message_channels() -> list[dict[str, Any]]:
    """Return message-bearing channels plus currently active thread channels."""
    channels = await get_channels()
    result = [c for c in channels if c.get("type") in {0, 5, 10, 11, 12, 15}]
    try:
        active = await discord_get(f"/guilds/{GUILD_ID}/threads/active")
        known = {str(c.get("id")) for c in result}
        for thread in active.get("threads", []):
            if str(thread.get("id")) not in known:
                result.append(thread)
    except httpx.HTTPStatusError:
        pass
    return result


@mcp.tool()
async def deep_scan_server(max_pages_per_channel: int = 0, incremental: bool = True) -> dict[str, Any]:
    """Perform a full server scan: structure, members, resources, threads, and message history."""
    history = await sync_server_history(
        max_pages_per_channel=max_pages_per_channel,
        incremental=incremental,
    )
    snapshot = await build_full_server_snapshot(include_messages=False)
    snapshot["scan"] = history
    snapshot["scan"]["indexed_messages"] = index.count()
    return snapshot


@mcp.tool()
async def get_server_overview() -> dict[str, Any]:
    """Return the complete visible server structure without message content."""
    guild = await discord_get(f"/guilds/{GUILD_ID}")
    channels = await get_channels()
    roles = await discord_get(f"/guilds/{GUILD_ID}/roles")
    return {
        "server": {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "owner_id": guild.get("owner_id"),
        },
        "categories": sum(1 for c in channels if c.get("type") == 4),
        "channels": len(channels),
        "roles": len(roles),
        "indexed_messages": index.count(),
        "indexed_channels": index.channel_count(),
        "database": DB_PATH,
    }


@mcp.tool()
async def list_channels() -> list[dict[str, Any]]:
    """List all visible channels, including categories, with permission overwrites."""
    channels = await get_channels()
    return [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "type": c.get("type"),
            "parent_id": c.get("parent_id"),
            "position": c.get("position"),
            "nsfw": c.get("nsfw", False),
            "permission_overwrites": c.get("permission_overwrites", []),
        }
        for c in sorted(channels, key=lambda item: (item.get("position", 0), str(item.get("id", ""))))
    ]


@mcp.tool()
async def list_roles() -> list[dict[str, Any]]:
    """List visible server roles and their effective Discord permission bitsets."""
    roles = await discord_get(f"/guilds/{GUILD_ID}/roles")
    return [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "position": r.get("position"),
            "managed": r.get("managed", False),
            "mentionable": r.get("mentionable", False),
            "permissions": r.get("permissions"),
        }
        for r in sorted(roles, key=lambda item: item.get("position", 0), reverse=True)
    ]


async def fetch_page(channel_id: str, before: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": 100}
    if before:
        params["before"] = before
    channel = {"id": channel_id}
    return [
        normalize_message(message, channel)
        for message in await discord_get(f"/channels/{channel_id}/messages", params=params)
    ]


@mcp.tool()
async def read_replies(message_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return indexed messages that explicitly reference a message."""
    return index.read_replies(message_id, limit)


@mcp.tool()
async def read_thread(thread_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Return indexed messages belonging to one Discord thread."""
    return index.read_thread(thread_id, limit)


async def fetch_archived_threads(parent_channel_id: str) -> list[dict[str, Any]]:
    """Best-effort discovery of public and private archived threads."""
    threads: list[dict[str, Any]] = []
    for endpoint in (
        f"/channels/{parent_channel_id}/threads/archived/public",
        f"/channels/{parent_channel_id}/threads/archived/private",
    ):
        try:
            payload = await discord_get(endpoint, params={"limit": 100})
            threads.extend(payload.get("threads", []))
        except httpx.HTTPStatusError:
            continue
    return threads


@mcp.tool()
async def sync_channel_history(
    channel_id: str,
    max_pages: int = 0,
    incremental: bool = True,
    channels: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Index accessible channel history, using the stored cursor for incremental runs."""
    visible_channels = channels if channels is not None else await get_message_channels()
    channel_map = {str(c["id"]): c for c in visible_channels}
    if channel_id not in channel_map:
        return {
            "channel_id": channel_id,
            "channel_name": None,
            "pages": 0,
            "messages_processed": 0,
            "complete": False,
            "incremental": incremental,
            "reached_cursor": False,
            "skipped": True,
            "reason": "Channel is not visible to the bot or is not a supported message channel",
        }

    channel = channel_map[channel_id]
    cursor = index.get_cursor(channel_id)
    known_newest = str(cursor["newest_message_id"]) if cursor and cursor.get("newest_message_id") else None
    before: str | None = None
    pages = 0
    processed = 0
    complete = False
    reached_cursor = False

    while True:
        page = await fetch_page(channel_id, before)
        if not page:
            complete = True
            break
        for item in page:
            item["channel_name"] = channel.get("name")
        processed += index.upsert_messages(page)
        pages += 1
        before = page[-1]["id"]
        if incremental and known_newest and any(item["id"] == known_newest for item in page):
            reached_cursor = True
            complete = bool(cursor.get("complete"))
            break
        if len(page) < 100 or (max_pages > 0 and pages >= max_pages):
            complete = len(page) < 100
            break

    newest_message_id = page[0]["id"] if pages and page else None
    index.set_cursor(channel_id, newest_message_id=newest_message_id, oldest_message_id=before, complete=complete)
    return {
        "channel_id": channel_id,
        "channel_name": channel.get("name"),
        "pages": pages,
        "messages_processed": processed,
        "complete": complete,
        "incremental": incremental,
        "reached_cursor": reached_cursor,
    }


@mcp.tool()
async def sync_server_history(max_pages_per_channel: int = 0, incremental: bool = True) -> dict[str, Any]:
    """Index accessible channels, active threads, and discoverable archived threads."""
    channels = await get_message_channels()
    known = {str(channel["id"]) for channel in channels}
    archived: list[dict[str, Any]] = []
    for channel in list(channels):
        if channel.get("type") in {0, 5, 15}:
            for thread in await fetch_archived_threads(str(channel["id"])):
                if str(thread.get("id")) not in known:
                    archived.append(thread)
                    known.add(str(thread.get("id")))
    channels.extend(archived)
    results = [
        await sync_channel_history(
            str(channel["id"]),
            max_pages_per_channel,
            incremental,
            channels,
        )
        for channel in channels
    ]
    processed_results = [result for result in results if not result.get("skipped")]
    return {
        "channels_processed": len(processed_results),
        "channels_skipped": len(results) - len(processed_results),
        "channels_discovered": len(channels),
        "archived_threads_discovered": len(archived),
        "results": results,
        "indexed_messages": index.count(),
    }


async def get_all_guild_members() -> list[dict[str, Any]]:
    """Fetch guild members in pages, respecting the bot's Discord permissions."""
    members: list[dict[str, Any]] = []
    after = "0"
    while True:
        page = await discord_get(
            f"/guilds/{GUILD_ID}/members",
            params={"limit": 1000, "after": after},
        )
        if not page:
            break
        members.extend(page)
        if len(page) < 1000:
            break
        after = str(page[-1].get("user", {}).get("id") or "")
        if not after:
            break
    return members


async def get_optional_guild_resource(path: str, key: str) -> list[dict[str, Any]]:
    try:
        payload = await discord_get(path)
        return payload if isinstance(payload, list) else payload.get(key, [])
    except httpx.HTTPStatusError:
        return []


async def build_full_server_snapshot(include_messages: bool = False, message_limit_per_channel: int = 50) -> dict[str, Any]:
    """Collect the server structure, members, roles, channels, threads and indexed activity."""
    guild = await discord_get(f"/guilds/{GUILD_ID}")
    channels = await get_channels()
    roles = await discord_get(f"/guilds/{GUILD_ID}/roles")
    members = await get_all_guild_members()
    active_threads = await discord_get(f"/guilds/{GUILD_ID}/threads/active")

    emojis = await get_optional_guild_resource(f"/guilds/{GUILD_ID}/emojis", "items")
    stickers = await get_optional_guild_resource(f"/guilds/{GUILD_ID}/stickers", "items")
    events = await get_optional_guild_resource(f"/guilds/{GUILD_ID}/scheduled-events", "items")

    channel_rows = []
    for channel in channels:
        row = {
            "id": channel.get("id"),
            "name": channel.get("name"),
            "type": channel.get("type"),
            "parent_id": channel.get("parent_id"),
            "position": channel.get("position"),
            "topic": channel.get("topic"),
            "nsfw": channel.get("nsfw", False),
            "slowmode": channel.get("rate_limit_per_user", 0),
            "permissions": channel.get("permission_overwrites", []),
            "thread_metadata": channel.get("thread_metadata"),
        }
        if include_messages and channel.get("type") in {0, 5, 10, 11, 12, 15}:
            row["messages"] = index.read_channel(str(channel["id"]), message_limit_per_channel)
        channel_rows.append(row)

    member_rows = []
    for member in members:
        user = member.get("user") or {}
        member_rows.append({
            "id": user.get("id"),
            "username": user.get("username"),
            "global_name": user.get("global_name"),
            "bot": user.get("bot", False),
            "joined_at": member.get("joined_at"),
            "roles": member.get("roles", []),
            "nick": member.get("nick"),
            "communication_disabled_until": member.get("communication_disabled_until"),
        })

    return {
        "server": {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "owner_id": guild.get("owner_id"),
            "description": guild.get("description"),
            "icon": guild.get("icon"),
            "banner": guild.get("banner"),
            "verification_level": guild.get("verification_level"),
            "default_message_notifications": guild.get("default_message_notifications"),
            "explicit_content_filter": guild.get("explicit_content_filter"),
            "features": guild.get("features", []),
            "preferred_locale": guild.get("preferred_locale"),
            "system_channel_id": guild.get("system_channel_id"),
            "rules_channel_id": guild.get("rules_channel_id"),
            "public_updates_channel_id": guild.get("public_updates_channel_id"),
        },
        "categories": [c for c in channel_rows if c.get("type") == 4],
        "channels": [c for c in channel_rows if c.get("type") != 4],
        "roles": roles,
        "members": member_rows,
        "active_threads": active_threads.get("threads", []),
        "emojis": emojis,
        "stickers": stickers,
        "scheduled_events": events,
        "indexed_activity": {
            "messages": index.count(),
            "channels": index.channel_count(),
            "channel_statistics": index.channel_stats(),
            "author_statistics": index.author_stats(),
        },
    }


@mcp.tool()
async def get_server_snapshot(include_messages: bool = False, message_limit_per_channel: int = 50, full: bool = False) -> dict[str, Any]:
    """Return a detailed server snapshot; full=True collects members and server resources too."""
    guild = await discord_get(f"/guilds/{GUILD_ID}")
    channels = await get_channels()
    roles = await discord_get(f"/guilds/{GUILD_ID}/roles")
    payload = {
        "server": {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "owner_id": guild.get("owner_id"),
            "description": guild.get("description"),
            "verification_level": guild.get("verification_level"),
            "features": guild.get("features", []),
        },
        "categories": [c for c in channels if c.get("type") == 4],
        "channels": channels,
        "roles": roles,
        "indexed_messages": index.count(),
        "indexed_channels": index.channel_count(),
    }
    if include_messages:
        payload["messages"] = {
            str(channel["id"]): index.read_channel(str(channel["id"]), message_limit_per_channel)
            for channel in channels
            if channel.get("type") in {0, 5, 10, 11, 12, 15}
        }
    return payload


@mcp.tool()
async def get_channel_statistics() -> list[dict[str, Any]]:
    """Return aggregate activity statistics for every indexed channel."""
    return index.channel_stats()


@mcp.tool()
async def get_author_statistics(limit: int = 100) -> list[dict[str, Any]]:
    """Return aggregate message counts by author; no message content is returned."""
    return index.author_stats(limit)


@mcp.tool()
async def get_news_digest(hours: int = 24, limit: int = 12, mark_read: bool = False) -> dict[str, Any]:
    """Return deterministic project news from indexed Discord messages."""
    return news_engine.digest(hours=hours, limit=limit, mark_read=mark_read)


@mcp.tool()
async def get_project_intelligence(hours: int = 24, limit: int = 12) -> dict[str, Any]:
    """Return deterministic event-level intelligence from indexed Discord history."""
    return intelligence_engine.build(hours=hours, limit=limit)


@mcp.tool()
async def get_sync_status() -> dict[str, Any]:
    """Return current local history-index status."""
    return {
        "database": DB_PATH,
        "indexed_messages": index.count(),
        "indexed_channels": index.channel_count(),
    }


@mcp.tool()
async def search_index(query: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search indexed message content."""
    return index.search(query.strip(), limit) if query.strip() else []


@mcp.tool()
async def read_channel(channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Read the newest indexed messages from one visible channel."""
    return index.read_channel(channel_id, limit)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=HOST, port=PORT)
