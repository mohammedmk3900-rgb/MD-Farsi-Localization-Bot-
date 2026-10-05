from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 5


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
            CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, translation_key TEXT NOT NULL, actor TEXT NOT NULL, reviewer TEXT, decision TEXT, reason TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, source TEXT NOT NULL DEFAULT '', translation TEXT NOT NULL DEFAULT '', findings TEXT NOT NULL DEFAULT '[]');
            CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
            CREATE TABLE IF NOT EXISTS glossary_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, captured_at TEXT NOT NULL, term_count INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_glossary_snapshots_project ON glossary_snapshots(project_id, captured_at);
            CREATE TABLE IF NOT EXISTS sync_runs (id TEXT PRIMARY KEY, project_id INTEGER NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, severity TEXT NOT NULL, code TEXT NOT NULL, message TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, resolved_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active);
            CREATE TABLE IF NOT EXISTS scheduler_jobs (job_id TEXT PRIMARY KEY, status TEXT NOT NULL, next_run_at TEXT, last_run_at TEXT, lease_until TEXT, run_count INTEGER NOT NULL DEFAULT 0, failure_count INTEGER NOT NULL DEFAULT 0, last_error TEXT);
            CREATE TABLE IF NOT EXISTS health_checks (check_name TEXT PRIMARY KEY, status TEXT NOT NULL, checked_at TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS member_progress (member_id TEXT PRIMARY KEY, completed INTEGER NOT NULL DEFAULT 0, review INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS achievements (member_id TEXT NOT NULL, achievement_key TEXT NOT NULL, earned_at TEXT NOT NULL, PRIMARY KEY(member_id, achievement_key));
            CREATE TABLE IF NOT EXISTS qa_runs (id TEXT PRIMARY KEY, translation_key TEXT NOT NULL, source TEXT NOT NULL, translation TEXT NOT NULL, findings TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
            for column, definition in (
                ("source", "TEXT NOT NULL DEFAULT ''"),
                ("translation", "TEXT NOT NULL DEFAULT ''"),
                ("findings", "TEXT NOT NULL DEFAULT '[]'"),
            ):
                existing = {row["name"] for row in db.execute("PRAGMA table_info(reviews)").fetchall()}
                if column not in existing:
                    db.execute(f"ALTER TABLE reviews ADD COLUMN {column} {definition}")
            db.execute("""INSERT INTO schema_meta(key, value) VALUES('schema_version', ?)
                         ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (str(SCHEMA_VERSION),))

    def record_event(self, event_type: str, actor: str | None, created_at: str, payload: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO events(event_type, actor, created_at, payload) VALUES (?, ?, ?, ?)",
                       (event_type, actor, created_at, json.dumps(payload, ensure_ascii=False, sort_keys=True)))

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as db:
            rows = db.execute("SELECT id,event_type,actor,created_at,payload FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r["id"], "event_type": r["event_type"], "actor": r["actor"], "created_at": r["created_at"], "payload": json.loads(r["payload"])} for r in rows]

    def create_task(self, *, title: str, scope: str, priority: str, due_at: str | None, created_at: str) -> int:
        with self._connect() as db:
            cur = db.execute("""INSERT INTO tasks(title,scope,priority,status,due_at,created_at,updated_at)
                                VALUES(?,?,?,?,?,?,?)""",
                             (title, scope, priority, "available", due_at, created_at, created_at))
            return int(cur.lastrowid)

    def task(self, task_id: int) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return None if row is None else dict(row)

    def tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if status is None:
                rows = db.execute("SELECT * FROM tasks ORDER BY id").fetchall()
            else:
                rows = db.execute("SELECT * FROM tasks WHERE status=? ORDER BY id", (status,)).fetchall()
        return [dict(r) for r in rows]

    def update_task(self, task_id: int, *, owner: str | None = None, reviewer: str | None = None,
                    priority: str | None = None, status: str | None = None, due_at: str | None = None,
                    updated_at: str, expected_status: str | None = None,
                    expected_owner: str | None = None) -> None:
        current = self.task(task_id)
        if current is None:
            raise KeyError(f"task #{task_id} not found")
        values = {
            "owner": current["owner"] if owner is None else owner,
            "reviewer": current["reviewer"] if reviewer is None else reviewer,
            "priority": current["priority"] if priority is None else priority,
            "status": current["status"] if status is None else status,
            "due_at": current["due_at"] if due_at is None else due_at,
        }
        with self._connect() as db:
            where = "id=?"
            params = [values["owner"], values["reviewer"], values["priority"], values["status"], values["due_at"], updated_at, task_id]
            if expected_status is not None:
                where += " AND status=?"
                params.append(expected_status)
            if expected_owner is not None:
                where += " AND (owner=? OR owner IS NULL)"
                params.append(expected_owner)
            cur = db.execute(f"""UPDATE tasks SET owner=?,reviewer=?,priority=?,status=?,due_at=?,updated_at=? WHERE {where}""", params)
            if cur.rowcount != 1:
                raise ValueError("stale task state")

    def transition_task(self, task_id: int, *, target_status: str, updated_at: str,
                       allowed_from: tuple[str, ...], owner: str | None = None,
                       reviewer: str | None = None, expected_owner: str | None = None) -> None:
        if not allowed_from:
            raise ValueError("allowed_from is required")
        assignments = ["status=?", "updated_at=?"]
        params: list[Any] = [target_status, updated_at]
        if owner is not None:
            assignments.append("owner=?")
            params.append(owner)
        if reviewer is not None:
            assignments.append("reviewer=?")
            params.append(reviewer)
        placeholders = ",".join("?" for _ in allowed_from)
        where = f"id=? AND status IN ({placeholders})"
        params.append(task_id)
        params.extend(allowed_from)
        if expected_owner is not None:
            where += " AND (owner=? OR owner IS NULL)"
            params.append(expected_owner)
        with self._connect() as db:
            cur = db.execute(
                f"UPDATE tasks SET {','.join(assignments)} WHERE {where}", params
            )
            if cur.rowcount != 1:
                raise ValueError("stale task state")

    def create_review(self, *, translation_key: str, actor: str, status: str,
                      created_at: str, source: str = "", translation: str = "",
                      findings: list[dict[str, Any]] | None = None) -> int:
        with self._connect() as db:
            cur = db.execute("""INSERT INTO reviews(translation_key,actor,status,created_at,updated_at,source,translation,findings)
                                VALUES(?,?,?,?,?,?,?,?,?)""",
                             (translation_key, actor, status, created_at, created_at, source, translation,
                              json.dumps(findings or [], ensure_ascii=False, sort_keys=True)))
            return int(cur.lastrowid)

    def reviews(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            if status is None:
                rows = db.execute("SELECT * FROM reviews ORDER BY id").fetchall()
            else:
                rows = db.execute("SELECT * FROM reviews WHERE status=? ORDER BY id", (status,)).fetchall()
        return [dict(r) for r in rows]

    def decide_review(self, review_id: int, *, reviewer: str, decision: str | None, reason: str | None,
                      status: str, updated_at: str, expected_status: str | None = None) -> None:
        with self._connect() as db:
            where = "id=?"
            params = [reviewer, decision, reason, status, updated_at, review_id]
            if expected_status is not None:
                where += " AND status=?"
                params.append(expected_status)
            cur = db.execute(f"""UPDATE reviews SET reviewer=?,decision=?,reason=?,status=?,updated_at=? WHERE {where}""", params)
            if cur.rowcount != 1:
                raise ValueError("stale review state")

    def transition_review(self, review_id: int, *, target_status: str, updated_at: str,
                         allowed_from: tuple[str, ...], reviewer: str | None = None,
                         decision: str | None = None, reason: str | None = None) -> None:
        if not allowed_from:
            raise ValueError("allowed_from is required")
        assignments = ["status=?", "updated_at=?"]
        params: list[Any] = [target_status, updated_at]
        if reviewer is not None:
            assignments.append("reviewer=?")
            params.append(reviewer)
        if decision is not None:
            assignments.append("decision=?")
            params.append(decision)
        if reason is not None:
            assignments.append("reason=?")
            params.append(reason)
        placeholders = ",".join("?" for _ in allowed_from)
        params.append(review_id)
        params.extend(allowed_from)
        with self._connect() as db:
            cur = db.execute(
                f"UPDATE reviews SET {','.join(assignments)} WHERE id=? AND status IN ({placeholders})",
                params,
            )
            if cur.rowcount != 1:
                raise ValueError("stale review state")

    def save_glossary_snapshot(self, project_id: int, captured_at: str, terms: list[dict[str, Any]]) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO glossary_snapshots(project_id,captured_at,term_count,payload) VALUES(?,?,?,?)",
                       (project_id, captured_at, len(terms), json.dumps(terms, ensure_ascii=False, sort_keys=True)))

    def latest_glossary_snapshot(self, project_id: int) -> list[dict[str, Any]] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM glossary_snapshots WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()
        return None if row is None else json.loads(row["payload"])

    def record_sync_run(self, run_id: str, project_id: int, started_at: str, status: str,
                        payload: dict[str, Any], finished_at: str | None = None) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO sync_runs(id,project_id,started_at,finished_at,status,payload) VALUES(?,?,?,?,?,?)",
                       (run_id, project_id, started_at, finished_at, status, json.dumps(payload, ensure_ascii=False, sort_keys=True)))

    def upsert_scheduler_job(self, job_id: str, *, status: str = "pending", next_run_at: str | None = None) -> None:
        with self._connect() as db:
            db.execute("""INSERT INTO scheduler_jobs(job_id,status,next_run_at) VALUES(?,?,?)
                         ON CONFLICT(job_id) DO UPDATE SET next_run_at=excluded.next_run_at""",
                       (job_id, status, next_run_at))

    def claim_scheduler_job(self, job_id: str, *, now_iso: str, lease_until: str) -> bool:
        with self._connect() as db:
            cur = db.execute("""UPDATE scheduler_jobs
                                SET status='running', lease_until=?, last_run_at=?, run_count=run_count+1
                                WHERE job_id=? AND status!='running' AND (lease_until IS NULL OR lease_until < ?)""",
                             (lease_until, now_iso, job_id, now_iso))
            return cur.rowcount == 1

    def finish_scheduler_job(self, job_id: str, *, next_run_at: str | None) -> None:
        with self._connect() as db:
            db.execute("""UPDATE scheduler_jobs SET status='pending',next_run_at=?,lease_until=NULL,last_error=NULL
                          WHERE job_id=?""", (next_run_at, job_id))

    def fail_scheduler_job(self, job_id: str, *, error: str, next_run_at: str | None) -> None:
        with self._connect() as db:
            db.execute("""UPDATE scheduler_jobs SET status='pending',next_run_at=?,lease_until=NULL,
                          failure_count=failure_count+1,last_error=? WHERE job_id=?""",
                       (next_run_at, error[:2000], job_id))

    def scheduler_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM scheduler_jobs WHERE job_id=?", (job_id,)).fetchone()
        return None if row is None else dict(row)

    def upsert_member_progress(self, member_id: str, completed: int, review: int, active: int, updated_at: str) -> None:
        with self._connect() as db:
            db.execute("""INSERT INTO member_progress(member_id,completed,review,active,updated_at)
                         VALUES(?,?,?,?,?) ON CONFLICT(member_id) DO UPDATE SET completed=excluded.completed,
                         review=excluded.review,active=excluded.active,updated_at=excluded.updated_at""",
                       (member_id, max(0, completed), max(0, review), max(0, active), updated_at))

    def member_progress(self, member_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM member_progress WHERE member_id=?", (member_id,)).fetchone()
        return None if row is None else dict(row)

    def award_achievement(self, member_id: str, achievement_key: str, earned_at: str) -> bool:
        with self._connect() as db:
            cur = db.execute("INSERT OR IGNORE INTO achievements(member_id,achievement_key,earned_at) VALUES(?,?,?)",
                             (member_id, achievement_key, earned_at))
            return cur.rowcount == 1

    def achievements(self, member_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM achievements" + (" WHERE member_id=?" if member_id else "") +
                              " ORDER BY earned_at", ((member_id,) if member_id else ())).fetchall()
        return [dict(row) for row in rows]

    def record_qa_run(self, run_id: str, translation_key: str, source: str, translation: str,
                      findings: list[dict[str, Any]], created_at: str) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO qa_runs(id,translation_key,source,translation,findings,created_at) VALUES(?,?,?,?,?,?)",
                       (run_id, translation_key, source, translation,
                        json.dumps(findings, ensure_ascii=False, sort_keys=True), created_at))

    def qa_runs(self, translation_key: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as db:
            if translation_key:
                rows = db.execute("SELECT * FROM qa_runs WHERE translation_key=? ORDER BY created_at DESC LIMIT ?",
                                  (translation_key, limit)).fetchall()
            else:
                rows = db.execute("SELECT * FROM qa_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) | {"findings": json.loads(row["findings"])} for row in rows]

    def counts(self) -> dict[str, int]:
        tables = ("events", "tasks", "reviews", "glossary_snapshots", "sync_runs", "alerts", "scheduler_jobs", "member_progress", "achievements", "qa_runs")
        with self._connect() as db:
            return {table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
