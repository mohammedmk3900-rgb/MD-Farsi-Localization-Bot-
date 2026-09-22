from __future__ import annotations

from datetime import timezone

from app.domain.models import ProjectSnapshot
from app.integrations.paratranz import ParaTranzClient
from app.persistence.database import Database
from app.services.events import Event, EventBus


class ProjectService:
    """Owns the only live ParaTranz project synchronization path."""

    def __init__(self, settings, bus: EventBus, database: Database):
        self.settings = settings
        self.bus = bus
        self.database = database

    def sync(self) -> ProjectSnapshot:
        snapshot = ParaTranzClient(self.settings).project_snapshot()
        payload = snapshot.model_dump(mode="json")
        captured = snapshot.captured_at.astimezone(timezone.utc).isoformat()
        canonical = {
            "schema": 1,
            "snapshot_type": "project",
            "captured_at": captured,
            "project": payload,
        }
        self.database.save_snapshot(captured, 1, canonical)
        self.database.append_event("project.snapshot", captured, payload)
        self.bus.publish(Event("project.snapshot", payload))
        return snapshot
