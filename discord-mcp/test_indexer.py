"""Focused regression tests for the Discord MCP bridge."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from indexer import MessageIndex


class DiscordMCPIndexTests(unittest.TestCase):
    def test_deleted_messages_are_excluded_from_search_and_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            index = MessageIndex(os.path.join(tmp, "discord.db"))
            index.upsert_messages([{
                "id": "1", "channel_id": "10", "channel_name": "general",
                "author_id": "20", "author_name": "MK",
                "content": "Millennium Dawn",
                "timestamp": "2026-09-21T00:00:00+00:00",
            }])
            self.assertEqual(index.count(), 1)
            index.mark_deleted("1")
            self.assertEqual(index.count(), 0)
            self.assertEqual(index.search("Millennium"), [])

    def test_channel_cursor_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            index = MessageIndex(os.path.join(tmp, "discord.db"))
            index.set_cursor("10", newest_message_id="200", oldest_message_id="100", complete=True)
            cursor = index.get_cursor("10")
            self.assertEqual(cursor["newest_message_id"], "200")
            self.assertEqual(cursor["oldest_message_id"], "100")
            self.assertTrue(cursor["complete"])


if __name__ == "__main__":
    unittest.main()
