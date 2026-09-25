from __future__ import annotations

from app.domain.models import Priority, Task, TaskStatus


class TaskService:
    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def create(
        self,
        task_id: int | None = None,
        title: str = "",
        scope: str = "",
        priority: Priority = Priority.NORMAL,
        due_at: str | None = None,
    ) -> Task:
        if not title.strip():
            raise ValueError("title is required")
        if task_id is None:
            task_id = self._next_id
        self._next_id = max(self._next_id, task_id + 1)
        task = Task(
            id=task_id,
            title=title.strip(),
            scope=scope.strip(),
            priority=priority,
            due_at=due_at,
        )
        self._tasks[task.id] = task
        return task

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
        return {"total": len(self._tasks), "by_status": counts, "review_queue": counts[TaskStatus.REVIEW.value]}

    def claim(self, task: Task, member_id: str) -> Task:
        if task.status not in {TaskStatus.AVAILABLE, TaskStatus.IN_PROGRESS}:
            raise ValueError("task cannot be claimed")
        if task.owner not in {None, "", member_id}:
            raise ValueError("task is owned by another member")
        task.owner = member_id
        task.status = TaskStatus.IN_PROGRESS
        return task

    def submit(self, task: Task, member_id: str) -> Task:
        if task.owner != member_id:
            raise ValueError("only the task owner can submit it")
        if task.status != TaskStatus.IN_PROGRESS:
            raise ValueError("task is not in progress")
        task.status = TaskStatus.REVIEW
        return task

    def complete(self, task: Task, reviewer_id: str) -> Task:
        if task.status != TaskStatus.REVIEW:
            raise ValueError("task is not awaiting review")
        task.reviewer = reviewer_id
        task.status = TaskStatus.DONE
        return task
