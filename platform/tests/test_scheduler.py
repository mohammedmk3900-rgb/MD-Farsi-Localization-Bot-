import tempfile
from pathlib import Path
from types import SimpleNamespace

from app.persistence.database import Database
from app.services.scheduler import ScheduledJob, Scheduler


def make_scheduler(monkeypatch):
    temp = tempfile.TemporaryDirectory()
    database = Database(Path(temp.name) / "platform.db")
    database.initialize()
    application = SimpleNamespace(
        context=SimpleNamespace(database=database),
        record=lambda *_: None,
    )
    monkeypatch.setattr("app.services.scheduler.application", application)
    return temp, database, Scheduler(poll_seconds=1, lease_seconds=60)


def test_scheduler_runs_new_job_once(monkeypatch):
    temp, database, scheduler = make_scheduler(monkeypatch)
    calls = []
    job = ScheduledJob("test", 3600, lambda: calls.append("run"), "test")

    assert scheduler.run_job(job)["status"] == "success"
    assert scheduler.run_job(job)["status"] == "not_due"
    assert calls == ["run"]
    row = database.connect().execute(
        "SELECT status, run_count, failure_count FROM scheduler_jobs WHERE name='test'"
    ).fetchone()
    assert tuple(row) == ("success", 1, 0)
    temp.cleanup()


def test_scheduler_failure_is_retriable(monkeypatch):
    temp, database, scheduler = make_scheduler(monkeypatch)

    def fail():
        raise RuntimeError("offline")

    job = ScheduledJob("test", 3600, fail, "test", retry_seconds=1)
    result = scheduler.run_job(job)

    assert result["status"] == "failed"
    row = database.connect().execute(
        "SELECT status, failure_count, last_error_type FROM scheduler_jobs WHERE name='test'"
    ).fetchone()
    assert tuple(row) == ("failed", 1, "RuntimeError")
    temp.cleanup()
