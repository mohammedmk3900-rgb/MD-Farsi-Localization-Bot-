from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import Priority, Task, TaskStatus, validate_task_transition
from app.persistence.store import Store


class TaskService:
    """Durable task workflow. SQLite is the source of operational task state."""

    def __init__(self, store: Store):
        self.store = store

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _from_row(row: dict) -> Task:
        return Task(
            id=int(row["id"]),
            title=row["title"],
            scope=row["scope"],
            owner=row["owner"],
            reviewer=row["reviewer"],
            priority=Priority(row["priority"]),
            status=TaskStatus(row["status"]),
            due_at=row["due_at"],
        )

    def create(self, *, title: str, scope: str = "", priority: Priority = Priority.NORMAL,
               due_at: str | None = None) -> Task:
        if not title.strip():
            raise ValueError("title is required")
        task_id = self.store.create_task(title=title.strip(), scope=scope.strip(),
                                         priority=priority.value, due_at=due_at, created_at=self._now())
        return self.get(task_id)

    def get(self, task_id: int) -> Task:
        row = self.store.task(task_id)
        if row is None:
            raise KeyError(f"task #{task_id} not found")
        return self._from_row(row)

    def list(self, status: TaskStatus | None = None) -> list[Task]:
        return [self._from_row(row) for row in self.store.tasks(None if status is None else status.value)]

    def summary(self) -> dict:
        counts = {status.value: 0 for status in TaskStatus}
        tasks = self.list()
        for task in tasks:
            counts[task.status.value] += 1
        return {"total": len(tasks), "by_status": counts, "review_queue": counts[TaskStatus.REVIEW.value]}

    def claim(self, task: Task, member_id: str) -> Task:
        validate_task_transition(task.status, TaskStatus.IN_PROGRESS)
        if task.owner not in {None, "", member_id}:
            raise ValueError("task is owned by another member")
        self.store.transition_task(task.id, target_status=TaskStatus.IN_PROGRESS.value,
                                  updated_at=self._now(),
                                  allowed_from=(TaskStatus.AVAILABLE.value, TaskStatus.IN_PROGRESS.value),
                                  owner=member_id, expected_owner=member_id)
        return self.get(task.id)

    def submit(self, task: Task, member_id: str) -> Task:
        if task.owner != member_id:
            raise ValueError("only the task owner can submit it")
        validate_task_transition(task.status, TaskStatus.REVIEW)
        self.store.transition_task(task.id, target_status=TaskStatus.REVIEW.value,
                                  updated_at=self._now(),
                                  allowed_from=(TaskStatus.IN_PROGRESS.value,),
                                  expected_owner=member_id)
        return self.get(task.id)

    def complete(self, task: Task, reviewer_id: str) -> Task:
        validate_task_transition(task.status, TaskStatus.DONE)
        self.store.transition_task(task.id, target_status=TaskStatus.DONE.value,
                                  updated_at=self._now(),
                                  allowed_from=(TaskStatus.REVIEW.value,),
                                  reviewer=reviewer_id)
        return self.get(task.id)
