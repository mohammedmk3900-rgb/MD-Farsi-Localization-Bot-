from __future__ import annotations

from app.services.events import Event


class NotificationService:
    """Central notification boundary. Discord is an adapter, not the source of logic."""

    def __init__(self, application):
        self.application = application

    def handle(self, event: Event) -> None:
        self.application.record(
            "notification.dispatched",
            {"event": event.name, "payload": event.payload},
        )
