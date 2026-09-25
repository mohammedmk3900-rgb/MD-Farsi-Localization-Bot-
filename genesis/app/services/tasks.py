from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import Priority, Task, TaskStatus
from app.persistence.store import Store


class TaskService:
    def __init__(self, store: Store | None = None):
        self.store = store
        self._tasks: dict[int, Task] = {}
        if store is not None:
            self._tasks = {task.id: task for task in store.tasks()}
        self._next_id = max(self._tasks, default=0) + 1

    def _touch(self, task: Task) -> Task:
        task.updated_at = datetime.now(timezone.utc).isoformat()
        if task.created_at is None:
            task.created_at = task.updated_at
        if self.store is not None:
            self.store.save_task(task)
        return task

    def create(self, task_id: int | None = None, title: str = "", scope: str = "",
               priority: Priority = Priority.NORMAL, due_at: str | None = None) -> Task:
        if not title.strip():
            raise ValueError("title is required")
        if task_id is None:
            task_id = self._next_id
        self._next_id = max(self._next_id, task_id + 1)
        task = Task(id=task_id, title=title.strip(), scope=scope.strip(),
                    priority=priority, due_at=due_at)
        self._tasks[task.id] = task
        return self._touch(task)

    def get(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"task #{task_id} not found") from exc

    def list(self, status: TaskStatus | None = None) -> list[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        return sorted(tasks, key=lambda task: task.id)

    def summary(self) -> dict:
        counts = {status.value: 0 for status in TaskStatus}
        for task in self._tasks.values():
            counts[task.status.value] += 1
        return {"total": len(self._tasks), "by_status": counts,
                "review_queue": counts[TaskStatus.REVIEW.value]}

    def claim(self, task: Task, member_id: str) -> Task:
        if task.status not in {TaskStatus.AVAILABLE, TaskStatus.IN_PROGRESS}:
            raise ValueError("task cannot be claimed")
        if task.owner not in {None, "", member_id}:
            raise ValueError("task is owned by another member")
        task.owner = member_id
        task.status = TaskStatus.IN_PROGRESS
        return self._touch(task)

    def submit(self, task: Task, member_id: str) -> Task:
        if task.owner != member_id:
            raise ValueError("only the task owner can submit it")
        if task.status != TaskStatus.IN_PROGRESS:
            raise ValueError("task is not in progress")
        task.status = TaskStatus.REVIEW
        return self._touch(task)

    def complete(self, task: Task, reviewer_id: str) -> Task:
        if task.status != TaskStatus.REVIEW:
            raise ValueError("task is not awaiting review")
        task.reviewer = reviewer_id
        task.status = TaskStatus.DONE
        return self._touch(task)

    def cancel(self, task: Task) -> Task:
        if task.status == TaskStatus.DONE:
            raise ValueError("completed task cannot be cancelled")
        task.status = TaskStatus.CANCELLED
        return self._touch(task)
