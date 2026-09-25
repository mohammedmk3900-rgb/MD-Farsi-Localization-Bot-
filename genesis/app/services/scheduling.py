from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.persistence.store import Store


@dataclass(frozen=True)
class Reminder:
    member_id: str
    task_id: int
    message: str


class ReminderService:
    def __init__(self, store: Store | None = None):
        self.store = store

    def overdue(self, tasks: list, now_iso: str) -> list[Reminder]:
        reminders = []
        for task in tasks:
            if task.due_at and task.due_at < now_iso and task.status.value not in {"done", "cancelled"} and task.owner:
                reminders.append(Reminder(task.owner, task.id, f"مأموریت #{task.id} از موعد گذشته است."))
        return reminders

    def schedule(self, member_id: str, task_id: int, run_at: str, message: str) -> int:
        if self.store is None:
            raise RuntimeError("persistent store is required")
        return self.store.schedule(
            "reminder", task_id, member_id, run_at, message,
            datetime.now(timezone.utc).isoformat(),
        )

    def due(self, now_iso: str) -> list[Reminder]:
        if self.store is None:
            return []
        rows = self.store.due_schedules(now_iso)
        reminders = [
            Reminder(str(row["actor"]), int(row["target_id"]), row["message"])
            for row in rows if row["kind"] == "reminder"
        ]
        for row in rows:
            if row["kind"] == "reminder":
                self.store.mark_schedule_delivered(int(row["id"]))
        return reminders


@dataclass(frozen=True)
class MissionSchedule:
    id: int
    mission_id: int
    run_at: str
    message: str


class MissionScheduler:
    def __init__(self, store: Store):
        self.store = store

    def schedule(self, mission_id: int, run_at: str, message: str) -> MissionSchedule:
        schedule_id = self.store.schedule(
            "mission", mission_id, None, run_at, message,
            datetime.now(timezone.utc).isoformat(),
        )
        return MissionSchedule(schedule_id, mission_id, run_at, message)

    def due(self, now_iso: str) -> list[MissionSchedule]:
        rows = self.store.due_schedules(now_iso)
        result = [
            MissionSchedule(int(row["id"]), int(row["target_id"]), row["run_at"], row["message"])
            for row in rows if row["kind"] == "mission"
        ]
        for row in rows:
            if row["kind"] == "mission":
                self.store.mark_schedule_delivered(int(row["id"]))
        return result
