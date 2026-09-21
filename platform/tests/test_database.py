from app.persistence.database import Database

def test_database_initializes(tmp_path):
    db = Database(str(tmp_path / "platform.db"))
    db.initialize()
    db.append_event("test", "2026-09-21T00:00:00Z", {"ok": True})
    with db.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
