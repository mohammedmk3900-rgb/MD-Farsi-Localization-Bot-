from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.models import Priority, Task
from app.persistence.store import Store
from app.services.missions import Mission


@dataclass(frozen=True)
class MissionRecord:
    id: int
    title: str
    scope: str
    priority: Priority
    reward: int
    status: str
    task_id: int | None
    created_at: str


class MissionEngineService:
    """Turns generated missions into durable operational work."""

    def __init__(self, store: Store, missions, tasks, events):
        self.store = store
        self.missions = missions
        self.tasks = tasks
        self.events = events

    def generate(self, scopes: list[str], limit: int = 5) -> list[MissionRecord]:
        generated = self.missions.generate(scopes, limit)
        result: list[MissionRecord] = []
        for mission in generated:
            result.append(self.create(mission))
        return result

    def create(self, mission: Mission) -> MissionRecord:
        created_at = datetime.now(timezone.utc).isoformat()
        mission_id = self.store.next_mission_id()
        record = MissionRecord(
            mission_id, mission.title, mission.scope, mission.priority,
            mission.reward, "open", None, created_at,
        )
        self.store.save_mission(record)
        self.events.publish(
            "mission.created",
            None,
            {"mission_id": mission_id, "title": mission.title, "scope": mission.scope},
        )
        return record

    def activate(self, mission_id: int) -> Task:
        record = self._get(mission_id)
        if record.status != "open":
            raise ValueError("mission is not open")
        task = self.tasks.create(
            title=record.title,
            scope=record.scope,
            priority=record.priority,
        )
        updated = MissionRecord(
            record.id, record.title, record.scope, record.priority,
            record.reward, "active", task.id, record.created_at,
        )
        self.store.save_mission(updated)
        self.events.publish(
            "mission.activated",
            None,
            {"mission_id": record.id, "task_id": task.id},
        )
        return task

    def list(self, status: str | None = None) -> list[MissionRecord]:
        return [
            MissionRecord(
                int(row["id"]), str(row["title"]), str(row["scope"]),
                row["priority"], int(row["reward"]), str(row["status"]),
                row["task_id"], str(row["created_at"]),
            )
            for row in self.store.missions(status=status)
        ]

    def _get(self, mission_id: int) -> MissionRecord:
        for mission in self.list():
            if mission.id == mission_id:
                return mission
        raise KeyError(f"mission #{mission_id} not found")
