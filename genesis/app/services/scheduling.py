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


class ScheduledSyncRunner:
    """Runs one durable ParaTranz sync job; safe to call from a periodic process."""

    JOB_ID = "paratranz-sync"

    def __init__(self, application, integration=None):
        from app.integrations.paratranz import ParaTranzIntegration
        self.application = application
        self.integration = integration or ParaTranzIntegration()

    def register(self, first_run_at: str | None = None) -> None:
        self.application.scheduler.register(self.JOB_ID, first_run_at)

    def run_once(self, now: datetime | None = None) -> dict | None:
        """Return None when not due/already leased; otherwise return a durable result."""
        now = now or datetime.now(timezone.utc)
        if not self.application.scheduler.claim(self.JOB_ID, now):
            return None
        try:
            result = self.application.sync.project(self.application, self.integration)
            self.application.scheduler.succeed(self.JOB_ID)
            self.application.audit("scheduler.job.succeeded", None, {"job_id": self.JOB_ID, "run_id": result["run_id"]})
            return result
        except Exception as exc:
            self.application.scheduler.fail(self.JOB_ID, exc)
            try:
                self.application.audit("scheduler.job.failed", None, {
                    "job_id": self.JOB_ID, "error_type": type(exc).__name__, "error": str(exc)
                })
            except Exception:
                pass
            raise
