from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.persistence.store import Store


@dataclass(frozen=True)
class Reminder:
    member_id: str
    task_id: int
    message: str


class ReminderService:
    def overdue(self, tasks: list, now_iso: str) -> list[Reminder]:
        return [
            Reminder(task.owner, task.id, f"مأموریت #{task.id} از موعد گذشته است.")
            for task in tasks
            if task.due_at and task.due_at < now_iso
            and task.status.value not in {"done", "cancelled"} and task.owner
        ]


class Scheduler:
    """Small durable scheduler primitive with leases and bounded retry metadata."""

    def __init__(self, store: Store, *, lease_seconds: int = 300, retry_seconds: int = 60):
        self.store = store
        self.lease_seconds = max(10, lease_seconds)
        self.retry_seconds = max(1, retry_seconds)

    def register(self, job_id: str, next_run_at: str | None = None) -> None:
        self.store.upsert_scheduler_job(job_id, next_run_at=next_run_at)

    def claim(self, job_id: str, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.store.claim_scheduler_job(
            job_id, now_iso=now.isoformat(),
            lease_until=(now + timedelta(seconds=self.lease_seconds)).isoformat(),
        )

    def succeed(self, job_id: str, next_run_at: str | None = None) -> None:
        self.store.finish_scheduler_job(job_id, next_run_at=next_run_at)

    def fail(self, job_id: str, error: Exception | str) -> None:
        now = datetime.now(timezone.utc)
        self.store.fail_scheduler_job(
            job_id, error=str(error),
            next_run_at=(now + timedelta(seconds=self.retry_seconds)).isoformat(),
        )
