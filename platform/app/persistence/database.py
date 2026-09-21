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
            """)

    def append_event(self, event_type: str, created_at: str, payload: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(event_type, created_at, payload) VALUES (?, ?, ?)",
                (event_type, created_at, json.dumps(payload, ensure_ascii=False)),
            )
