from __future__ import annotations

from app.services.discord_notifications import DiscordNotificationService


class DiscordRouter:
    """Maps platform events to stable Discord channel IDs."""

    def __init__(self, settings):
        self.settings = settings
        self.notifications = DiscordNotificationService(settings)

    def progress(self, message: str):
        return self.notifications.send(self.settings.channel_progress, message)

    def stats(self, message: str):
        return self.notifications.send(self.settings.channel_stats, message)

    def achievements(self, message: str):
        return self.notifications.send(self.settings.channel_achievements, message)

    def health(self, message: str):
        return self.notifications.send(self.settings.channel_health, message)

    def report(self, message: str):
        return self.notifications.send(self.settings.channel_reports, message)

    def glossary(self, message: str):
        return self.notifications.send(self.settings.channel_glossary, message)
