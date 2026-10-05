from pathlib import Path

from app.persistence.store import Store


def test_store_initializes_and_records_events(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    store.record_event("test", "42", "2026-09-25T00:00:00+00:00", {"ok": True})
    events = store.events()
    assert events[0]["event_type"] == "test"
    assert events[0]["payload"] == {"ok": True}


def test_task_state_survives_service_restart(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.tasks import TaskService
    from app.domain.models import Priority, TaskStatus

    first = TaskService(store)
    task = first.create(title="Review focus", priority=Priority.HIGH)
    first.claim(task, "member-1")

    second = TaskService(store)
    restored = second.get(task.id)
    assert restored.owner == "member-1"
    assert restored.status == TaskStatus.IN_PROGRESS


def test_scheduler_lease_prevents_double_claim(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.scheduling import Scheduler
    from datetime import datetime, timezone

    scheduler = Scheduler(store)
    scheduler.register("sync")
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    assert scheduler.claim("sync", now)
    assert not scheduler.claim("sync", now)
    scheduler.succeed("sync")
    assert scheduler.claim("sync", now)


def test_review_state_is_durable(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.review import ReviewQueue, ReviewDecision, ReviewStatus
    from app.domain.models import TranslationCheck

    queue = ReviewQueue(store)
    item = queue.submit("translator-1", TranslationCheck("KEY", "ترجمه"))
    claimed = queue.claim(item.id, "reviewer-1")
    assert claimed.status == ReviewStatus.IN_REVIEW
    result = queue.decide(item.id, ReviewDecision.APPROVE, "reviewer-1")
    assert result["status"] == ReviewStatus.APPROVED
    assert queue.pending() == []
    assert store.reviews()[0]["reviewer"] == "reviewer-1"
