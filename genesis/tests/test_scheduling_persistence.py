from pathlib import Path

from app.persistence.store import Store
from app.services.application import GenesisApplication


def build(tmp_path: Path):
    app = GenesisApplication(Store(tmp_path / "genesis.db"))
    app.initialize()
    return app


def test_reminder_is_delivered_once(tmp_path):
    app = build(tmp_path)
    app.reminders.schedule("member-1", 7, "2026-09-25T10:00:00+00:00", "deadline")
    first = app.reminders.due("2026-09-25T11:00:00+00:00")
    second = app.reminders.due("2026-09-25T12:00:00+00:00")
    assert len(first) == 1
    assert second == []


def test_mission_is_delivered_once(tmp_path):
    app = build(tmp_path)
    app.mission_scheduler.schedule(42, "2026-09-25T10:00:00+00:00", "mission due")
    first = app.mission_scheduler.due("2026-09-25T11:00:00+00:00")
    second = app.mission_scheduler.due("2026-09-25T12:00:00+00:00")
    assert [x.mission_id for x in first] == [42]
    assert second == []
