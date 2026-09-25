from __future__ import annotations

from app.domain.models import Priority, Task, TaskStatus


class TaskService:
    def create(
        self,
        task_id: int,
        title: str,
        scope: str = "",
        priority: Priority = Priority.NORMAL,
        due_at: str | None = None,
    ) -> Task:
        if not title.strip():
            raise ValueError("title is required")
        return Task(
            id=task_id,
            title=title.strip(),
            scope=scope.strip(),
            priority=priority,
            due_at=due_at,
        )

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
