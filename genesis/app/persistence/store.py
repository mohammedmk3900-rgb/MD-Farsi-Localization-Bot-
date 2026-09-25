from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.domain.models import Priority, Task, TaskStatus


class Store:
    """SQLite boundary for Genesis operational state and audit history."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    actor TEXT,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT '',
                    owner TEXT,
                    reviewer TEXT,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    due_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    source TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    findings TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    target_id INTEGER,
                    actor TEXT,
                    run_at TEXT NOT NULL,
                    message TEXT NOT NULL,
                    delivered INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_schedules_due
                    ON schedules(delivered, run_at);
                """
            )

    def record_event(self, event_type: str, actor: str | None, created_at: str, payload: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO events(event_type, actor, created_at, payload) VALUES (?, ?, ?, ?)",
                (event_type, actor, created_at, json.dumps(payload, ensure_ascii=False)),
            )

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self._connect() as db:
            rows = db.execute(
                "SELECT id,event_type,actor,created_at,payload FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "actor": row["actor"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

    def save_task(self, task: Task) -> Task:
        if task.id <= 0:
            raise ValueError("task id must be positive")
        if not task.title.strip():
            raise ValueError("title is required")
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO tasks
                (id,title,scope,owner,reviewer,priority,status,due_at,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, scope=excluded.scope, owner=excluded.owner,
                    reviewer=excluded.reviewer, priority=excluded.priority,
                    status=excluded.status, due_at=excluded.due_at,
                    updated_at=excluded.updated_at
                """,
                (
                    task.id, task.title, task.scope, task.owner, task.reviewer,
                    task.priority.value, task.status.value, task.due_at,
                    task.created_at, task.updated_at,
                ),
            )
        return task

    def next_task_id(self) -> int:
        with self._connect() as db:
            row = db.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM tasks").fetchone()
            return int(row["next_id"])

    def tasks(self) -> list[Task]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        return [
            Task(
                id=row["id"], title=row["title"], scope=row["scope"],
                owner=row["owner"], reviewer=row["reviewer"],
                priority=Priority(row["priority"]), status=TaskStatus(row["status"]),
                due_at=row["due_at"], created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def task(self, task_id: int) -> Task | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return Task(
            id=row["id"], title=row["title"], scope=row["scope"],
            owner=row["owner"], reviewer=row["reviewer"],
            priority=Priority(row["priority"]), status=TaskStatus(row["status"]),
            due_at=row["due_at"], created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def save_review(self, actor: str, source: str, translation: str, findings: list[dict], created_at: str) -> int:
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO reviews(actor,source,translation,findings,created_at) VALUES (?,?,?,?,?)",
                (actor, source, translation, json.dumps(findings, ensure_ascii=False), created_at),
            )
            return int(cur.lastrowid)

    def reviews(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM reviews ORDER BY id").fetchall()
        return [
            {
                "id": row["id"], "actor": row["actor"], "source": row["source"],
                "translation": row["translation"],
                "findings": json.loads(row["findings"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def schedule(self, kind: str, target_id: int | None, actor: str | None, run_at: str, message: str, created_at: str) -> int:
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO schedules(kind,target_id,actor,run_at,message,created_at) VALUES (?,?,?,?,?,?)",
                (kind, target_id, actor, run_at, message, created_at),
            )
            return int(cur.lastrowid)

    def due_schedules(self, now_iso: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM schedules WHERE delivered=0 AND run_at <= ? ORDER BY run_at,id",
                (now_iso,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_schedule_delivered(self, schedule_id: int) -> None:
        with self._connect() as db:
            db.execute("UPDATE schedules SET delivered=1 WHERE id=?", (schedule_id,))
