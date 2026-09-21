from __future__ import annotations

from app.integrations.discord_app import DiscordApp
from app.services.events import Event, EventBus


class Automation:
    """Deterministic automation: collect -> persist -> notify. Human review remains human."""

    def __init__(self, application, discord: DiscordApp | None = None):
        self.application = application
        self.discord = discord

    def attach(self, bus: EventBus) -> None:
        bus.subscribe("project.snapshot", self.on_project_snapshot)
        bus.subscribe("health.checked", self.on_health)
        bus.subscribe("achievement.reached", self.on_achievement)

    def on_project_snapshot(self, event: Event) -> None:
        self.application.record("automation.project_snapshot", event.payload)

    def on_health(self, event: Event) -> None:
        self.application.record("automation.health", event.payload)

    def on_achievement(self, event: Event) -> None:
        self.application.record("automation.achievement", event.payload)
