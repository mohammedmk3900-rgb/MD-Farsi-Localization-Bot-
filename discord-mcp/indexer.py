"""Incremental Discord message index for the MCP bridge.

The index is intentionally simple: SQLite stores message metadata/content and
per-channel cursors. A deployment can run sync_channels() periodically.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Awaitable, Callable

DB_PATH = Path(__file__).with_name("discord.db")


class MessageIndex:
    def __init__(self, path: str | Path = DB_PATH) -> None:
        self.path = str(path)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def _init(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    channel_name TEXT,
                    author_id TEXT,
                    author_name TEXT,
                    content TEXT NOT NULL,
                    timestamp TEXT,
                    edited_timestamp TEXT,
                    url TEXT
                )
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp
                ON messages(channel_id, timestamp)
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_content
                ON messages(content)
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_cursors (
                    channel_id TEXT PRIMARY KEY,
                    newest_message_id TEXT
                )
                """
            )

    def upsert_messages(self, messages: list[dict[str, Any]]) -> int:
        if not messages:
            return 0
        with self._connect() as db:
            db.executemany(
                """
                INSERT INTO messages
                (id, channel_id, channel_name, author_id, author_name, content,
                 timestamp, edited_timestamp, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  channel_name=excluded.channel_name,
                  author_name=excluded.author_name,
                  content=excluded.content,
                  edited_timestamp=excluded.edited_timestamp,
                  url=excluded.url
                """,
                [
                    (
                        m["id"],
                        m["channel_id"],
                        m.get("channel_name"),
                        m.get("author_id"),
                        m.get("author_name"),
                        m.get("content", ""),
                        m.get("timestamp"),
                        m.get("edited_timestamp"),
                        m.get("url"),
                    )
                    for m in messages
                ],
            )
            return len(messages)

    def set_cursor(self, channel_id: str, newest_message_id: str) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO channel_cursors(channel_id, newest_message_id)
                VALUES (?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                  newest_message_id=excluded.newest_message_id
                """,
                (channel_id, newest_message_id),
            )

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        # SQLite FTS is deliberately avoided here so this stays dependency-free.
        pattern = f"%{query}%"
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT id, channel_id, channel_name, author_id, author_name,
                       content, timestamp, edited_timestamp, url
                FROM messages
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (pattern, max(1, min(limit, 100))),
            ).fetchall()
        return [dict(row) for row in rows]


async def sync_channel(
    fetch_page: Callable[..., Awaitable[list[dict[str, Any]]]],
    index: MessageIndex,
    channel_id: str,
    *,
    oldest_id: str | None = None,
) -> int:
    """Fetch pages from newest to oldest until the requested boundary.

    fetch_page(channel_id, before_id) must return messages in Discord's normal
    newest-first order. The callback is kept abstract so the indexer is easy
    to test without Discord credentials.
    """
    before = oldest_id
    total = 0

    while True:
        page = await fetch_page(channel_id, before)
        if not page:
            break

        total += index.upsert_messages(page)
        oldest = page[-1]["id"]
        before = oldest

        # A short page means the channel has been exhausted.
        if len(page) < 100:
            break

    return total
