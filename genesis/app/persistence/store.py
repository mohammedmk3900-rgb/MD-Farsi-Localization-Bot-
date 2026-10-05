from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2

class Store:
    """Durable SQLite boundary for operational state, snapshots and audit history."""
    def __init__(self, path: str | Path, *, busy_timeout_ms: int = 5000):
        self.path = Path(path)
        self.busy_timeout_ms = max(100, int(busy_timeout_ms))

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=self.busy_timeout_ms / 1000)
        db.row_factory = sqlite3.Row
        db.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        return db

    def initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, actor TEXT, created_at TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, scope TEXT NOT NULL DEFAULT '', owner TEXT, reviewer TEXT, priority TEXT NOT NULL, status TEXT NOT NULL, due_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner);
            CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, translation_key TEXT NOT NULL, actor TEXT NOT NULL, reviewer TEXT, decision TEXT, reason TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
            CREATE TABLE IF NOT EXISTS glossary_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, captured_at TEXT NOT NULL, term_count INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_glossary_snapshots_project ON glossary_snapshots(project_id, captured_at);
            CREATE TABLE IF NOT EXISTS sync_runs (id TEXT PRIMARY KEY, project_id INTEGER NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, severity TEXT NOT NULL, code TEXT NOT NULL, message TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, resolved_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active);
            CREATE TABLE IF NOT EXISTS scheduler_jobs (job_id TEXT PRIMARY KEY, status TEXT NOT NULL, next_run_at TEXT, last_run_at TEXT, lease_until TEXT, run_count INTEGER NOT NULL DEFAULT 0, failure_count INTEGER NOT NULL DEFAULT 0, last_error TEXT);
            CREATE TABLE IF NOT EXISTS health_checks (check_name TEXT PRIMARY KEY, status TEXT NOT NULL, checked_at TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
            """)
            db.execute("""INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (str(SCHEMA_VERSION),))

    def record_event(self, event_type: str, actor: str | None, created_at: str, payload: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO events(event_type, actor, created_at, payload) VALUES (?, ?, ?, ?)", (event_type, actor, created_at, json.dumps(payload, ensure_ascii=False, sort_keys=True)))

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as db:
            rows = db.execute("SELECT id,event_type,actor,created_at,payload FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r["id"], "event_type": r["event_type"], "actor": r["actor"], "created_at": r["created_at"], "payload": json.loads(r["payload"])} for r in rows]

    def save_glossary_snapshot(self, project_id: int, captured_at: str, terms: list[dict[str, Any]]) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO glossary_snapshots(project_id,captured_at,term_count,payload) VALUES(?,?,?,?)", (project_id, captured_at, len(terms), json.dumps(terms, ensure_ascii=False, sort_keys=True)))

    def latest_glossary_snapshot(self, project_id: int) -> list[dict[str, Any]] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM glossary_snapshots WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()
        return None if row is None else json.loads(row["payload"])

    def record_sync_run(self, run_id: str, project_id: int, started_at: str, status: str, payload: dict[str, Any], finished_at: str | None = None) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO sync_runs(id,project_id,started_at,finished_at,status,payload) VALUES(?,?,?,?,?,?)", (run_id, project_id, started_at, finished_at, status, json.dumps(payload, ensure_ascii=False, sort_keys=True)))

    def counts(self) -> dict[str, int]:
        tables = ("events", "tasks", "reviews", "glossary_snapshots", "sync_runs", "alerts", "scheduler_jobs")
        with self._connect() as db:
            return {table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}