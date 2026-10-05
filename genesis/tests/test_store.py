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


def test_scheduler_failure_is_recorded(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.scheduling import Scheduler

    scheduler = Scheduler(store, retry_seconds=7)
    scheduler.register("paratranz-sync")
    assert scheduler.claim("paratranz-sync")
    scheduler.fail("paratranz-sync", "temporary upstream failure")
    job = store.scheduler_job("paratranz-sync")
    assert job["status"] == "pending"
    assert job["failure_count"] == 1
    assert job["last_error"] == "temporary upstream failure"


def test_alerts_are_persistent(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.alerts import AlertService

    alerts = AlertService(store)
    alerts.service_failure("sync", "upstream unavailable", "SYNC_DOWN")
    assert alerts.active()[0]["code"] == "SYNC_DOWN"


def test_review_payload_survives_restart(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.review import ReviewQueue
    from app.domain.models import TranslationCheck

    check = TranslationCheck("KEY $X$", "ترجمه $X$", [{"kind": "demo", "severity": "warning"}])
    item = ReviewQueue(store).submit("translator-1", check)

    restored = ReviewQueue(Store(tmp_path / "genesis.db")).pending()[0]
    assert restored.id == item.id
    assert restored.check.source == "KEY $X$"
    assert restored.check.translation == "ترجمه $X$"
    assert restored.check.findings[0]["kind"] == "demo"


def test_progress_and_achievement_state_is_durable(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.progress import ProgressService
    from app.services.achievements import AchievementService

    progress = ProgressService(store).member("m1", completed=10, review=2, active=1)
    assert progress.total == 13
    restored = ProgressService(Store(tmp_path / "genesis.db")).member("m1")
    assert restored.completed == 10
    achievements = AchievementService(store).earned(10, member_id="m1")
    assert {a.key for a in achievements} == {"first_task", "ten_tasks"}
    assert len(AchievementService(Store(tmp_path / "genesis.db")).persisted("m1")) == 2


def test_translation_qa_history_is_durable(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.translation import TranslationService

    TranslationService().check_and_record(store, "KEY", "Hello $X$", "سلام $X$")
    history = TranslationService().history(store, "KEY")
    assert len(history) == 1
    assert history[0]["translation_key"] == "KEY"


def test_task_stale_transition_is_rejected(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.tasks import TaskService
    from app.domain.models import Priority

    service = TaskService(store)
    task = service.create(title="Race", priority=Priority.NORMAL)
    first = service.get(task.id)
    second = service.get(task.id)
    service.claim(first, "member-a")
    try:
        service.claim(second, "member-b")
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale task claim was accepted")


def test_review_stale_claim_is_rejected(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.review import ReviewQueue
    from app.domain.models import TranslationCheck

    queue = ReviewQueue(store)
    item = queue.submit("translator", TranslationCheck("KEY", "ترجمه"))
    queue.claim(item.id, "reviewer-a")
    try:
        queue.claim(item.id, "reviewer-b")
    except ValueError as exc:
        assert "open" in str(exc)
    else:
        raise AssertionError("stale review claim was accepted")


def test_task_state_machine_rejects_terminal_transition(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.tasks import TaskService
    from app.domain.models import Priority, TaskStatus

    service = TaskService(store)
    task = service.create(title="State machine", priority=Priority.NORMAL)
    store.update_task(task.id, status=TaskStatus.DONE.value, updated_at="2026-10-05T00:00:00+00:00")
    done = service.get(task.id)
    try:
        service.claim(done, "member-a")
    except ValueError as exc:
        assert "invalid task transition" in str(exc)
    else:
        raise AssertionError("DONE task was allowed to transition")


def test_review_state_machine_rejects_terminal_reopen(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.services.review import ReviewQueue, ReviewDecision
    from app.domain.models import TranslationCheck

    queue = ReviewQueue(store)
    item = queue.submit("translator", TranslationCheck("KEY", "ترجمه"))
    queue.claim(item.id, "reviewer")
    queue.decide(item.id, ReviewDecision.APPROVE, "reviewer")
    try:
        queue.claim(item.id, "reviewer-2")
    except ValueError as exc:
        assert "invalid review transition" in str(exc)
    else:
        raise AssertionError("APPROVED review was allowed to reopen")


def test_atomic_task_transition_rejects_stale_status(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    from app.domain.models import Priority

    task_id = store.create_task(title="atomic", scope="", priority=Priority.NORMAL.value,
                                due_at=None, created_at="2026-10-05T00:00:00+00:00")
    store.transition_task(task_id, target_status="in_progress",
                          updated_at="2026-10-05T00:01:00+00:00",
                          allowed_from=("available",), owner="member-a")
    try:
        store.transition_task(task_id, target_status="review",
                              updated_at="2026-10-05T00:02:00+00:00",
                              allowed_from=("available",), owner="member-b")
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale atomic task transition was accepted")


def test_atomic_review_transition_rejects_stale_status(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    review_id = store.create_review(
        translation_key="KEY", actor="translator", status="open",
        created_at="2026-10-05T00:00:00+00:00"
    )
    store.transition_review(review_id, target_status="in_review",
                            updated_at="2026-10-05T00:01:00+00:00",
                            allowed_from=("open",), reviewer="reviewer-a")
    try:
        store.transition_review(review_id, target_status="approved",
                                updated_at="2026-10-05T00:02:00+00:00",
                                allowed_from=("open",), reviewer="reviewer-b")
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale atomic review transition was accepted")
