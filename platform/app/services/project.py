from __future__ import annotations

from app.domain.models import ProjectSnapshot
from app.integrations.paratranz import ParaTranzClient
from app.services.events import Event, EventBus


class ProjectService:
    def __init__(self, settings, bus: EventBus):
        self.settings = settings
        self.bus = bus

    def sync(self) -> ProjectSnapshot:
        snapshot = ParaTranzClient(self.settings).project_snapshot()
        self.bus.publish(
            Event("project.snapshot", snapshot.model_dump(mode="json"))
        )
        return snapshot
