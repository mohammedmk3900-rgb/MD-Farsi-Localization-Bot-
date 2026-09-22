from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import ProjectSnapshot
from app.integrations.paratranz import ParaTranzClient
from app.persistence.database import Database
from app.services.events import Event, EventBus


class ProjectService:
    def __init__(self, settings, bus: EventBus, database: Database):
        self.settings = settings
        self.bus = bus
        self.database = database

    def sync(self) -> ProjectSnapshot:
        snapshot = ParaTranzClient(self.settings).project_snapshot()
        payload = snapshot.model_dump(mode="json")
        captured = snapshot.captured_at.astimezone(timezone.utc).isoformat()

        self.database.save_snapshot(captured, snapshot.schema_version, {"project": payload})
        self.database.append_event("project.snapshot", captured, payload)
        self.bus.publish(Event("project.snapshot", payload))
        return snapshot
