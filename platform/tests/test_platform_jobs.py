import unittest
from unittest.mock import patch

from app.services.jobs import report
from app.services.reports import ReportService


class PlatformJobTests(unittest.TestCase):
    def test_report_reads_persisted_snapshot(self):
        snapshot = {
            "project": {
                "translated": 25,
                "reviewed": 10,
                "strings_total": 100,
                "translation_percent": 25.0,
                "review_percent": 10.0,
            }
        }
        with patch("app.services.jobs.application.context.database.recent_snapshots", return_value=[{"payload": snapshot}]):
            with patch("app.services.jobs.application.context.settings.channel_reports", ""):
                result = report("daily")
        self.assertEqual(result["period"], "daily")
        self.assertEqual(result["project"]["translated"], 25)

    def test_report_service_is_deterministic_about_snapshot_shape(self):
        result = ReportService().build({"project": {"translated": 7}}, "weekly")
        self.assertEqual(result["period"], "weekly")
        self.assertEqual(result["project"]["translated"], 7)


if __name__ == "__main__":
    unittest.main()
