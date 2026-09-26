from __future__ import annotations

import tempfile
import unittest

from app.persistence.database import Database
from app.services.manager import ProjectManagerService


class ManagerReadModelTests(unittest.TestCase):
    def test_build_reports_review_gap_and_velocity(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(temp + "/db.sqlite")
            db.initialize()
            db.save_snapshot("2026-09-26T10:00:00+00:00", 1, {"project": {
                "project_id": 19621, "translated": 120, "reviewed": 20,
                "strings_total": 1000, "translation_percent": 12.0, "review_percent": 2.0
            }})
            db.save_snapshot("2026-09-26T11:00:00+00:00", 1, {"project": {
                "project_id": 19621, "translated": 140, "reviewed": 30,
                "strings_total": 1000, "translation_percent": 14.0, "review_percent": 3.0
            }})
            result = ProjectManagerService(db).build()
            self.assertEqual(result["progress"]["review_gap"], 110)
            self.assertEqual(result["delta"]["translated"], 20)
            self.assertEqual(result["delta"]["reviewed"], 10)
            self.assertEqual(result["velocity"]["average_translation_per_snapshot"], 20.0)
            self.assertEqual(result["status"], "attention")


if __name__ == "__main__":
    unittest.main()
