from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import httpx


class DiscordAuditService:
    """Collects bounded, public-safe Discord structure/activity metrics."""

    def __init__(self, settings):
        self.settings = settings
        self.recent_messages = max(0, settings.recent_messages_per_channel)

    def _client(self) -> httpx.Client:
        token = self.settings.discord_bot_token.strip()
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        return httpx.Client(
            base_url="https://discord.com/api/v10",
            headers={
                "Authorization": f"Bot {token}",
                "User-Agent": "MD-Farsi-Localization-Platform/2.0",
            },
            timeout=30,
        )

    def _get(self, client: httpx.Client, path: str, **kwargs):
        response = client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    def collect(self) -> dict:
        if not self.settings.discord_bot_token or not self.settings.discord_guild_id:
            raise RuntimeError("DISCORD_BOT_TOKEN and DISCORD_GUILD_ID are required")

        guild_id = self.settings.discord_guild_id
        with self._client() as client:
            guild = self._get(client, f"/guilds/{guild_id}")
            channels = self._get(client, f"/guilds/{guild_id}/channels")
            roles = self._get(client, f"/guilds/{guild_id}/roles")

        channel_rows = [
            {
                "id": str(c.get("id")),
                "name": c.get("name"),
                "type": c.get("type"),
                "parent_id": str(c["parent_id"]) if c.get("parent_id") else None,
                "position": c.get("position", 0),
                "nsfw": bool(c.get("nsfw", False)),
                "permission_overwrites": len(c.get("permission_overwrites", [])),
            }
            for c in sorted(channels, key=lambda x: (x.get("position", 0), str(x.get("id", ""))))
        ]
        role_rows = [
            {
                "id": str(r.get("id")),
                "name": r.get("name"),
                "position": r.get("position", 0),
                "managed": bool(r.get("managed", False)),
                "mentionable": bool(r.get("mentionable", False)),
                "permissions": r.get("permissions"),
            }
            for r in sorted(roles, key=lambda x: x.get("position", 0), reverse=True)
        ]
        return {
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
            "collection": {
                "recent_messages_per_channel": self.recent_messages,
                "note": "Structure only; message content and member identity are never stored.",
            },
        }

    def persist(self, output: str = "data/discord_audit.json") -> dict:
        payload = self.collect()
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload
