from __future__ import annotations

from app.runtime import bus, project_service
from app.services.events import Event


def sync_project() -> dict:
    snapshot = project_service.sync()
    return snapshot.model_dump(mode="json")


def publish_health(health: dict) -> None:
    bus.publish(Event("health.checked", health))


def publish_achievement(achievement: dict) -> None:
    bus.publish(Event("achievement.reached", achievement))
