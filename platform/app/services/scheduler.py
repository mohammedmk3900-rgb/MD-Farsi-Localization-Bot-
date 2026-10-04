from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.application import application
from app.services import jobs

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduledJob:
    name: str
    interval_seconds: int
    handler: Callable[[], object]
    description: str
    retry_seconds: int = 300


class Scheduler:
    """Persistent autonomous scheduler with SQLite-backed execution leases."""

    def __init__(self, poll_seconds: int = 30, lease_seconds: int = 900):
        self.database = application.context.database
        self.poll_seconds = max(1, int(poll_seconds))
        self.lease_seconds = max(30, int(lease_seconds))
        self.jobs: list[ScheduledJob] = []
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.database.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS scheduler_jobs (
                    name TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'idle',
                    lock_until TEXT,
                    last_run_at TEXT,
                    next_run_at TEXT,
                    last_error_type TEXT,
                    run_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_scheduler_next_run
                    ON scheduler_jobs(next_run_at, status);
                """
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def register(self, name: str, interval_seconds: int, handler: Callable[[], object], description: str = "", retry_seconds: int = 300) -> None:
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be positive")
        if any(job.name == name for job in self.jobs):
            raise ValueError(f"duplicate scheduler job: {name}")
        self.jobs.append(ScheduledJob(name, interval_seconds, handler, description, max(1, retry_seconds)))

    def _claim(self, name: str, now: datetime) -> bool:
        now_text = now.isoformat()
        lease_text = (now + timedelta(seconds=self.lease_seconds)).isoformat()
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT lock_until FROM scheduler_jobs WHERE name=?", (name,)).fetchone()
            if row and row["lock_until"] and str(row["lock_until"]) > now_text:
                db.rollback()
                return False
            db.execute(
                """
                INSERT INTO scheduler_jobs(name,status,lock_until,updated_at)
                VALUES (?, 'running', ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    status='running', lock_until=excluded.lock_until, updated_at=excluded.updated_at
                """,
                (name, lease_text, now_text),
            )
            db.commit()
        return True

    def _due(self, job: ScheduledJob, now: datetime) -> bool:
        with self.database.connect() as db:
            row = db.execute(
                "SELECT next_run_at, lock_until FROM scheduler_jobs WHERE name=?",
                (job.name,),
            ).fetchone()
        if not row:
            return True
        if row["lock_until"] and str(row["lock_until"]) > now.isoformat():
            return False
        if not row["next_run_at"]:
            return True
        try:
            return datetime.fromisoformat(str(row["next_run_at"])) <= now
        except ValueError:
            return True

    def _finish(self, job: ScheduledJob, status: str, error_type: str | None = None) -> None:
        now = self._now()
        next_run = now + timedelta(seconds=job.retry_seconds if status == "failed" else job.interval_seconds)
        with self.database.connect() as db:
            db.execute(
                """
                UPDATE scheduler_jobs
                SET status=?, lock_until=NULL, last_run_at=?, next_run_at=?,
                    last_error_type=?, run_count=run_count+1,
                    failure_count=failure_count+CASE WHEN ?='failed' THEN 1 ELSE 0 END,
                    updated_at=?
                WHERE name=?
                """,
                (status, now.isoformat(), next_run.isoformat(), error_type, status, now.isoformat(), job.name),
            )

    def run_job(self, job: ScheduledJob) -> dict[str, object]:
        now = self._now()
        if not self._due(job, now):
            return {"job": job.name, "status": "not_due"}
        if not self._claim(job.name, now):
            return {"job": job.name, "status": "locked"}

        try:
            job.handler()
        except Exception as exc:
            self._finish(job, "failed", type(exc).__name__)
            application.record("scheduler.job_failed", {"job": job.name, "error_type": type(exc).__name__})
            LOGGER.exception("scheduler job failed: %s", job.name)
            return {"job": job.name, "status": "failed", "error_type": type(exc).__name__}

        self._finish(job, "success")
        application.record("scheduler.job_completed", {"job": job.name})
        return {"job": job.name, "status": "success"}

    def run_once(self) -> list[dict[str, object]]:
        return [self.run_job(job) for job in self.jobs]

    def run_forever(self) -> None:
        LOGGER.info("MD Farsi autonomous scheduler started with %d jobs", len(self.jobs))
        while True:
            self.run_once()
            time.sleep(self.poll_seconds)


def build_scheduler(poll_seconds: int = 30, lease_seconds: int = 900) -> Scheduler:
    scheduler = Scheduler(poll_seconds, lease_seconds)
    scheduler.register("sync", 6 * 60 * 60, jobs.sync, "Project/ParaTranz synchronization")
    scheduler.register("glossary", 6 * 60 * 60, jobs.glossary_sync, "Glossary synchronization and publication")
    scheduler.register("discord_audit", 12 * 60 * 60, jobs.audit, "Discord structure audit")
    scheduler.register("health", 30 * 60, jobs.health, "Platform health check")
    scheduler.register("manager", 60 * 60, jobs.manager, "Manager read model")
    scheduler.register("daily_report", 24 * 60 * 60, lambda: jobs.report("daily"), "Daily report")
    scheduler.register("weekly_report", 7 * 24 * 60 * 60, lambda: jobs.report("weekly"), "Weekly report")
    return scheduler
