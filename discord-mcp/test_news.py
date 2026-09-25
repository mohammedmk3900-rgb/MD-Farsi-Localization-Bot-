import tempfile
import unittest
from pathlib import Path

from indexer import MessageIndex
from news import DiscordNewsEngine


class DiscordNewsTests(unittest.TestCase):
    def test_digest_groups_and_highlights_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "discord.db"
            index = MessageIndex(db)
            index.upsert_messages([
                {
                    "id": "1", "channel_id": "10", "channel_name": "ترجمه",
                    "author_id": "a", "author_name": "MK",
                    "content": "اعلام مهم: واژه‌نامه پروژه آپدیت شد",
                    "timestamp": "2026-09-25T10:00:00+00:00",
                    "edited_timestamp": None, "url": "https://discord.com/test/1",
                },
                {
                    "id": "2", "channel_id": "11", "channel_name": "بازبینی",
                    "author_id": "b", "author_name": "Reviewer",
                    "content": "این ترجمه نیاز به بازبینی دارد",
                    "timestamp": "2026-09-25T11:00:00+00:00",
                    "edited_timestamp": None, "url": "https://discord.com/test/2",
                },
            ])
            result = DiscordNewsEngine(db).digest(hours=24, limit=5)
            self.assertEqual(result["message_count"], 2)
            self.assertGreaterEqual(result["category_counts"]["واژه‌نامه"], 1)
            self.assertEqual(result["active_channels"], 2)
            self.assertTrue(result["highlights"])


if __name__ == "__main__":
    unittest.main()
