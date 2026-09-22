import tempfile
import unittest
from unittest.mock import patch

from app.config import Settings
from app.persistence.database import Database
from app.services.events import EventBus
from app.services.project import ProjectService


class ProjectPersistenceTests(unittest.TestCase):
    def test_sync_persists_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(f"{directory}/platform.db")
            db.initialize()
            settings = Settings(paratranz_token="test-token")
            service = ProjectService(settings, EventBus(), db)

            fake = {
                "project_id": 19621,
                "captured_at": "2026-09-22T00:00:00+00:00",
                "words_total": 100,
                "strings_total": 50,
                "translated": 10,
                "reviewed": 5,
                "files": 2,
                "members": 3,
                "translation_percent": 20.0,
                "review_percent": 10.0,
            }

            with patch("app.services.project.ParaTranzClient.project_snapshot") as call:
                from app.domain.models import ProjectSnapshot
                call.return_value = ProjectSnapshot(**fake)
                service.sync()

            rows = db.recent_snapshots(1)
            self.assertEqual(rows[0]["payload"]["project"]["translated"], 10)
            self.assertEqual(rows[0]["payload"]["project"]["translation_percent"], 20.0)


if __name__ == "__main__":
    unittest.main()
