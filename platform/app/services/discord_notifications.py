from __future__ import annotations

from app.integrations.discord_app import DiscordApp


class DiscordNotificationService:
    """All automated Discord output goes through MD news, never Discord webhooks.

    Discord credentials are required only when a Discord operation is actually
    executed. Constructing the platform, importing the application, and running
    offline/unit tests must not require production credentials.
    """

    def __init__(self, settings):
        self.settings = settings
        self._discord: DiscordApp | None = None

    @property
    def discord(self) -> DiscordApp:
        if self._discord is None:
            self._discord = DiscordApp(self.settings.discord_bot_token)
        return self._discord

    @discord.setter
    def discord(self, value: DiscordApp) -> None:
        self._discord = value

    def send(self, channel_id: str, content: str) -> dict:
        if not channel_id:
            raise ValueError("Discord channel ID is required")
        return self.discord.send(channel_id, content)

    def embed(self, channel_id: str, title: str, description: str) -> dict:
        if not channel_id:
            raise ValueError("Discord channel ID is required")
        return self.discord.send_embed(channel_id, title=title, description=description)
