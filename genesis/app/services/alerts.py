from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.persistence.store import Store


@dataclass(frozen=True)
class Alert:
    severity: str
    component: str
    message: str
    code: str = "GENESIS"


class AlertService:
    def __init__(self, store: Store | None = None):
        self.store = store

    def service_failure(self, component: str, message: str, code: str = "SERVICE_FAILURE") -> Alert:
        return self._record(Alert("critical", component, message, code))

    def degraded(self, component: str, message: str, code: str = "DEGRADED") -> Alert:
        return self._record(Alert("warning", component, message, code))

    def _record(self, alert: Alert) -> Alert:
        if self.store:
            now = datetime.now(timezone.utc).isoformat()
            with self.store._connect() as db:
                db.execute(
                    "INSERT INTO alerts(severity,code,message,created_at) VALUES(?,?,?,?)",
                    (alert.severity, alert.code, f"[{alert.component}] {alert.message}", now),
                )
        return alert

    def active(self) -> list[dict]:
        if not self.store:
            return []
        with self.store._connect() as db:
            rows = db.execute("SELECT * FROM alerts WHERE active=1 ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def resolve(self, alert_id: int) -> None:
        if not self.store:
            return
        now = datetime.now(timezone.utc).isoformat()
        with self.store._connect() as db:
            db.execute("UPDATE alerts SET active=0,resolved_at=? WHERE id=?", (now, alert_id))
