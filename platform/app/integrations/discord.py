from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.domain.models import DiscordSnapshot


class DiscordClient:
    base_url = "https://discord.com/api/v10"

    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.discord_bot_token or not settings.discord_guild_id:
            raise RuntimeError("DISCORD_BOT_TOKEN and DISCORD_GUILD_ID are required")

    def _client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "Authorization": f"Bot {self.settings.discord_bot_token}",
                "User-Agent": "MD-Farsi-Localization-Platform/1.0",
            },
            timeout=30,
        )

    def snapshot(self) -> DiscordSnapshot:
        with self._client() as client:
            me = client.get(f"{self.base_url}/users/@me")
            me.raise_for_status()

            guild = client.get(f"{self.base_url}/guilds/{self.settings.discord_guild_id}")
            guild.raise_for_status()

            channels_response = client.get(
                f"{self.base_url}/guilds/{self.settings.discord_guild_id}/channels"
            )
            channels_response.raise_for_status()

            roles_response = client.get(
                f"{self.base_url}/guilds/{self.settings.discord_guild_id}/roles"
            )
            roles_response.raise_for_status()

            channels = channels_response.json()
            roles = roles_response.json()

        return DiscordSnapshot(
            captured_at=datetime.now(timezone.utc),
            guild_id=str(guild.json()["id"]),
            guild_name=str(guild.json()["name"]),
            categories=sum(c.get("type") == 4 for c in channels),
            channels=len(channels),
            roles=len(roles),
        )
