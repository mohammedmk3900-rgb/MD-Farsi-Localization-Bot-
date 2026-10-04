from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.persistence.database import Database


STATUSES = ("available", "in_progress", "review", "done", "cancelled")


class TaskService:
    def __init__(self, database: Database):
        self.database = database

    def create(
        self,
        title: str,
        owner: str | None = None,
        scope: str = "",
        priority: str = "normal",
        due_at: str | None = None,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("title is required")
        if priority not in {"low", "normal", "high", "urgent"}:
            raise ValueError("invalid priority")
        return self.database.create_task(
            title=title.strip(),
            owner=owner,
            scope=scope.strip(),
            priority=priority,
            due_at=due_at,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def list(self, status: str | None = None, owner: str | None = None) -> list[dict[str, Any]]:
        if status is not None and status not in STATUSES:
            raise ValueError("invalid status")
        return self.database.list_tasks(status=status, owner=owner)

    def claim(self, task_id: int, owner: str) -> dict[str, Any]:
        if not owner.strip():
            raise ValueError("owner is required")
        task = self.database.get_task(task_id)
        if not task:
            raise KeyError("task not found")
        if task["status"] not in {"available", "in_progress"}:
            raise ValueError("task cannot be claimed")
        if task["owner"] not in {None, "", owner}:
            raise ValueError("task is owned by another member")
        return self.database.update_task(task_id, status="in_progress", owner=owner)

    def submit(self, task_id: int, owner: str) -> dict[str, Any]:
        task = self.database.get_task(task_id)
        if not task:
            raise KeyError("task not found")
        if task["owner"] != owner:
            raise ValueError("only the task owner can submit it")
        return self.database.update_task(task_id, status="review")

    def complete(self, task_id: int, reviewer: str) -> dict[str, Any]:
        task = self.database.get_task(task_id)
        if not task:
            raise KeyError("task not found")
        if task["status"] != "review":
            raise ValueError("task is not awaiting review")
        return self.database.update_task(task_id, status="done", reviewer=reviewer)

    def cancel(self, task_id: int) -> dict[str, Any]:
        task = self.database.get_task(task_id)
        if not task:
            raise KeyError("task not found")
        return self.database.update_task(task_id, status="cancelled")

    def summary(self) -> dict[str, int]:
        rows = self.database.list_tasks()
        return {status: sum(1 for row in rows if row["status"] == status) for status in STATUSES}
