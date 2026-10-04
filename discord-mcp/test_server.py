import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DISCORD_BOT_TOKEN", "test")
os.environ.setdefault("DISCORD_GUILD_ID", "1")
_TEST_DB = tempfile.NamedTemporaryFile(delete=False)
_TEST_DB.close()
os.environ["DISCORD_DB_PATH"] = _TEST_DB.name

import server
from indexer import MessageIndex


class DiscordServerTests(unittest.TestCase):
    def setUp(self):
        self.old_index = server.index
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        server.index = MessageIndex(self.tmp.name)

    def tearDown(self):
        server.index = self.old_index
        try:
            os.unlink(self.tmp.name)
        except FileNotFoundError:
            pass

    def test_normalize_message_preserves_thread_context(self):
        result = server.normalize_message(
            {
                "id": "3",
                "author": {"id": "7", "username": "tester"},
                "content": "hello",
                "timestamp": "2026-10-04T00:00:00+00:00",
            },
            {"id": "1", "name": "thread-name", "type": 11},
        )
        self.assertEqual(result["channel_name"], "thread-name")
        self.assertEqual(result["thread_id"], "1")

    def test_incomplete_cursor_resumes_from_oldest_message(self):
        channel = {"id": "1", "name": "thread-name", "type": 11}
        server.index.set_cursor(
            "1",
            newest_message_id="6",
            oldest_message_id="5",
            complete=False,
        )
        page = [
            {
                "id": "4",
                "channel_id": "1",
                "channel_name": "thread-name",
                "author_id": "7",
                "author_name": "tester",
                "content": "older one",
                "timestamp": "2026-10-03T00:00:00+00:00",
                "reference_message_id": None,
                "reference_channel_id": None,
                "thread_id": "1",
                "message_type": 0,
                "attachment_count": 0,
                "link_count": 0,
                "url": "https://discord.com/channels/1/1/4",
            },
            {
                "id": "3",
                "channel_id": "1",
                "channel_name": "thread-name",
                "author_id": "7",
                "author_name": "tester",
                "content": "oldest",
                "timestamp": "2026-10-02T00:00:00+00:00",
                "reference_message_id": None,
                "reference_channel_id": None,
                "thread_id": "1",
                "message_type": 0,
                "attachment_count": 0,
                "link_count": 0,
                "url": "https://discord.com/channels/1/1/3",
            },
        ]

        async def fake_page(channel_id, before=None, after=None, limit=100, channel=None):
            if before == "5":
                return page
            return []

        with (
            patch.object(server, "get_message_channels", new=AsyncMock(return_value=[channel])),
            patch.object(server, "fetch_page", side_effect=fake_page) as fetch,
        ):
            result = asyncio.run(
                server.sync_channel_history("1", max_pages=0, incremental=True)
            )

        self.assertEqual(result["messages_processed"], 2)
        self.assertTrue(result["complete"])
        self.assertEqual(server.index.get_cursor("1")["newest_message_id"], "6")
        self.assertEqual(server.index.get_cursor("1")["oldest_message_id"], "3")
        self.assertEqual(fetch.await_args_list[0].kwargs["before"], "5")
        self.assertEqual(fetch.await_args_list[0].kwargs["channel"], channel)

    def test_read_channel_page_passes_channel_metadata(self):
        channel = {"id": "1", "name": "thread-name", "type": 11}
        with (
            patch.object(server, "get_message_channels", new=AsyncMock(return_value=[channel])),
            patch.object(server, "fetch_page", new=AsyncMock(return_value=[])) as fetch,
        ):
            result = asyncio.run(server.read_channel_page("1", before="7"))

        self.assertEqual(result, [])
        self.assertEqual(fetch.await_args.kwargs["channel"], channel)

    def test_invalid_discord_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            server.validate_snowflake("not-an-id", "channel_id")


if __name__ == "__main__":
    unittest.main()
