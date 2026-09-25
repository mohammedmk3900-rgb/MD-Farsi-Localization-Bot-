from __future__ import annotations

from app.domain.models import Task, TaskStatus


class ReportService:
    def task_summary(self, tasks: list[Task]) -> dict:
        counts = {status.value: 0 for status in TaskStatus}
        for task in tasks:
            counts[task.status.value] += 1
        return {
            "total": len(tasks),
            "by_status": counts,
            "review_queue": counts[TaskStatus.REVIEW.value],
        }
