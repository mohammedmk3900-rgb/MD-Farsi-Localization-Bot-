import unittest
from unittest.mock import patch

from app.application import application
import json
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

    def test_discord_intelligence_artifact_is_valid_json(self):
        import sqlite3
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from app.services.jobs import build_discord_intelligence

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "discord.db"
            output_path = Path(tmp) / "intelligence.json"
            with sqlite3.connect(db_path) as db:
                db.execute("""
                    CREATE TABLE messages (
                        id TEXT PRIMARY KEY, channel_id TEXT, channel_name TEXT,
                        author_id TEXT, author_name TEXT, content TEXT, timestamp TEXT,
                        edited_timestamp TEXT, url TEXT, reference_message_id TEXT,
                        reference_channel_id TEXT, thread_id TEXT, message_type INTEGER DEFAULT 0,
                        deleted INTEGER DEFAULT 0
                    )
                """)
            with patch.object(application.context.settings, "discord_database_path", str(db_path)):
                with patch.object(application.context.settings, "discord_intelligence_path", str(output_path)):
                    with patch("app.services.jobs.application.record"):
                        result = build_discord_intelligence()
            self.assertEqual(result["status"], "success")
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
