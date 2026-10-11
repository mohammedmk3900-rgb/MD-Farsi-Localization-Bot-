from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
_TEST_ROOT = tempfile.TemporaryDirectory(prefix="md-discord-server-tests-")
os.environ["DISCORD_BOT_TOKEN"] = "test-token"
os.environ["DISCORD_GUILD_ID"] = "1"
os.environ["DISCORD_DB_PATH"] = str(Path(_TEST_ROOT.name) / "server.db")

import server
from indexer import MessageIndex


def _message(message_id: int, channel_id: str = "10") -> dict:
    return {
        "id": str(message_id),
        "channel_id": channel_id,
        "channel_name": "general",
        "author_id": "20",
        "author_name": "MK",
        "content": f"message {message_id}",
        "timestamp": f"2026-10-11T10:{message_id % 60:02d}:00+00:00",
    }


def test_partial_backfill_keeps_newest_id_from_first_page(tmp_path, monkeypatch):
    index = MessageIndex(tmp_path / "discord.db")
    monkeypatch.setattr(server, "index", index)
    monkeypatch.setattr(
        server,
        "get_message_channels",
        lambda: _async_value([{"id": "10", "name": "general", "type": 0}]),
    )
    pages = [
        [_message(i) for i in range(200, 100, -1)],
        [_message(i) for i in range(100, 0, -1)],
    ]

    async def fake_fetch_page(channel_id, before=None, after=None, limit=100, channel=None):
        return pages[0] if before is None else pages[1]

    monkeypatch.setattr(server, "fetch_page", fake_fetch_page)
    result = asyncio.run(server.sync_channel_history("10", max_pages=2, incremental=True))

    cursor = index.get_cursor("10")
    assert result["complete"] is False
    assert cursor["newest_message_id"] == "200"
    assert cursor["oldest_message_id"] == "1"


def test_completed_incremental_sync_advances_newest_cursor(tmp_path, monkeypatch):
    index = MessageIndex(tmp_path / "discord.db")
    index.set_cursor("10", newest_message_id="100", oldest_message_id="1", complete=True)
    monkeypatch.setattr(server, "index", index)
    monkeypatch.setattr(
        server,
        "get_message_channels",
        lambda: _async_value([{"id": "10", "name": "general", "type": 0}]),
    )

    async def fake_fetch_page(channel_id, before=None, after=None, limit=100, channel=None):
        return [_message(i) for i in range(120, 20, -1)]

    monkeypatch.setattr(server, "fetch_page", fake_fetch_page)
    result = asyncio.run(server.sync_channel_history("10", incremental=True))

    cursor = index.get_cursor("10")
    assert result["reached_cursor"] is True
    assert cursor["newest_message_id"] == "120"
    assert cursor["complete"] is True


async def _async_value(value):
    return value


def test_optional_resource_reports_permission_denied(monkeypatch):
    import httpx

    response = httpx.Response(403, request=httpx.Request("GET", "https://discord.com/api/v10/test"))

    async def forbidden(path):
        raise httpx.HTTPStatusError("forbidden", request=response.request, response=response)

    monkeypatch.setattr(server, "discord_get", forbidden)
    items, status = asyncio.run(server.get_optional_guild_resource_with_status("/test", "items"))

    assert items == []
    assert status == {"status": "permission_denied", "http_status": 403}


def test_optional_empty_resource_is_not_marked_as_failed(monkeypatch):
    async def empty(path):
        return {"items": []}

    monkeypatch.setattr(server, "discord_get", empty)
    items, status = asyncio.run(server.get_optional_guild_resource_with_status("/test", "items"))

    assert items == []
    assert status == {"status": "available", "count": 0}
