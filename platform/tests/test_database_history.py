import tempfile
import unittest

from app.persistence.database import Database


class DatabaseHistoryTests(unittest.TestCase):
    def test_snapshot_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/platform.db")
            db.initialize()
            db.save_snapshot("2026-09-22T00:00:00+00:00", 1, {"project": {"translated": 42}})
            rows = db.recent_snapshots()
            self.assertEqual(rows[0]["payload"]["project"]["translated"], 42)

    def test_event_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/platform.db")
            db.initialize()
            db.append_event("test.event", "2026-09-22T00:00:00+00:00", {"ok": True})
            rows = db.recent_events()
            self.assertEqual(rows[0]["event_type"], "test.event")
            self.assertTrue(rows[0]["payload"]["ok"])


if __name__ == "__main__":
    unittest.main()
