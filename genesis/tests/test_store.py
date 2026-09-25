from pathlib import Path

from app.persistence.store import Store


def test_store_initializes_and_records_events(tmp_path: Path):
    store = Store(tmp_path / "genesis.db")
    store.initialize()
    store.record_event("test", "42", "2026-09-25T00:00:00+00:00", {"ok": True})
    events = store.events()
    assert events[0]["event_type"] == "test"
    assert events[0]["payload"] == {"ok": True}
