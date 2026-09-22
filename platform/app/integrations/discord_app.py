from __future__ import annotations

import httpx


class DiscordApp:
    """The MD news application adapter for Discord REST."""

    BASE = "https://discord.com/api/v10"

    def __init__(self, token: str):
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN is required")
        token = token.strip()
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        self.headers = {
            "Authorization": f"Bot {token}",
            "User-Agent": "MD-Farsi-Localization/2.0",
        }

    def _request(self, method: str, path: str, **kwargs):
        with httpx.Client(base_url=self.BASE, headers=self.headers, timeout=30) as client:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None

    def identity(self) -> dict:
        return self._request("GET", "/users/@me")

    def guild(self, guild_id: str) -> dict:
        return self._request("GET", f"/guilds/{guild_id}")

    def send(self, channel_id: str, content: str) -> dict:
        return self._request("POST", f"/channels/{channel_id}/messages", json={"content": content})

    def send_embed(self, channel_id: str, *, title: str, description: str, color: int = 0x00D9FF) -> dict:
        return self._request(
            "POST",
            f"/channels/{channel_id}/messages",
            json={"embeds": [{"title": title, "description": description, "color": color}]},
        )
