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

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT '',
                owner TEXT,
                reviewer TEXT,
                priority TEXT NOT NULL DEFAULT 'normal',
                status TEXT NOT NULL DEFAULT 'available',
                due_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status_owner
                ON tasks(status, owner);
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
            {"captured_at": row["captured_at"], "schema_version": row["schema_version"], "payload": json.loads(row["payload"])}
            for row in rows
        ]

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, event_type, created_at, payload FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": row["id"], "event_type": row["event_type"], "created_at": row["created_at"], "payload": json.loads(row["payload"])}
            for row in rows
        ]

    def create_task(
        self,
        title: str,
        owner: str | None,
        scope: str,
        priority: str,
        due_at: str | None,
        created_at: str,
    ) -> dict[str, Any]:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO tasks(title, scope, owner, priority, status, due_at, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'available', ?, ?, ?)",
                (title, scope, owner, priority, due_at, created_at, created_at),
            )
            task_id = int(cursor.lastrowid)
        return self.get_task(task_id) or {}

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self, status: str | None = None, owner: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks"
        conditions: list[str] = []
        values: list[str] = []
        if status is not None:
            conditions.append("status = ?")
            values.append(status)
        if owner is not None:
            conditions.append("owner = ?")
            values.append(owner)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, id DESC"
        with self.connect() as db:
            return [dict(row) for row in db.execute(query, values).fetchall()]

    def update_task(self, task_id: int, **changes: Any) -> dict[str, Any]:
        allowed = {"owner", "reviewer", "priority", "status", "due_at"}
        changes = {key: value for key, value in changes.items() if key in allowed}
        if not changes:
            task = self.get_task(task_id)
            if not task:
                raise KeyError("task not found")
            return task
        changes["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        assignments = ", ".join(f"{key} = ?" for key in changes)
        values = list(changes.values()) + [task_id]
        with self.connect() as db:
            cursor = db.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", values)
            if cursor.rowcount == 0:
                raise KeyError("task not found")
        return self.get_task(task_id) or {}
