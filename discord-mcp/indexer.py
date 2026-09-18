"""SQLite index for authorized Discord message history."""
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
            db.execute("PRAGMA synchronous=NORMAL")
            db.execute("""CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, channel_name TEXT,
                author_id TEXT, author_name TEXT, content TEXT NOT NULL,
                timestamp TEXT, edited_timestamp TEXT, url TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp ON messages(channel_id, timestamp)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content)")
            db.execute("""CREATE TABLE IF NOT EXISTS channel_cursors (
                channel_id TEXT PRIMARY KEY, newest_message_id TEXT, oldest_message_id TEXT,
                complete INTEGER NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    def upsert_messages(self, messages: list[dict[str, Any]]) -> int:
        if not messages:
            return 0
        with self._connect() as db:
            db.executemany("""INSERT INTO messages
                (id, channel_id, channel_name, author_id, author_name, content,
                 timestamp, edited_timestamp, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET channel_name=excluded.channel_name,
                author_name=excluded.author_name, content=excluded.content,
                edited_timestamp=excluded.edited_timestamp, url=excluded.url""", [
                (m["id"], m["channel_id"], m.get("channel_name"), m.get("author_id"),
                 m.get("author_name"), m.get("content", ""), m.get("timestamp"),
                 m.get("edited_timestamp"), m.get("url")) for m in messages])
        return len(messages)

    def set_cursor(self, channel_id: str, newest_message_id: str | None = None,
                   oldest_message_id: str | None = None, complete: bool = False) -> None:
        with self._connect() as db:
            db.execute("""INSERT INTO channel_cursors
                (channel_id, newest_message_id, oldest_message_id, complete)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                newest_message_id=COALESCE(excluded.newest_message_id, newest_message_id),
                oldest_message_id=COALESCE(excluded.oldest_message_id, oldest_message_id),
                complete=excluded.complete, updated_at=CURRENT_TIMESTAMP""",
                (channel_id, newest_message_id, oldest_message_id, int(complete)))

    def count(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM messages").fetchone()[0])

    def channel_count(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(DISTINCT channel_id) FROM messages").fetchone()[0])

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        pattern = f"%{query.strip()}%"
        with self._connect() as db:
            rows = db.execute("""SELECT id, channel_id, channel_name, author_id,
                author_name, content, timestamp, edited_timestamp, url FROM messages
                WHERE content LIKE ? COLLATE NOCASE ORDER BY timestamp DESC LIMIT ?""",
                (pattern, max(1, min(limit, 100)))).fetchall()
        return [dict(row) for row in rows]

    def read_channel(self, channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("""SELECT id, channel_id, channel_name, author_id,
                author_name, content, timestamp, edited_timestamp, url FROM messages
                WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?""",
                (channel_id, max(1, min(limit, 100)))).fetchall()
        return [dict(row) for row in rows]


async def sync_channel(fetch_page: Callable[..., Awaitable[list[dict[str, Any]]]],
                       index: MessageIndex, channel_id: str,
                       *, oldest_id: str | None = None) -> int:
    before = oldest_id
    total = 0
    while True:
        page = await fetch_page(channel_id, before)
        if not page:
            break
        total += index.upsert_messages(page)
        before = page[-1]["id"]
        if len(page) < 100:
            break
    return total
