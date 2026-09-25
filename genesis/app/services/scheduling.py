from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reminder:
    member_id: str
    task_id: int
    message: str


class ReminderService:
    def overdue(self, tasks: list, now_iso: str) -> list[Reminder]:
        reminders = []
        for task in tasks:
            if task.due_at and task.due_at < now_iso and task.status.value not in {"done", "cancelled"} and task.owner:
                reminders.append(Reminder(task.owner, task.id, f"مأموریت #{task.id} از موعد گذشته است."))
        return reminders
