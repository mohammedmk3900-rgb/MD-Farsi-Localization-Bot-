import unittest
from unittest.mock import patch

from app.services.commands import CommandService


class CommandReadOnlyTests(unittest.TestCase):
    def test_stats_does_not_trigger_live_sync(self):
        service = CommandService()
        with patch.object(service, "_latest_project", return_value={}):
            with patch("app.services.commands.sync_project", side_effect=AssertionError("stats must not sync")):
                result = service.stats()
        self.assertFalse(result["synced"])

    def test_progress_does_not_trigger_live_sync(self):
        service = CommandService()
        with patch.object(service, "_latest_project", return_value={}):
            with patch("app.services.commands.sync_project", side_effect=AssertionError("progress must not sync")):
                result = service.progress()
        self.assertFalse(result["synced"])

    def test_report_without_snapshot_is_read_only(self):
        service = CommandService()
        with patch.object(service, "_latest_project", return_value={}):
            with patch("app.services.commands.sync_project", side_effect=AssertionError("report must not sync")):
                result = service.report()
        self.assertEqual(result["status"], "no_snapshot")


if __name__ == "__main__":
    unittest.main()
