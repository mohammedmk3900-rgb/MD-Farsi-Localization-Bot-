import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from intelligence import DiscordIntelligence


class IntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "discord.db"
        db = sqlite3.connect(self.db_path)
        db.execute(
            """
            CREATE TABLE messages (
                id TEXT PRIMARY KEY,
                channel_id TEXT,
                channel_name TEXT,
                author_id TEXT,
                author_name TEXT,
                content TEXT,
                timestamp TEXT,
                edited_timestamp TEXT,
                url TEXT,
                reference_message_id TEXT,
                reference_channel_id TEXT,
                thread_id TEXT,
                message_type INTEGER DEFAULT 0,
                deleted INTEGER DEFAULT 0
            )
            """
        )
        now = datetime.now(timezone.utc)
        rows = [
            ("1", "c1", "ترجمه", "a1", "MK", "ترجمه فایل جدید آماده شد", (now - timedelta(hours=2)).isoformat(), None, "u1", None, None, None),
            ("2", "c1", "ترجمه", "a2", "T", "این مورد باید بررسی شود؟", (now - timedelta(hours=1, minutes=55)).isoformat(), None, "u2", "1", "c1", "thread-1"),
            ("3", "c1", "ترجمه", "a1", "MK", "بازبینی انجام شد", (now - timedelta(hours=1, minutes=50)).isoformat(), None, "u3", "2", "c1", "thread-1"),
            ("4", "c2", "واژه‌نامه", "a3", "A", "واژه‌نامه آپدیت شد", (now - timedelta(hours=1)).isoformat(), None, "u4", None, None, None),
        ]
        db.executemany(
            """
            INSERT INTO messages
            (id,channel_id,channel_name,author_id,author_name,content,timestamp,
             edited_timestamp,url,reference_message_id,reference_channel_id,thread_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        db.commit()
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_builds_event_and_relationship_metrics(self):
        result = DiscordIntelligence(self.db_path).build(hours=24, limit=10)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["current"]["messages"], 4)
        self.assertEqual(result["current"]["replies"], 2)
        self.assertEqual(result["current"]["thread_messages"], 2)
        self.assertIn("واژه‌نامه", result["current"]["category_counts"])
        self.assertGreaterEqual(len(result["events"]), 2)

    def test_unresolved_followup_is_detected(self):
        db = sqlite3.connect(self.db_path)
        now = datetime.now(timezone.utc)
        db.execute(
            """
            INSERT INTO messages
            (id,channel_id,channel_name,author_id,author_name,content,timestamp,url)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            ("5", "c3", "پروژه", "a4", "B", "لطفاً این خطا را بررسی کنید؟", now.isoformat(), "u5"),
        )
        db.commit()
        db.close()
        result = DiscordIntelligence(self.db_path).build(hours=24, limit=20)
        self.assertGreaterEqual(result["health"]["unresolved_followups"], 1)
        self.assertEqual(result["health"]["status"], "attention")


if __name__ == "__main__":
    unittest.main()
