from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_type_created
                ON events(event_type, created_at);

            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_captured
                ON snapshots(captured_at);
            """)

    def append_event(self, event_type: str, created_at: str, payload: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(event_type, created_at, payload) VALUES (?, ?, ?)",
                (event_type, created_at, json.dumps(payload, ensure_ascii=False)),
            )

    def save_snapshot(self, captured_at: str, schema_version: int, payload: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO snapshots(captured_at, schema_version, payload) VALUES (?, ?, ?)",
                (captured_at, schema_version, json.dumps(payload, ensure_ascii=False)),
            )

    def recent_snapshots(self, limit: int = 30) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self.connect() as db:
            rows = db.execute(
                "SELECT captured_at, schema_version, payload FROM snapshots "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "captured_at": row["captured_at"],
                "schema_version": row["schema_version"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, event_type, created_at, payload FROM events "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]
