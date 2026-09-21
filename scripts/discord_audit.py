"""Generate a sanitized, public-safe Discord server audit snapshot.

Never writes message content, member names/IDs, bot tokens, or other member PII.
"""
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx

API = "https://discord.com/api/v10"
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD_ID = os.getenv("DISCORD_GUILD_ID", "").strip()
RECENT_MESSAGES = max(0, int(os.getenv("DISCORD_AUDIT_RECENT_MESSAGES", "200")))
OUT = Path(os.getenv("DISCORD_AUDIT_OUTPUT", "data/discord_audit.json"))
if not TOKEN or not GUILD_ID:
    raise RuntimeError("DISCORD_BOT_TOKEN and DISCORD_GUILD_ID are required")

def get(client: httpx.Client, path: str, **kwargs: Any) -> Any:
    response = client.get(path, **kwargs)
    response.raise_for_status()
    return response.json()

def recent_activity(client: httpx.Client, channel_id: str, channel_name: str) -> dict[str, Any]:
    if RECENT_MESSAGES <= 0:
        return {"channel_name": channel_name, "sampled_messages": 0}
    remaining, before, count = RECENT_MESSAGES, None, 0
    authors: set[str] = set()
    newest = oldest = None
    while remaining:
        limit = min(100, remaining)
        params: dict[str, Any] = {"limit": limit}
        if before:
            params["before"] = before
        messages = get(client, f"{API}/channels/{channel_id}/messages", params=params)
        if not messages:
            break
        for message in messages:
            count += 1
            author = message.get("author") or {}
            if author.get("id"):
                authors.add(str(author["id"]))
            ts = message.get("timestamp")
            if ts:
                newest = newest or ts
                oldest = ts
        before = str(messages[-1]["id"])
        remaining -= len(messages)
        if len(messages) < limit:
            break
    return {
        "channel_name": channel_name,
        "sampled_messages": count,
        "unique_authors": len(authors),
        "newest_message_at": newest,
        "oldest_sampled_message_at": oldest,
    }

def main() -> None:
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "MD-Farsi-Localization-Discord-Audit/1.0",
    }
    with httpx.Client(headers=headers, timeout=30.0) as client:
        guild = get(client, f"{API}/guilds/{GUILD_ID}")
        channels = get(client, f"{API}/guilds/{GUILD_ID}/channels")
        roles = get(client, f"{API}/guilds/{GUILD_ID}/roles")
        channel_rows = []
        activity = []
        for channel in sorted(channels, key=lambda c: (c.get("position", 0), str(c.get("id", "")))):
            channel_rows.append({
                "id": str(channel.get("id")),
                "name": channel.get("name"),
                "type": channel.get("type"),
                "parent_id": str(channel["parent_id"]) if channel.get("parent_id") else None,
                "position": channel.get("position", 0),
                "nsfw": bool(channel.get("nsfw", False)),
                "permission_overwrites": len(channel.get("permission_overwrites", [])),
            })
            if channel.get("type") in {0, 5, 10, 11, 12, 15}:
                try:
                    activity.append(recent_activity(client, str(channel["id"]), str(channel.get("name", ""))))
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in {403, 404}:
                        raise
                    activity.append({"channel_name": channel.get("name"), "sampled_messages": 0, "unavailable": True})
        role_rows = [{
            "id": str(role.get("id")),
            "name": role.get("name"),
            "position": role.get("position", 0),
            "managed": bool(role.get("managed", False)),
            "mentionable": bool(role.get("mentionable", False)),
            "permissions": role.get("permissions"),
        } for role in sorted(roles, key=lambda r: r.get("position", 0), reverse=True)]

    payload = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Discord API",
        "privacy": {
            "message_content_stored": False,
            "member_names_stored": False,
            "member_ids_stored": False,
            "bot_token_stored": False,
        },
        "server": {
            "id": str(guild.get("id")),
            "name": guild.get("name"),
            "categories": sum(1 for c in channels if c.get("type") == 4),
            "channels": len(channels),
            "roles": len(roles),
        },
        "channels": channel_rows,
        "roles": role_rows,
        "activity": activity,
        "collection": {
            "recent_messages_per_channel": RECENT_MESSAGES,
            "note": "Bounded activity metrics only; message content is deliberately excluded.",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discord audit written to {OUT} • {len(channel_rows)} channels • {len(role_rows)} roles")

if __name__ == "__main__":
    main()
