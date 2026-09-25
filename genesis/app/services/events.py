from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.persistence.store import Store


@dataclass(frozen=True)
class GenesisEvent:
    event_type: str
    actor: str | None
    payload: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class Notification:
    id: int
    recipient: str
    event_type: str
    message: str
    created_at: str


class EventService:
    """Durable event + notification boundary for application services."""

    def __init__(self, store: Store):
        self.store = store

    def publish(
        self,
        event_type: str,
        actor: str | None,
        payload: dict[str, Any],
        *,
        notifications: list[tuple[str, str]] | None = None,
    ) -> GenesisEvent:
        created_at = datetime.now(timezone.utc).isoformat()
        event = GenesisEvent(event_type, actor, payload, created_at)
        self.store.record_event(event_type, actor, created_at, payload)
        for recipient, message in notifications or []:
            self.store.enqueue_notification(recipient, event_type, message, created_at)
        return event

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.events(limit)

    def pending_notifications(self, recipient: str | None = None) -> list[Notification]:
        return [
            Notification(
                int(row["id"]),
                str(row["recipient"]),
                str(row["event_type"]),
                str(row["message"]),
                str(row["created_at"]),
            )
            for row in self.store.notifications(recipient=recipient, delivered=False)
        ]

    def acknowledge(self, notification_id: int) -> None:
        self.store.mark_notification_delivered(notification_id)
