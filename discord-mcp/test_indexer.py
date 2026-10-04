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

    def test_incremental_cursor_state_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            index = MessageIndex(os.path.join(tmp, "discord.db"))
            index.upsert_messages([{
                "id": "200", "channel_id": "10", "channel_name": "general",
                "author_id": "20", "author_name": "MK",
                "content": "new", "timestamp": "2026-09-25T00:00:00+00:00",
            }])
            index.set_cursor("10", newest_message_id="200", oldest_message_id="200", complete=True)
            cursor = index.get_cursor("10")
            self.assertEqual(cursor["newest_message_id"], "200")
            self.assertTrue(cursor["complete"])

    def test_channel_cursor_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            index = MessageIndex(os.path.join(tmp, "discord.db"))
            index.set_cursor("10", newest_message_id="200", oldest_message_id="100", complete=True)
            cursor = index.get_cursor("10")
            self.assertEqual(cursor["newest_message_id"], "200")
            self.assertEqual(cursor["oldest_message_id"], "100")
            self.assertTrue(cursor["complete"])



    def test_message_relationships_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            index = MessageIndex(os.path.join(tmp, "discord.db"))
            index.upsert_messages([
                {
                    "id": "root", "channel_id": "channel", "channel_name": "translation",
                    "author_id": "1", "author_name": "MK", "content": "Faction -> اتحاد",
                    "timestamp": "2026-09-25T10:00:00+00:00",
                    "url": "https://discord.com/channels/g/channel/root",
                    "attachment_count": 1, "link_count": 1,
                },
                {
                    "id": "reply", "channel_id": "channel", "channel_name": "translation",
                    "author_id": "2", "author_name": "Reviewer", "content": "ثبت شد",
                    "timestamp": "2026-09-25T10:01:00+00:00",
                    "url": "https://discord.com/channels/g/channel/reply",
                    "reference_message_id": "root", "reference_channel_id": "channel",
                },
                {
                    "id": "thread-message", "channel_id": "thread", "channel_name": "discussion",
                    "author_id": "3", "author_name": "Translator", "content": "بررسی شد",
                    "timestamp": "2026-09-25T10:02:00+00:00",
                    "url": "https://discord.com/channels/g/thread/thread-message",
                    "thread_id": "thread",
                },
            ])
            replies = index.read_replies("root")
            self.assertEqual([item["id"] for item in replies], ["reply"])
            self.assertEqual(replies[0]["reference_channel_id"], "channel")
            thread = index.read_thread("thread")
            self.assertEqual([item["id"] for item in thread], ["thread-message"])
            result = index.search("Faction")
            self.assertEqual(result[0]["attachment_count"], 1)
            self.assertEqual(result[0]["link_count"], 1)


if __name__ == "__main__":
    unittest.main()
