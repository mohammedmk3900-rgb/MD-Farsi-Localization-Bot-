from __future__ import annotations

from app.integrations.discord_app import DiscordApp


class DiscordNotificationService:
    """All automated Discord output goes through MD news, never Discord webhooks."""

    def __init__(self, settings):
        self.settings = settings
        self.discord = DiscordApp(settings.discord_bot_token)

    def send(self, channel_id: str, content: str) -> dict:
        if not channel_id:
            raise ValueError("Discord channel ID is required")
        return self.discord.send(channel_id, content)

    def embed(self, channel_id: str, title: str, description: str) -> dict:
        if not channel_id:
            raise ValueError("Discord channel ID is required")
        return self.discord.send_embed(channel_id, title=title, description=description)
